"""Research perspective database operations."""

from typing import List, Dict, Any
from uuid import UUID

from .client import BaseSupabaseDB
from ..schemas import Perspective


class PerspectiveOperations(BaseSupabaseDB):
    """Database operations for research perspectives."""

    async def save_perspective(
        self, session_id: UUID, perspective: Perspective
    ) -> Perspective:
        """Save an analysis perspective."""
        data = {
            "session_id": str(session_id),
            "perspective_type": perspective.perspective_type,
            "analysis_text": perspective.analysis_text,
            "key_insights": perspective.key_insights,
            "confidence": perspective.confidence,
            "findings_analyzed": (
                [str(f) for f in perspective.findings_analyzed]
                if perspective.findings_analyzed
                else None
            ),
            "sources_cited": (
                [str(s) for s in perspective.sources_cited]
                if perspective.sources_cited
                else None
            ),
            "recommendations": perspective.recommendations,
            "warnings": perspective.warnings,
        }

        result = self.client.table("research_perspectives").insert(data).execute()

        if result.data:
            return self._row_to_perspective(result.data[0])
        raise Exception("Failed to save perspective")

    async def get_perspectives(self, session_id: UUID) -> List[Perspective]:
        """Get all perspectives for a session."""
        result = (
            self.client.table("research_perspectives")
            .select("*")
            .eq("session_id", str(session_id))
            .execute()
        )

        return [self._row_to_perspective(row) for row in result.data]

    def _row_to_perspective(self, row: Dict[str, Any]) -> Perspective:
        """Convert database row to Perspective."""
        return Perspective(
            id=row["id"],
            session_id=row["session_id"],
            perspective_type=row["perspective_type"],
            analysis_text=row["analysis_text"],
            key_insights=row.get("key_insights", []),
            confidence=row.get("confidence", 0.5),
            recommendations=row.get("recommendations", []),
            warnings=row.get("warnings", []),
            created_at=row.get("created_at"),
        )
