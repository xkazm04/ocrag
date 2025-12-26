"""Database operations for key insights management."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from supabase import Client

from .client import BaseSupabaseDB


class InsightOperations(BaseSupabaseDB):
    """Operations for key_insights table."""

    async def create_insight(
        self,
        insight_text: str,
        insight_category: str,
        importance_level: str = "notable",
        discoverability: str = "moderate",
        perspective_id: Optional[UUID] = None,
        finding_id: Optional[UUID] = None,
        claim_id: Optional[UUID] = None,
        insight_summary: Optional[str] = None,
        analyst_notes: Optional[str] = None,
        follow_up_needed: bool = False,
        related_entities: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new key insight."""
        data = {
            "insight_text": insight_text,
            "insight_category": insight_category,
            "importance_level": importance_level,
            "discoverability": discoverability,
            "follow_up_needed": follow_up_needed,
        }

        if perspective_id:
            data["perspective_id"] = str(perspective_id)
        if finding_id:
            data["finding_id"] = str(finding_id)
        if claim_id:
            data["claim_id"] = str(claim_id)
        if insight_summary:
            data["insight_summary"] = insight_summary
        if analyst_notes:
            data["analyst_notes"] = analyst_notes
        if related_entities:
            data["related_entities"] = related_entities

        result = self.client.table("key_insights").insert(data).execute()
        return result.data[0] if result.data else {}

    async def get_insight(self, insight_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a single insight by ID."""
        result = (
            self.client.table("key_insights")
            .select("*")
            .eq("id", str(insight_id))
            .execute()
        )
        return result.data[0] if result.data else None

    async def list_insights(
        self,
        category: Optional[str] = None,
        importance: Optional[str] = None,
        discoverability: Optional[str] = None,
        verification_status: Optional[str] = None,
        follow_up_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List insights with optional filters."""
        query = self.client.table("key_insights").select("*")

        if category:
            query = query.eq("insight_category", category)
        if importance:
            query = query.eq("importance_level", importance)
        if discoverability:
            query = query.eq("discoverability", discoverability)
        if verification_status:
            query = query.eq("verification_status", verification_status)
        if follow_up_only:
            query = query.eq("follow_up_needed", True)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        return result.data

    async def get_hidden_gems(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get insights marked as hidden gems - the non-obvious discoveries."""
        result = (
            self.client.table("key_insights")
            .select("*")
            .eq("discoverability", "hidden_gem")
            .order("importance_level", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data

    async def get_critical_insights(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get critical importance insights."""
        result = (
            self.client.table("key_insights")
            .select("*")
            .eq("importance_level", "critical")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    async def update_insight(
        self, insight_id: UUID, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an insight."""
        result = (
            self.client.table("key_insights")
            .update(updates)
            .eq("id", str(insight_id))
            .execute()
        )
        return result.data[0] if result.data else {}

    async def verify_insight(
        self, insight_id: UUID, status: str, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update verification status of an insight."""
        updates = {"verification_status": status}
        if notes:
            updates["analyst_notes"] = notes
        return await self.update_insight(insight_id, updates)

    async def mark_follow_up(
        self, insight_id: UUID, needed: bool, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark insight for follow-up."""
        updates = {"follow_up_needed": needed}
        if notes:
            updates["follow_up_notes"] = notes
        return await self.update_insight(insight_id, updates)

    async def delete_insight(self, insight_id: UUID) -> bool:
        """Delete an insight."""
        result = (
            self.client.table("key_insights")
            .delete()
            .eq("id", str(insight_id))
            .execute()
        )
        return len(result.data) > 0


class InsightTagOperations(BaseSupabaseDB):
    """Operations for insight tags."""

    async def create_tag(
        self,
        tag_name: str,
        description: Optional[str] = None,
        color: str = "#6B7280",
    ) -> Dict[str, Any]:
        """Create a new tag."""
        data = {"tag_name": tag_name, "tag_color": color}
        if description:
            data["tag_description"] = description

        result = self.client.table("insight_tags").insert(data).execute()
        return result.data[0] if result.data else {}

    async def list_tags(self) -> List[Dict[str, Any]]:
        """List all available tags."""
        result = self.client.table("insight_tags").select("*").execute()
        return result.data

    async def tag_insight(self, insight_id: UUID, tag_id: UUID) -> bool:
        """Add a tag to an insight."""
        data = {"insight_id": str(insight_id), "tag_id": str(tag_id)}
        try:
            self.client.table("insight_tag_links").insert(data).execute()
            return True
        except Exception:
            return False

    async def untag_insight(self, insight_id: UUID, tag_id: UUID) -> bool:
        """Remove a tag from an insight."""
        result = (
            self.client.table("insight_tag_links")
            .delete()
            .eq("insight_id", str(insight_id))
            .eq("tag_id", str(tag_id))
            .execute()
        )
        return len(result.data) > 0

    async def get_insight_tags(self, insight_id: UUID) -> List[Dict[str, Any]]:
        """Get all tags for an insight."""
        result = (
            self.client.table("insight_tag_links")
            .select("tag_id, insight_tags(*)")
            .eq("insight_id", str(insight_id))
            .execute()
        )
        return [r["insight_tags"] for r in result.data if r.get("insight_tags")]


class InsightConnectionOperations(BaseSupabaseDB):
    """Operations for insight connections."""

    async def connect_insights(
        self,
        from_id: UUID,
        to_id: UUID,
        connection_type: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a connection between two insights."""
        data = {
            "insight_from_id": str(from_id),
            "insight_to_id": str(to_id),
            "connection_type": connection_type,
        }
        if notes:
            data["connection_notes"] = notes

        result = self.client.table("insight_connections").insert(data).execute()
        return result.data[0] if result.data else {}

    async def get_connected_insights(self, insight_id: UUID) -> Dict[str, List[Dict]]:
        """Get all insights connected to this one."""
        # Outgoing connections
        outgoing = (
            self.client.table("insight_connections")
            .select("*, key_insights!insight_to_id(*)")
            .eq("insight_from_id", str(insight_id))
            .execute()
        )

        # Incoming connections
        incoming = (
            self.client.table("insight_connections")
            .select("*, key_insights!insight_from_id(*)")
            .eq("insight_to_id", str(insight_id))
            .execute()
        )

        return {"outgoing": outgoing.data, "incoming": incoming.data}

    async def disconnect_insights(
        self, from_id: UUID, to_id: UUID, connection_type: Optional[str] = None
    ) -> bool:
        """Remove connection between insights."""
        query = (
            self.client.table("insight_connections")
            .delete()
            .eq("insight_from_id", str(from_id))
            .eq("insight_to_id", str(to_id))
        )
        if connection_type:
            query = query.eq("connection_type", connection_type)

        result = query.execute()
        return len(result.data) > 0
