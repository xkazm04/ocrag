"""Knowledge topic database operations."""

from typing import Optional, List, Dict, Any
from uuid import UUID

from .client import BaseSupabaseDB
from ..schemas import KnowledgeTopic, KnowledgeTopicCreate


class TopicOperations(BaseSupabaseDB):
    """Database operations for knowledge topics."""

    async def create_topic(self, topic: KnowledgeTopicCreate) -> KnowledgeTopic:
        """Create a new knowledge topic."""
        data = {
            "name": topic.name,
            "slug": topic.slug,
            "description": topic.description,
            "topic_type": topic.topic_type,
            "icon": topic.icon,
            "color": topic.color,
            "parent_id": str(topic.parent_id) if topic.parent_id else None,
        }

        result = self.client.table("knowledge_topics").insert(data).execute()

        if result.data:
            return self._row_to_topic(result.data[0])
        raise Exception("Failed to create topic")

    async def get_topic(self, topic_id: UUID) -> Optional[KnowledgeTopic]:
        """Get a topic by ID."""
        result = (
            self.client.table("knowledge_topics")
            .select("*")
            .eq("id", str(topic_id))
            .execute()
        )

        if result.data:
            return self._row_to_topic(result.data[0])
        return None

    async def get_topic_by_slug(self, slug: str) -> Optional[KnowledgeTopic]:
        """Get a topic by slug."""
        result = (
            self.client.table("knowledge_topics")
            .select("*")
            .eq("slug", slug)
            .execute()
        )

        if result.data:
            return self._row_to_topic(result.data[0])
        return None

    async def list_topics(
        self,
        parent_id: Optional[UUID] = None,
        topic_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[KnowledgeTopic]:
        """List topics with optional filters."""
        query = self.client.table("knowledge_topics").select("*")

        if parent_id:
            query = query.eq("parent_id", str(parent_id))
        else:
            query = query.is_("parent_id", "null")

        if topic_type:
            query = query.eq("topic_type", topic_type)

        result = query.order("name").limit(limit).execute()

        return [self._row_to_topic(row) for row in result.data]

    async def get_topic_tree(
        self, root_id: Optional[UUID] = None
    ) -> List[KnowledgeTopic]:
        """Get hierarchical topic tree."""
        if root_id:
            result = self.client.rpc(
                "get_topic_descendants", {"root_topic_id": str(root_id)}
            ).execute()
        else:
            result = (
                self.client.table("knowledge_topics")
                .select("*")
                .order("depth")
                .order("name")
                .execute()
            )

        return [self._row_to_topic(row) for row in result.data]

    async def get_topic_path(self, topic_id: UUID) -> List[KnowledgeTopic]:
        """Get the path from root to this topic."""
        result = self.client.rpc(
            "get_topic_path", {"topic_uuid": str(topic_id)}
        ).execute()

        if not result.data:
            return []

        topic_ids = [row["id"] for row in result.data]
        topics_result = (
            self.client.table("knowledge_topics")
            .select("*")
            .in_("id", topic_ids)
            .execute()
        )

        topics = [self._row_to_topic(row) for row in topics_result.data]
        return sorted(topics, key=lambda t: t.depth)

    async def update_topic(
        self, topic_id: UUID, updates: Dict[str, Any]
    ) -> KnowledgeTopic:
        """Update a topic."""
        result = (
            self.client.table("knowledge_topics")
            .update(updates)
            .eq("id", str(topic_id))
            .execute()
        )

        if result.data:
            return self._row_to_topic(result.data[0])
        raise Exception("Failed to update topic")

    async def delete_topic(self, topic_id: UUID) -> None:
        """Delete a topic."""
        self.client.table("knowledge_topics").delete().eq(
            "id", str(topic_id)
        ).execute()

    def _row_to_topic(self, row: Dict[str, Any]) -> KnowledgeTopic:
        """Convert database row to KnowledgeTopic."""
        return KnowledgeTopic(
            id=row["id"],
            parent_id=row.get("parent_id"),
            name=row["name"],
            slug=row["slug"],
            description=row.get("description"),
            topic_type=row.get("topic_type"),
            icon=row.get("icon"),
            color=row.get("color"),
            path=row.get("path") or [],
            depth=row.get("depth", 0),
            finding_count=row.get("finding_count", 0),
            entity_count=row.get("entity_count", 0),
            last_activity_at=row.get("last_activity_at"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
