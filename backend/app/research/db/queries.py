"""Research query database operations."""

from typing import Optional, Dict, Any
from uuid import UUID

from .client import BaseSupabaseDB
from ..schemas import ResearchQuery


class QueryOperations(BaseSupabaseDB):
    """Database operations for research queries."""

    async def save_query(
        self,
        session_id: UUID,
        query_text: str,
        query_purpose: Optional[str] = None,
        query_round: int = 1,
        execution_time_ms: Optional[int] = None,
        result_count: int = 0,
        grounding_metadata: Optional[Dict[str, Any]] = None,
    ) -> ResearchQuery:
        """Save a search query."""
        data = {
            "session_id": str(session_id),
            "query_text": query_text,
            "query_purpose": query_purpose,
            "query_round": query_round,
            "execution_time_ms": execution_time_ms,
            "result_count": result_count,
            "grounding_metadata": grounding_metadata,
        }

        result = self.client.table("research_queries").insert(data).execute()

        if result.data:
            return self._row_to_query(result.data[0])
        raise Exception("Failed to save query")

    def _row_to_query(self, row: Dict[str, Any]) -> ResearchQuery:
        """Convert database row to ResearchQuery."""
        return ResearchQuery(
            id=row["id"],
            session_id=row["session_id"],
            query_text=row["query_text"],
            query_purpose=row.get("query_purpose"),
            query_round=row["query_round"],
            executed_at=row["executed_at"],
            execution_time_ms=row.get("execution_time_ms"),
            result_count=row["result_count"],
            grounding_metadata=row.get("grounding_metadata"),
        )
