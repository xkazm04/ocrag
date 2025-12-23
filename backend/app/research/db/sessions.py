"""Research session database operations."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from supabase import Client

from .client import BaseSupabaseDB
from ..schemas import ResearchSession


class SessionOperations(BaseSupabaseDB):
    """Database operations for research sessions."""

    async def create_session(
        self,
        title: str,
        query: str,
        template_type: str,
        parameters: Dict[str, Any],
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ResearchSession:
        """Create a new research session."""
        data = {
            "title": title,
            "query": query,
            "template_type": template_type,
            "parameters": parameters,
            "workspace_id": workspace_id or self.workspace_id,
            "user_id": user_id,
            "status": "active",
        }

        result = self.client.table("research_sessions").insert(data).execute()

        if result.data:
            return self._row_to_session(result.data[0])
        raise Exception("Failed to create research session")

    async def get_session(self, session_id: UUID) -> Optional[ResearchSession]:
        """Get a research session by ID."""
        result = (
            self.client.table("research_sessions")
            .select("*")
            .eq("id", str(session_id))
            .execute()
        )

        if result.data:
            return self._row_to_session(result.data[0])
        return None

    async def update_session_status(self, session_id: UUID, status: str) -> None:
        """Update session status."""
        data = {"status": status}
        if status == "completed":
            data["completed_at"] = datetime.utcnow().isoformat()

        self.client.table("research_sessions").update(data).eq(
            "id", str(session_id)
        ).execute()

    async def complete_session(self, session_id: UUID) -> None:
        """Mark a session as completed."""
        await self.update_session_status(session_id, "completed")

    async def list_sessions(
        self,
        workspace_id: Optional[str] = None,
        template_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ResearchSession]:
        """List research sessions with filters."""
        query = self.client.table("research_sessions").select("*")

        if workspace_id:
            query = query.eq("workspace_id", workspace_id)
        if template_type:
            query = query.eq("template_type", template_type)
        if status:
            query = query.eq("status", status)

        result = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return [self._row_to_session(row) for row in result.data]

    async def delete_session(self, session_id: UUID) -> None:
        """Delete a session and all related data (cascade)."""
        self.client.table("research_sessions").delete().eq(
            "id", str(session_id)
        ).execute()

    def _row_to_session(self, row: Dict[str, Any]) -> ResearchSession:
        """Convert database row to ResearchSession."""
        return ResearchSession(
            id=row["id"],
            user_id=row.get("user_id"),
            workspace_id=row["workspace_id"],
            title=row["title"],
            query=row["query"],
            template_type=row["template_type"],
            status=row["status"],
            parameters=row.get("parameters", {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row.get("completed_at"),
        )
