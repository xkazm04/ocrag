"""Research source database operations."""

from typing import Optional, List, Dict, Any
from uuid import UUID

from .client import BaseSupabaseDB
from ..schemas import Source


class SourceOperations(BaseSupabaseDB):
    """Database operations for research sources."""

    async def save_sources(
        self,
        session_id: UUID,
        sources: List[Source],
        query_id: Optional[UUID] = None,
    ) -> List[Source]:
        """Save multiple sources (upsert by URL)."""
        if not sources:
            return []

        data = [
            {
                "session_id": str(session_id),
                "query_id": str(query_id) if query_id else None,
                "url": s.url,
                "title": s.title,
                "domain": s.domain,
                "snippet": s.snippet,
                "credibility_score": s.credibility_score,
                "credibility_factors": s.credibility_factors,
                "source_type": s.source_type,
                "content_date": s.content_date.isoformat() if s.content_date else None,
            }
            for s in sources
        ]

        result = (
            self.client.table("research_sources")
            .upsert(data, on_conflict="session_id,url")
            .execute()
        )

        return [self._row_to_source(row) for row in result.data]

    async def get_sources(
        self,
        session_id: UUID,
        min_credibility: Optional[float] = None,
        source_type: Optional[str] = None,
    ) -> List[Source]:
        """Get sources for a session."""
        query = (
            self.client.table("research_sources")
            .select("*")
            .eq("session_id", str(session_id))
        )

        if min_credibility is not None:
            query = query.gte("credibility_score", min_credibility)
        if source_type:
            query = query.eq("source_type", source_type)

        result = query.order("credibility_score", desc=True).execute()

        return [self._row_to_source(row) for row in result.data]

    def _row_to_source(self, row: Dict[str, Any]) -> Source:
        """Convert database row to Source."""
        return Source(
            id=row["id"],
            url=row["url"],
            title=row.get("title"),
            domain=row.get("domain"),
            snippet=row.get("snippet"),
            credibility_score=row.get("credibility_score"),
            credibility_factors=row.get("credibility_factors"),
            source_type=row.get("source_type"),
            content_date=row.get("content_date"),
            discovered_at=row.get("discovered_at"),
        )
