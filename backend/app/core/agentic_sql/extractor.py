"""
Extract structured data from documents and populate SQL tables.
Uses Gemini to decompose documents into relational data.
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gemini_client import get_gemini_client
from app.core.agentic_sql.schemas import (
    SQLDocument, SQLClaim, SQLMetric, SQLEntity, SQLTopic,
    SQLRelationship, SQLDocumentChunk
)


STRUCTURED_EXTRACTION_PROMPT = """
You are a data extraction specialist. Extract structured information from this document
for storage in a relational database.

DOCUMENT: {filename}
CONTENT:
---
{content}
---

Extract the following as JSON:

## 1. DOCUMENT METADATA
{{
    "document_type": "financial_report|legal_contract|technical_doc|correspondence|presentation|policy|research|meeting_notes|other",
    "summary": "2-3 sentence summary",
    "purpose": "Why this document exists",
    "key_conclusion": "Main takeaway",
    "document_date": "YYYY-MM-DD or null",
    "period_start": "YYYY-MM-DD or null",
    "period_end": "YYYY-MM-DD or null",
    "confidence_level": "high|medium|low"
}}

## 2. CLAIMS
Extract factual statements, opinions, predictions, and recommendations.
[
    {{
        "claim_text": "The exact claim",
        "claim_type": "fact|opinion|prediction|recommendation",
        "topic": "Topic category",
        "confidence": "high|medium|low",
        "source_section": "Section name or heading",
        "is_quantitative": true/false,
        "can_be_verified": true/false
    }}
]
- Extract 10-30 key claims depending on document length
- Be precise — include specific details from the claim
- Focus on important/actionable claims

## 3. METRICS
Extract all quantitative data points.
[
    {{
        "metric_name": "Revenue|Growth Rate|Headcount|etc",
        "value": "The value as written ($4.2B, 12%, etc)",
        "numeric_value": 4200000000 (parsed float, null if unparseable),
        "unit": "USD|percent|units|etc",
        "period": "Q3 2025|FY2024|etc",
        "period_start": "YYYY-MM-DD or null",
        "period_end": "YYYY-MM-DD or null",
        "context": "Additional context",
        "comparison_base": "YoY|QoQ|vs budget|absolute|null",
        "entity_name": "Who this metric is about",
        "category": "financial|operational|growth|headcount|performance|other"
    }}
]
- Extract ALL numeric data points
- Parse numeric values for comparison (convert "4.2B" to 4200000000)
- Infer period dates from context

## 4. ENTITIES
Extract all named entities.
[
    {{
        "entity_name": "Name",
        "entity_type": "organization|person|product|location",
        "role": "subject|author|mentioned|competitor|partner",
        "title": "Title for people or null",
        "context": "Why entity is mentioned"
    }}
]

## 5. TOPICS
[
    {{"topic_name": "...", "is_primary": true/false}}
]
- 3-5 primary topics, 5-10 secondary topics
- Be specific (not "business" but "quarterly earnings analysis")

