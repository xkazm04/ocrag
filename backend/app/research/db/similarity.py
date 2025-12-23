"""Similarity and deduplication database operations."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from .client import BaseSupabaseDB
from ..schemas import SimilarityCandidate, KnowledgeClaim, FindingClaim


class SimilarityOperations(BaseSupabaseDB):
    """Database operations for similarity detection and deduplication."""

    async def find_similar_claims(
        self,
        embedding: List[float],
        threshold: float = 0.85,
        limit: int = 10,
        exclude_claim_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """Find claims similar to the given embedding."""
        params = {
            "claim_embedding": embedding,
            "similarity_threshold": threshold,
            "limit_count": limit,
        }
        if exclude_claim_id:
            params["exclude_claim_id"] = str(exclude_claim_id)

        result = self.client.rpc("find_similar_claims", params).execute()
        return result.data if result.data else []

    async def create_candidate(
        self,
        claim_id: UUID,
        similar_claim_id: UUID,
        similarity_score: float,
        similarity_type: str = "semantic",
    ) -> SimilarityCandidate:
        """Create a similarity candidate for review."""
        data = {
            "claim_id": str(claim_id),
            "similar_claim_id": str(similar_claim_id),
            "similarity_score": similarity_score,
            "similarity_type": similarity_type,
            "status": "pending",
        }

        result = (
            self.client.table("similarity_candidates")
            .upsert(data, on_conflict="claim_id,similar_claim_id")
            .execute()
        )

        if result.data:
            row = result.data[0]
            return SimilarityCandidate(
                id=row["id"],
                claim_id=row["claim_id"],
                similar_claim_id=row["similar_claim_id"],
                similarity_score=row["similarity_score"],
                similarity_type=row.get("similarity_type"),
                status=row["status"],
                created_at=row["created_at"],
            )
        raise Exception("Failed to create similarity candidate")

    async def get_pending_candidates(self, limit: int = 20) -> List[SimilarityCandidate]:
        """Get pending similarity candidates for review."""
        result = (
            self.client.table("similarity_candidates")
            .select("*")
            .eq("status", "pending")
            .order("similarity_score", desc=True)
            .limit(limit)
            .execute()
        )

        return [
            SimilarityCandidate(
                id=row["id"],
                claim_id=row["claim_id"],
                similar_claim_id=row["similar_claim_id"],
                similarity_score=row["similarity_score"],
                similarity_type=row.get("similarity_type"),
                status=row["status"],
                reviewed_by_user_id=row.get("reviewed_by_user_id"),
                reviewed_at=row.get("reviewed_at"),
                created_at=row["created_at"],
            )
            for row in result.data
        ]

    async def resolve_candidate(
        self,
        candidate_id: UUID,
        status: str,
        user_id: Optional[str] = None,
    ) -> None:
        """Resolve a similarity candidate."""
        self.client.table("similarity_candidates").update({
            "status": status,
            "reviewed_by_user_id": user_id,
            "reviewed_at": datetime.utcnow().isoformat(),
        }).eq("id", str(candidate_id)).execute()


class FindingClaimOperations(BaseSupabaseDB):
    """Database operations for finding-claim links."""

    async def link_finding_to_claim(
        self,
        finding_id: UUID,
        claim_id: UUID,
        link_type: str = "created",
        match_score: Optional[float] = None,
    ) -> FindingClaim:
        """Link a research finding to a knowledge claim."""
        data = {
            "finding_id": str(finding_id),
            "claim_id": str(claim_id),
            "link_type": link_type,
            "match_score": match_score,
        }

        result = (
            self.client.table("finding_claims")
            .upsert(data, on_conflict="finding_id,claim_id")
            .execute()
        )

        if result.data:
            row = result.data[0]
            return FindingClaim(
                id=row["id"],
                finding_id=row["finding_id"],
                claim_id=row["claim_id"],
                link_type=row.get("link_type"),
                match_score=row.get("match_score"),
                created_at=row["created_at"],
            )
        raise Exception("Failed to link finding to claim")

    async def get_finding_claim_ids(self, finding_id: UUID) -> List[UUID]:
        """Get claim IDs linked to a finding."""
        result = (
            self.client.table("finding_claims")
            .select("claim_id")
            .eq("finding_id", str(finding_id))
            .execute()
        )
        return [row["claim_id"] for row in result.data] if result.data else []

    async def mark_finding_promoted(
        self, finding_id: UUID, claim_id: UUID
    ) -> None:
        """Mark a finding as promoted to knowledge base."""
        self.client.table("research_findings").update({
            "knowledge_claim_id": str(claim_id),
            "is_promoted": True,
        }).eq("id", str(finding_id)).execute()
