"""Knowledge claim database operations."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from .client import BaseSupabaseDB
from ..schemas import KnowledgeClaim, KnowledgeClaimCreate


class ClaimOperations(BaseSupabaseDB):
    """Database operations for knowledge claims."""

    async def create_claim(
        self,
        claim: KnowledgeClaimCreate,
        embedding: Optional[List[float]] = None,
        user_id: Optional[str] = None,
    ) -> KnowledgeClaim:
        """Create a new knowledge claim."""
        content_hash = self.hash_string(claim.content)

        data = {
            "claim_type": claim.claim_type,
            "content": claim.content,
            "summary": claim.summary,
            "content_hash": content_hash,
            "topic_id": str(claim.topic_id) if claim.topic_id else None,
            "tags": claim.tags or [],
            "confidence_score": claim.confidence_score,
            "temporal_context": claim.temporal_context,
            "event_date": claim.event_date.isoformat() if claim.event_date else None,
            "date_range_start": (
                claim.date_range_start.isoformat() if claim.date_range_start else None
            ),
            "date_range_end": (
                claim.date_range_end.isoformat() if claim.date_range_end else None
            ),
            "extracted_data": claim.extracted_data,
            "visibility": claim.visibility,
            "workspace_id": claim.workspace_id,
            "created_by_user_id": user_id,
        }

        if embedding:
            data["embedding"] = embedding

        result = self.client.table("knowledge_claims").insert(data).execute()

        if result.data:
            return self._row_to_claim(result.data[0])
        raise Exception("Failed to create claim")

    async def get_claim(self, claim_id: UUID) -> Optional[KnowledgeClaim]:
        """Get a claim by ID."""
        result = (
            self.client.table("knowledge_claims")
            .select("*")
            .eq("id", str(claim_id))
            .execute()
        )

        if result.data:
            return self._row_to_claim(result.data[0])
        return None

    async def search_claims(
        self,
        query: Optional[str] = None,
        topic_id: Optional[UUID] = None,
        claim_types: Optional[List[str]] = None,
        verification_status: Optional[str] = None,
        min_confidence: Optional[float] = None,
        visibility: str = "public",
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[KnowledgeClaim], int]:
        """Search claims with filters. Returns (claims, total_count)."""
        q = (
            self.client.table("knowledge_claims")
            .select("*", count="exact")
            .eq("is_current", True)
        )

        if visibility != "all":
            q = q.eq("visibility", visibility)
        if query:
            q = q.ilike("content", f"%{query}%")
        if topic_id:
            q = q.eq("topic_id", str(topic_id))
        if claim_types:
            q = q.in_("claim_type", claim_types)
        if verification_status:
            q = q.eq("verification_status", verification_status)
        if min_confidence is not None:
            q = q.gte("confidence_score", min_confidence)

        result = (
            q.order("confidence_score", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        total = result.count if result.count else len(result.data)
        claims = [self._row_to_claim(row) for row in result.data]

        return claims, total

    async def get_claims_by_topic(
        self, topic_id: UUID, limit: int = 50
    ) -> List[KnowledgeClaim]:
        """Get all claims for a topic."""
        result = (
            self.client.table("knowledge_claims")
            .select("*")
            .eq("is_current", True)
            .eq("topic_id", str(topic_id))
            .order("confidence_score", desc=True)
            .limit(limit)
            .execute()
        )

        return [self._row_to_claim(row) for row in result.data]

    async def update_claim(
        self, claim_id: UUID, updates: Dict[str, Any]
    ) -> KnowledgeClaim:
        """Update a claim."""
        updates["updated_at"] = datetime.utcnow().isoformat()

        result = (
            self.client.table("knowledge_claims")
            .update(updates)
            .eq("id", str(claim_id))
            .execute()
        )

        if result.data:
            return self._row_to_claim(result.data[0])
        raise Exception("Failed to update claim")

    async def update_claim_embedding(
        self, claim_id: UUID, embedding: List[float]
    ) -> None:
        """Update the embedding for a claim."""
        self.client.table("knowledge_claims").update(
            {"embedding": embedding}
        ).eq("id", str(claim_id)).execute()

    async def verify_claim(self, claim_id: UUID, status: str) -> KnowledgeClaim:
        """Update claim verification status."""
        return await self.update_claim(claim_id, {"verification_status": status})

    def _row_to_claim(self, row: Dict[str, Any]) -> KnowledgeClaim:
        """Convert database row to KnowledgeClaim."""
        return KnowledgeClaim(
            id=row["id"],
            claim_type=row["claim_type"],
            content=row["content"],
            summary=row.get("summary"),
            content_hash=row["content_hash"],
            topic_id=row.get("topic_id"),
            tags=row.get("tags") or [],
            confidence_score=row.get("confidence_score", 0.5),
            verification_status=row.get("verification_status", "unverified"),
            corroboration_count=row.get("corroboration_count", 0),
            temporal_context=row.get("temporal_context"),
            event_date=row.get("event_date"),
            date_range_start=row.get("date_range_start"),
            date_range_end=row.get("date_range_end"),
            visibility=row.get("visibility", "public"),
            created_by_user_id=row.get("created_by_user_id"),
            workspace_id=row.get("workspace_id", "default"),
            version=row.get("version", 1),
            superseded_by=row.get("superseded_by"),
            is_current=row.get("is_current", True),
            extracted_data=row.get("extracted_data"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
