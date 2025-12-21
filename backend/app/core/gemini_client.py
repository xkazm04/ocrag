"""
Unified Gemini client for OCR, extraction, retrieval, and chat.
"""
import json
import re
from typing import Optional
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


class GeminiClient:
    """Unified client for all Gemini operations."""

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        self._cached_map_id: Optional[str] = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def ocr_pdf(
        self,
        pdf_bytes: bytes,
        extraction_prompt: Optional[str] = None
    ) -> dict:
        """
        Extract text and structure from PDF using Gemini's native vision.

        Returns:
            {
                "content": str,  # Markdown formatted content
                "metadata": {
                    "pages": int,
                    "has_tables": bool,
                    "has_images": bool,
                    "estimated_tokens": int
                }
            }
        """
        prompt = extraction_prompt or """
        Extract ALL content from this PDF document.

        Output format:
        1. Convert to clean Markdown preserving structure
        2. Preserve tables as Markdown tables
        3. Describe images/charts in [IMAGE: description] blocks
        4. Maintain headers, lists, and formatting
        5. For multi-column layouts, process left-to-right

        After the content, provide metadata as JSON:
        ```json
        {"pages": N, "has_tables": bool, "has_images": bool}
        ```
        """

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                types.Part.from_text(text=prompt)
            ],
            config=types.GenerateContentConfig(
                response_mime_type="text/plain"
            )
        )

        return self._parse_ocr_response(response.text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def extract_document_intelligence(
        self,
        content: str,
        filename: str
    ) -> dict:
        """
        Extract intelligence from document for the document map.

        Returns:
            {
                "essence": str,
                "topics": list[str],
                "entities": dict,
                "retrieval_hints": str,
                "suggested_chunks": list[dict] | None
            }
        """
        prompt = f"""
        Analyze this document and extract structured intelligence.

        Document filename: {filename}

        Content:
        {content[:100000]}

        Provide a JSON response with:
        {{
            "essence": "2-3 sentence summary of core content and purpose",
            "topics": ["topic1", "topic2", ...],
            "entities": {{
                "organizations": [...],
                "people": [...],
                "dates": [...],
                "metrics": [...],
                "locations": [...]
            }},
            "retrieval_hints": "What questions would this document answer? What queries should retrieve this?",
            "document_type": "financial_report|legal_contract|technical_doc|correspondence|other",
            "suggested_chunk_boundaries": [
                {{"start_marker": "Section 1...", "end_marker": "Section 2...", "topic": "..."}}
            ]
        }}
        """

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        return self._parse_json_response(response.text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def consult_map_for_retrieval(
        self,
        query: str,
        document_map: dict
    ) -> dict:
        """
        One-shot retrieval: consult document map to select documents/chunks.

        Returns:
            {
                "retrieve": ["doc_id", "doc_id_chunk_N", ...],
                "reasoning": str
            }
        """
        prompt = f"""
        You are a retrieval specialist. Given a user query and document map,
        select the MINIMAL set of documents/chunks needed to answer the query.

        USER QUERY: {query}

        DOCUMENT MAP:
        {self._format_map_for_prompt(document_map)}

        Instructions:
        1. Analyze query intent and information needs
        2. Match against document essences, topics, and retrieval hints
        3. For small documents (size_class="small"), return doc_id
        4. For large documents, return specific chunk_ids (e.g., "doc_123_c2")
        5. Consider cross-references for multi-hop queries
        6. Return MINIMAL set - don't over-retrieve

        Response format (JSON):
        {{
            "retrieve": ["doc_001", "doc_042_c3", "doc_042_c4"],
            "reasoning": "Brief explanation of selection logic"
        }}
        """

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        return self._parse_json_response(response.text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def generate_answer(
        self,
        query: str,
        retrieved_content: list[dict],
        chat_history: Optional[list[dict]] = None
    ) -> dict:
        """
        Generate answer using retrieved documents.

        Args:
            query: User's question
            retrieved_content: List of {"id": str, "content": str, "context": str}
            chat_history: Previous messages for context

        Returns:
            {
                "answer": str,
                "citations": [{"doc_id": str, "excerpt": str}],
                "confidence": float
            }
        """
        # Build context
        context_parts = []
        for doc in retrieved_content:
            context_parts.append(f"""
[Document: {doc['id']}]
{doc.get('context', '')}

{doc['content']}
---
""")

        history_text = ""
        if chat_history:
            history_text = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in chat_history[-5:]
            ])

        prompt = f"""
        Answer the user's question using ONLY the provided documents.

        DOCUMENTS:
        {''.join(context_parts)}

        {f'CHAT HISTORY:{chr(10)}{history_text}' if history_text else ''}

        USER QUESTION: {query}

        Instructions:
        1. Answer directly and concisely
        2. Cite sources using [doc_id] format
        3. If information is insufficient, say so clearly
        4. Do not hallucinate - only use provided content

        Response format (JSON):
        {{
            "answer": "Your comprehensive answer with [doc_id] citations",
            "citations": [
                {{"doc_id": "doc_001", "excerpt": "Relevant quote"}}
            ],
            "confidence": 0.0-1.0
        }}
        """

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        return self._parse_json_response(response.text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def update_document_map(
        self,
        existing_map: dict,
        new_document: dict
    ) -> dict:
        """
        Update document map with new document, identifying relationships.

        Returns updated map with new document and cross-references.
        """
        prompt = f"""
        Update this document map with a new document.

        EXISTING MAP SUMMARY:
        {existing_map.get('corpus_summary', 'Empty corpus')}

        EXISTING DOCUMENTS (summaries):
        {self._format_existing_docs_summary(existing_map)}

        NEW DOCUMENT:
        ID: {new_document['id']}
        Filename: {new_document['filename']}
        Essence: {new_document['essence']}
        Topics: {new_document['topics']}
        Entities: {new_document['entities']}

        Tasks:
        1. Identify relationships to existing documents
        2. Update cross-references (by_entity, by_topic)
        3. Update corpus_summary to reflect new addition

        Response format (JSON):
        {{
            "relationships": [
                {{"doc_id": "existing_doc_id", "relation": "references|supersedes|complements", "note": "..."}}
            ],
            "new_cross_references": {{
                "by_entity": {{"EntityName": ["doc_ids"]}},
                "by_topic": {{"topic": ["doc_ids"]}}
            }},
            "updated_corpus_summary": "New summary incorporating this document"
        }}
        """

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        return self._parse_json_response(response.text)

    def _parse_ocr_response(self, text: str) -> dict:
        """Parse OCR response separating content and metadata."""
        # Try to find JSON metadata block
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)

        if json_match:
            content = text[:json_match.start()].strip()
            try:
                metadata = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                metadata = {"pages": 1, "has_tables": False, "has_images": False}
        else:
            content = text
            metadata = {"pages": 1, "has_tables": False, "has_images": False}

        # Estimate tokens
        metadata["estimated_tokens"] = len(content) // 4

        return {"content": content, "metadata": metadata}

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON response from Gemini."""
        # Clean potential markdown code blocks
        text = re.sub(r'^```json\s*', '', text.strip())
        text = re.sub(r'\s*```$', '', text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Could not parse JSON from response: {text[:500]}")

    def _format_map_for_prompt(self, document_map: dict) -> str:
        """Format document map for inclusion in prompt."""
        # Truncate large maps
        simplified = {
            "corpus_summary": document_map.get("corpus_summary", ""),
            "documents": [
                {
                    "id": d["id"],
                    "essence": d["essence"],
                    "topics": d["topics"],
                    "retrieval_hints": d.get("retrieval_hints", ""),
                    "size_class": d.get("size_class", "small"),
                    "chunks": [
                        {"chunk_id": c["chunk_id"], "topic": c.get("topic", "")}
                        for c in d.get("chunks", [])
                    ] if d.get("chunks") else None
                }
                for d in document_map.get("documents", [])
            ],
            "cross_references": document_map.get("cross_references", {})
        }
        return json.dumps(simplified, indent=2)

    def _format_existing_docs_summary(self, document_map: dict) -> str:
        """Format existing documents for map update prompt."""
        docs = document_map.get("documents", [])
        summaries = [
            f"- {d['id']}: {d['essence'][:100]}..."
            for d in docs[:20]
        ]
        return "\n".join(summaries) if summaries else "No existing documents"


# Singleton instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Get singleton Gemini client instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
