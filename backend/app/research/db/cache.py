"""Research cache database operations."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from .client import BaseSupabaseDB
from ..schemas import ResearchSession


class CacheOperations(BaseSupabaseDB):
    """Database operations for research cache."""

    async def get_cached_session(
        self, query: str, template_type: str
    ) -> Optional[ResearchSession]:
        """Get a cached session if available and not expired."""
        query_hash = self.hash_string(query)

        result = (
            self.client.table("research_cache")
            .select("*, research_sessions(*)")
            .eq("query_hash", query_hash)
            .eq("template_type", template_type)
            .eq("workspace_id", self.workspace_id)
            .gt("cache_expires_at", datetime.utcnow().isoformat())
            .execute()
        )

        if result.data:
            cache_row = result.data[0]
            # Update hit count
            self.client.table("research_cache").update({
                "hit_count": cache_row["hit_count"] + 1,
                "last_hit_at": datetime.utcnow().isoformat(),
            }).eq("id", cache_row["id"]).execute()

            if cache_row.get("research_sessions"):
                session_row = cache_row["research_sessions"]
                return ResearchSession(
                    id=session_row["id"],
                    workspace_id=session_row["workspace_id"],
                    title=session_row["title"],
                    query=session_row["query"],
                    template_type=session_row["template_type"],
                    status=session_row["status"],
                    parameters=session_row.get("parameters", {}),
                    created_at=session_row["created_at"],
                    updated_at=session_row["updated_at"],
                )

        return None

    async def cache_session(
        self,
        query: str,
        template_type: str,
        session_id: UUID,
        ttl_hours: int = 24,
    ) -> None:
        """Cache a research session."""
        query_hash = self.hash_string(query)
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

        data = {
            "query_hash": query_hash,
            "template_type": template_type,
            "workspace_id": self.workspace_id,
            "cached_session_id": str(session_id),
            "cache_expires_at": expires_at.isoformat(),
        }

        self.client.table("research_cache").upsert(
            data, on_conflict="query_hash,template_type,workspace_id"
        ).execute()

    async def clear_cache(
        self,
        workspace_id: Optional[str] = None,
        template_type: Optional[str] = None,
    ) -> None:
        """Clear research cache."""
        query = self.client.table("research_cache").delete()

        if workspace_id:
            query = query.eq("workspace_id", workspace_id)
        if template_type:
            query = query.eq("template_type", template_type)

        query.execute()

    async def get_cache_stats(self, workspace_id: str) -> Dict[str, Any]:
        """Get cache statistics."""
        result = (
            self.client.table("research_cache")
            .select("*")
            .eq("workspace_id", workspace_id)
            .execute()
        )

        total = len(result.data)
        hit_count = sum(row.get("hit_count", 0) for row in result.data)
        expired = sum(
            1
            for row in result.data
            if datetime.fromisoformat(
                row["cache_expires_at"].replace("Z", "+00:00")
            ) < datetime.utcnow()
        )

        return {
            "total_entries": total,
            "hit_count": hit_count,
            "expired_entries": expired,
            "cache_size_mb": 0.0,
        }