OUTPUT FORMAT:
{{
    "metadata": {{...}},
    "claims": [...],
    "metrics": [...],
    "entities": [...],
    "topics": [...]
}}
"""


class StructuredExtractor:
    """Extract structured data from documents for SQL storage."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.gemini = get_gemini_client()

    async def extract_and_store(
        self,
        document_id: str,
        workspace_id: str,
        filename: str,
        content: str,
        chunks: Optional[list[dict]] = None
    ) -> dict:
        """
        Extract structured data and store in SQL tables.

        Returns extraction statistics.
        """
        # Extract structured data via Gemini
        extraction = await self._extract_structured_data(filename, content)

        # Store document metadata
        await self._store_document(
            document_id, workspace_id, filename,
            extraction.get("metadata", {}), len(content) // 4
        )

        # Store claims
        claims_count = await self._store_claims(
            document_id, extraction.get("claims", [])
        )

        # Store metrics
        metrics_count = await self._store_metrics(
            document_id, extraction.get("metrics", [])
        )

        # Store entities
        entities_count = await self._store_entities(
            document_id, extraction.get("entities", [])
        )

        # Store topics
        topics_count = await self._store_topics(
            document_id, extraction.get("topics", [])
        )

        # Store chunks for fallback
        if chunks:
            await self._store_chunks(document_id, chunks)

        await self.db.commit()

        return {
            "document_id": document_id,
            "claims_extracted": claims_count,
            "metrics_extracted": metrics_count,
            "entities_extracted": entities_count,
            "topics_extracted": topics_count
        }

    async def _extract_structured_data(self, filename: str, content: str) -> dict:
        """Use Gemini to extract structured data."""
        from google.genai import types

        # Truncate for context limits
        max_chars = 300000
        if len(content) > max_chars:
            content = content[:int(max_chars * 0.7)] + "\n...\n" + content[-int(max_chars * 0.2):]

        prompt = STRUCTURED_EXTRACTION_PROMPT.format(
            filename=filename,
            content=content
        )

        response = await self.gemini.client.aio.models.generate_content(
            model=self.gemini.model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        return self.gemini._parse_json_response(response.text)

    async def _store_document(
        self, doc_id: str, workspace_id: str,
        filename: str, metadata: dict, token_count: int
    ):
        """Store document metadata."""
        doc = SQLDocument(
            id=doc_id,
            workspace_id=workspace_id,
            filename=filename,
            document_type=metadata.get("document_type", "other"),
            summary=metadata.get("summary", ""),
            purpose=metadata.get("purpose", ""),
            key_conclusion=metadata.get("key_conclusion", ""),
            document_date=self._parse_date(metadata.get("document_date")),
            period_start=self._parse_date(metadata.get("period_start")),
            period_end=self._parse_date(metadata.get("period_end")),
            confidence_level=metadata.get("confidence_level", "medium"),
            token_count=token_count,
            created_at=datetime.utcnow()
        )
        self.db.add(doc)

    async def _store_claims(self, doc_id: str, claims: list) -> int:
        """Store extracted claims."""
        for claim_data in claims:
            claim = SQLClaim(
                document_id=doc_id,
                claim_text=claim_data.get("claim_text", ""),
                claim_type=claim_data.get("claim_type", "fact"),
                topic=claim_data.get("topic", ""),
                confidence=claim_data.get("confidence", "medium"),
                source_section=claim_data.get("source_section", ""),
                is_quantitative=claim_data.get("is_quantitative", False),
                can_be_verified=claim_data.get("can_be_verified", True)
            )
            self.db.add(claim)
        return len(claims)

    async def _store_metrics(self, doc_id: str, metrics: list) -> int:
        """Store extracted metrics."""
        for metric_data in metrics:
            metric = SQLMetric(
                document_id=doc_id,
                metric_name=metric_data.get("metric_name", ""),
                value=metric_data.get("value", ""),
                numeric_value=metric_data.get("numeric_value"),
                unit=metric_data.get("unit", ""),
                period=metric_data.get("period", ""),
                period_start=self._parse_date(metric_data.get("period_start")),
                period_end=self._parse_date(metric_data.get("period_end")),
                context=metric_data.get("context", ""),
                comparison_base=metric_data.get("comparison_base"),
                entity_name=metric_data.get("entity_name", ""),
                category=metric_data.get("category", "other")
            )
            self.db.add(metric)
        return len(metrics)

    async def _store_entities(self, doc_id: str, entities: list) -> int:
        """Store extracted entities."""
        for entity_data in entities:
            entity = SQLEntity(
                document_id=doc_id,
                entity_name=entity_data.get("entity_name", ""),
                entity_type=entity_data.get("entity_type", "organization"),
                role=entity_data.get("role", "mentioned"),
                title=entity_data.get("title"),
                context=entity_data.get("context", "")
            )
            self.db.add(entity)
        return len(entities)

    async def _store_topics(self, doc_id: str, topics: list) -> int:
        """Store document topics."""
        for topic_data in topics:
            topic = SQLTopic(
                document_id=doc_id,
                topic_name=topic_data.get("topic_name", ""),
                is_primary=topic_data.get("is_primary", False)
            )
            self.db.add(topic)
        return len(topics)

    async def _store_chunks(self, doc_id: str, chunks: list):
        """Store text chunks for fallback."""
        for i, chunk in enumerate(chunks):
            db_chunk = SQLDocumentChunk(
                document_id=doc_id,
                chunk_index=i,
                section_name=chunk.get("section", ""),
                chunk_text=chunk.get("content", ""),
                token_count=chunk.get("token_count", 0)
            )
            self.db.add(db_chunk)

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None


def get_structured_extractor(db: AsyncSession) -> StructuredExtractor:
    """Get structured extractor instance."""
    return StructuredExtractor(db)
