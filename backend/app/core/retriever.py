"""
One-shot retrieval system using document map.
No re-ranking required - the LLM makes intelligent retrieval decisions.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.gemini_client import get_gemini_client
from app.core.document_map import DocumentMapManager
from app.db.models import Document, DocumentChunk


class IntelligentRetriever:
    """One-shot retrieval using document map consultation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.gemini = get_gemini_client()
        self.map_manager = DocumentMapManager(db)

    async def retrieve(
        self,
        query: str,
        workspace_id: str = "default",
        max_documents: int = 5
    ) -> list[dict]:
        """
        Retrieve relevant documents/chunks for query.

        1. Get document map
        2. Consult Gemini for retrieval decision (one-shot)
        3. Fetch selected documents/chunks
        4. Return with context metadata
        """
        # Get document map
        document_map = await self.map_manager.get_map(workspace_id)

        if not document_map["documents"]:
            return []

        # Consult map for retrieval decision
        retrieval_decision = await self.gemini.consult_map_for_retrieval(
            query, document_map
        )

        doc_ids_to_retrieve = retrieval_decision.get("retrieve", [])[:max_documents]

        if not doc_ids_to_retrieve:
            return []

        # Fetch documents and chunks
        retrieved_content = []

        for doc_ref in doc_ids_to_retrieve:
            if "_c" in doc_ref:
                # This is a chunk reference (e.g., "doc_123_c2")
                parts = doc_ref.rsplit("_c", 1)
                doc_id = parts[0]
                chunk_num = int(parts[1])

                content = await self._fetch_chunk(doc_id, chunk_num, document_map)
            else:
                # Full document
                content = await self._fetch_document(doc_ref, document_map)

            if content:
                retrieved_content.append(content)

        return retrieved_content

    async def _fetch_document(self, doc_id: str, document_map: dict) -> Optional[dict]:
        """Fetch full document content."""
        # Get from database
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            return None

        # Get map entry for context
        map_entry = next(
            (d for d in document_map["documents"] if d["id"] == doc_id),
            None
        )

        return {
            "id": doc_id,
            "content": doc.content,
            "context": f"Document: {doc.filename}. {map_entry['essence'] if map_entry else ''}"
        }

    async def _fetch_chunk(
        self,
        doc_id: str,
        chunk_num: int,
        document_map: dict
    ) -> Optional[dict]:
        """Fetch specific chunk with context."""
        chunk_id = f"{doc_id}_c{chunk_num}"

        result = await self.db.execute(
            select(DocumentChunk).where(DocumentChunk.chunk_id == chunk_id)
        )
        chunk = result.scalar_one_or_none()

        if not chunk:
            return None

        # Get map entry for context
        map_entry = next(
            (d for d in document_map["documents"] if d["id"] == doc_id),
            None
        )

        chunk_map_entry = None
        if map_entry and map_entry.get("chunks"):
            chunk_map_entry = next(
                (c for c in map_entry["chunks"] if c["chunk_id"] == chunk_id),
                None
            )

        context_parts = [f"From document: {map_entry['filename'] if map_entry else doc_id}"]
        if chunk_map_entry:
            context_parts.append(f"Section: {chunk_map_entry.get('section', 'Unknown')}")
            context_parts.append(chunk_map_entry.get("context", ""))

        return {
            "id": chunk_id,
            "content": chunk.content,
            "context": " ".join(context_parts)
        }

    async def retrieve_by_ids(
        self,
        doc_ids: list[str],
        workspace_id: str = "default"
    ) -> list[dict]:
        """
        Retrieve specific documents/chunks by ID.
        Useful for direct retrieval without map consultation.
        """
        document_map = await self.map_manager.get_map(workspace_id)
        retrieved_content = []

        for doc_ref in doc_ids:
            if "_c" in doc_ref:
                parts = doc_ref.rsplit("_c", 1)
                doc_id = parts[0]
                chunk_num = int(parts[1])
                content = await self._fetch_chunk(doc_id, chunk_num, document_map)
            else:
                content = await self._fetch_document(doc_ref, document_map)

            if content:
                retrieved_content.append(content)

        return retrieved_content


def get_retriever(db: AsyncSession) -> IntelligentRetriever:
    """Get retriever instance."""
    return IntelligentRetriever(db)
