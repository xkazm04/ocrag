"""Research finding database operations."""

from typing import Optional, List, Dict, Any
from uuid import UUID

from .client import BaseSupabaseDB
from ..schemas import Finding


class FindingOperations(BaseSupabaseDB):
    """Database operations for research findings."""

    async def save_findings(
        self, session_id: UUID, findings: List[Finding]
    ) -> List[Finding]:
        """Save multiple findings."""
        if not findings:
            return []

        data = [
            {
                "session_id": str(session_id),
                "finding_type": f.finding_type,
                "content": f.content,
                "summary": f.summary,
                "perspective": f.perspective,
                "confidence_score": f.confidence_score,
                "supporting_sources": (
                    [str(s) for s in f.supporting_sources]
                    if f.supporting_sources
                    else None
                ),
                "temporal_context": f.temporal_context,
                "event_date": f.event_date.isoformat() if f.event_date else None,
                "extracted_data": f.extracted_data,
            }
            for f in findings
        ]

        result = self.client.table("research_findings").insert(data).execute()

        return [self._row_to_finding(row) for row in result.data]

    async def get_findings(
        self,
        session_id: UUID,
        finding_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
    ) -> List[Finding]:
        """Get findings for a session."""
        query = (
            self.client.table("research_findings")
            .select("*")
            .eq("session_id", str(session_id))
        )

        if finding_type:
            query = query.eq("finding_type", finding_type)
        if min_confidence is not None:
            query = query.gte("confidence_score", min_confidence)

        result = query.order("confidence_score", desc=True).execute()

        return [self._row_to_finding(row) for row in result.data]

    async def get_finding(self, finding_id: UUID) -> Optional[Finding]:
        """Get a single finding by ID."""
        result = (
            self.client.table("research_findings")
            .select("*")
            .eq("id", str(finding_id))
            .execute()
        )

        if result.data:
            return self._row_to_finding(result.data[0])
        return None

    async def update_finding(
        self, finding_id: UUID, updates: Dict[str, Any]
    ) -> Finding:
        """Update a finding."""
        result = (
            self.client.table("research_findings")
            .update(updates)
            .eq("id", str(finding_id))
            .execute()
        )

        if result.data:
            return self._row_to_finding(result.data[0])
        raise Exception("Failed to update finding")

    def _row_to_finding(self, row: Dict[str, Any]) -> Finding:
        """Convert database row to Finding."""
        return Finding(
            id=row["id"],
            session_id=row["session_id"],
            finding_type=row["finding_type"],
            content=row["content"],
            summary=row.get("summary"),
            perspective=row.get("perspective"),
            confidence_score=row.get("confidence_score", 0.5),
            temporal_context=row.get("temporal_context"),
            event_date=row.get("event_date"),
            extracted_data=row.get("extracted_data"),
            created_at=row.get("created_at"),
        )
