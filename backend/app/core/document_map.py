"""
Living Document Map management.
The map is the core of one-shot retrieval - it's an LLM-maintained index.
"""
import json
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentMap as DocumentMapModel
from app.core.gemini_client import get_gemini_client


class DocumentMapManager:
    """Manages the living document map."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.gemini = get_gemini_client()

    async def get_map(self, workspace_id: str = "default") -> dict:
        """Get current document map for workspace."""
        result = await self.db.execute(
            select(DocumentMapModel).where(DocumentMapModel.workspace_id == workspace_id)
        )
        map_record = result.scalar_one_or_none()

        if map_record:
            return json.loads(map_record.map_data)

        # Return empty map structure
        return {
            "corpus_id": workspace_id,
            "last_updated": datetime.utcnow().isoformat(),
            "corpus_summary": "",
            "documents": [],
            "cross_references": {
                "by_entity": {},
                "by_topic": {}
            }
        }

    async def add_document(
        self,
        workspace_id: str,
        document_id: str,
        filename: str,
        content: str,
        size_class: str,
        chunks: Optional[list[dict]] = None
    ) -> dict:
        """
        Add document to map with full intelligence extraction.

        1. Extract document intelligence via Gemini
        2. Identify relationships to existing documents
        3. Update cross-references
        4. Update corpus summary
        """
        # Get current map
        current_map = await self.get_map(workspace_id)

        # Extract intelligence from new document
        intelligence = await self.gemini.extract_document_intelligence(content, filename)

        # Build document entry
        doc_entry = {
            "id": document_id,
            "filename": filename,
            "type": intelligence.get("document_type", "other"),
            "size_class": size_class,
            "essence": intelligence["essence"],
            "topics": intelligence["topics"],
            "entities": intelligence["entities"],
            "retrieval_hints": intelligence["retrieval_hints"],
            "added_at": datetime.utcnow().isoformat(),
            "relationships": []
        }

        # Add chunks if large document
        if chunks:
            doc_entry["chunks"] = [
                {
                    "chunk_id": f"{document_id}_{c['chunk_id']}",
                    "section": c["section"],
                    "context": c["context"],
                    "retrieval_hints": f"Part of {filename}: {c['section']}"
                }
                for c in chunks
            ]

        # If we have existing documents, find relationships
        if current_map["documents"]:
            map_updates = await self.gemini.update_document_map(current_map, doc_entry)

            # Add relationships
            doc_entry["relationships"] = map_updates.get("relationships", [])

            # Merge cross-references
            new_refs = map_updates.get("new_cross_references", {})
            self._merge_cross_references(current_map["cross_references"], new_refs)

            # Update corpus summary
            current_map["corpus_summary"] = map_updates.get(
                "updated_corpus_summary",
                current_map["corpus_summary"]
            )
        else:
            # First document - create initial summary
            current_map["corpus_summary"] = f"Corpus containing: {filename}. {intelligence['essence']}"

            # Initialize cross-references
            for entity_type, entities in intelligence["entities"].items():
                for entity in entities:
                    if entity not in current_map["cross_references"]["by_entity"]:
                        current_map["cross_references"]["by_entity"][entity] = []
                    current_map["cross_references"]["by_entity"][entity].append(document_id)

            for topic in intelligence["topics"]:
                if topic not in current_map["cross_references"]["by_topic"]:
                    current_map["cross_references"]["by_topic"][topic] = []
                current_map["cross_references"]["by_topic"][topic].append(document_id)

        # Add document to map
        current_map["documents"].append(doc_entry)
        current_map["last_updated"] = datetime.utcnow().isoformat()

        # Persist map
        await self._save_map(workspace_id, current_map)

        return doc_entry

    async def remove_document(self, workspace_id: str, document_id: str) -> bool:
        """Remove document from map and update cross-references."""
        current_map = await self.get_map(workspace_id)

        # Find and remove document
        doc_to_remove = None
        for i, doc in enumerate(current_map["documents"]):
            if doc["id"] == document_id:
                doc_to_remove = current_map["documents"].pop(i)
                break

        if not doc_to_remove:
            return False

        # Clean cross-references
        for entity, doc_ids in list(current_map["cross_references"]["by_entity"].items()):
            if document_id in doc_ids:
                doc_ids.remove(document_id)

        for topic, doc_ids in list(current_map["cross_references"]["by_topic"].items()):
            if document_id in doc_ids:
                doc_ids.remove(document_id)

        # Remove empty entries
        current_map["cross_references"]["by_entity"] = {
            k: v for k, v in current_map["cross_references"]["by_entity"].items() if v
        }
        current_map["cross_references"]["by_topic"] = {
            k: v for k, v in current_map["cross_references"]["by_topic"].items() if v
        }

        # Update timestamp
        current_map["last_updated"] = datetime.utcnow().isoformat()

        # Persist
        await self._save_map(workspace_id, current_map)

        return True

    def _merge_cross_references(self, existing: dict, new: dict) -> None:
        """Merge new cross-references into existing."""
        for ref_type in ["by_entity", "by_topic"]:
            if ref_type in new:
                for key, doc_ids in new[ref_type].items():
                    if key not in existing[ref_type]:
                        existing[ref_type][key] = []
                    existing[ref_type][key].extend(doc_ids)
                    # Deduplicate
                    existing[ref_type][key] = list(set(existing[ref_type][key]))

    async def _save_map(self, workspace_id: str, map_data: dict) -> None:
        """Persist document map to database."""
        result = await self.db.execute(
            select(DocumentMapModel).where(DocumentMapModel.workspace_id == workspace_id)
        )
        map_record = result.scalar_one_or_none()

        if map_record:
            map_record.map_data = json.dumps(map_data)
            map_record.updated_at = datetime.utcnow()
        else:
            map_record = DocumentMapModel(
                workspace_id=workspace_id,
                map_data=json.dumps(map_data)
            )
            self.db.add(map_record)

        await self.db.commit()
