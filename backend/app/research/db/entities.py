"""Knowledge entity database operations."""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from .client import BaseSupabaseDB
from ..schemas import KnowledgeEntity, KnowledgeEntityCreate


class EntityOperations(BaseSupabaseDB):
    """Database operations for knowledge entities."""

    async def create_entity(self, entity: KnowledgeEntityCreate) -> KnowledgeEntity:
        """Create a new knowledge entity."""
        name_hash = self.hash_string(entity.canonical_name)

        data = {
            "canonical_name": entity.canonical_name,
            "entity_type": entity.entity_type,
            "aliases": entity.aliases or [],
            "name_hash": name_hash,
            "description": entity.description,
            "profile_data": entity.profile_data,
            "image_url": entity.image_url,
            "external_ids": entity.external_ids,
        }

        result = self.client.table("knowledge_entities").insert(data).execute()

        if result.data:
            return self._row_to_entity(result.data[0])
        raise Exception("Failed to create entity")

    async def get_entity(self, entity_id: UUID) -> Optional[KnowledgeEntity]:
        """Get an entity by ID."""
        result = (
            self.client.table("knowledge_entities")
            .select("*")
            .eq("id", str(entity_id))
            .execute()
        )

        if result.data:
            return self._row_to_entity(result.data[0])
        return None

    async def find_entity_by_name(
        self, name: str, entity_type: Optional[str] = None
    ) -> Optional[KnowledgeEntity]:
        """Find an entity by exact name match."""
        name_hash = self.hash_string(name)
        query = (
            self.client.table("knowledge_entities")
            .select("*")
            .eq("name_hash", name_hash)
        )

        if entity_type:
            query = query.eq("entity_type", entity_type)

        result = query.execute()

        if result.data:
            return self._row_to_entity(result.data[0])
        return None

    async def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[KnowledgeEntity]:
        """Search entities by name (partial match)."""
        q = (
            self.client.table("knowledge_entities")
            .select("*")
            .ilike("canonical_name", f"%{query}%")
        )

        if entity_type:
            q = q.eq("entity_type", entity_type)

        result = q.order("mention_count", desc=True).limit(limit).execute()

        return [self._row_to_entity(row) for row in result.data]

    async def get_or_create_entity(
        self, name: str, entity_type: str, **kwargs
    ) -> Tuple[KnowledgeEntity, bool]:
        """Get existing entity or create new one. Returns (entity, created)."""
        existing = await self.find_entity_by_name(name, entity_type)
        if existing:
            return existing, False

        entity = KnowledgeEntityCreate(
            canonical_name=name, entity_type=entity_type, **kwargs
        )
        created = await self.create_entity(entity)
        return created, True

    async def update_entity(
        self, entity_id: UUID, updates: Dict[str, Any]
    ) -> KnowledgeEntity:
        """Update an entity."""
        result = (
            self.client.table("knowledge_entities")
            .update(updates)
            .eq("id", str(entity_id))
            .execute()
        )

        if result.data:
            return self._row_to_entity(result.data[0])
        raise Exception("Failed to update entity")

    async def increment_entity_mentions(self, entity_id: UUID) -> None:
        """Increment entity mention count."""
        self.client.rpc(
            "increment_counter",
            {
                "table_name": "knowledge_entities",
                "row_id": str(entity_id),
                "column_name": "mention_count",
            },
        ).execute()

    async def delete_entity(self, entity_id: UUID) -> bool:
        """Delete an entity and update related claims to remove references."""
        # First, remove claim_entities references
        self.client.table("claim_entities").delete().eq(
            "entity_id", str(entity_id)
        ).execute()

        # Delete the entity
        result = self.client.table("knowledge_entities").delete().eq(
            "id", str(entity_id)
        ).execute()

        return len(result.data) > 0

    async def merge_entities(
        self, target_id: UUID, source_ids: List[UUID]
    ) -> KnowledgeEntity:
        """Merge multiple entities into one. Collects aliases and deletes sources."""
        # Get target entity
        target = await self.get_entity(target_id)
        if not target:
            raise Exception(f"Target entity {target_id} not found")

        # Collect aliases from source entities
        all_aliases = set(target.aliases or [])

        for source_id in source_ids:
            source = await self.get_entity(source_id)
            if source:
                # Add source name and aliases to target aliases
                all_aliases.add(source.canonical_name)
                all_aliases.update(source.aliases or [])

                # Delete all claim_entities for this source
                # (claims retain via target entity reference)
                self.client.table("claim_entities").delete().eq(
                    "entity_id", str(source_id)
                ).execute()

                # Delete source entity
                self.client.table("knowledge_entities").delete().eq(
                    "id", str(source_id)
                ).execute()

        # Update target with merged aliases
        all_aliases.discard(target.canonical_name)  # Don't include canonical name in aliases
        updated = await self.update_entity(target_id, {"aliases": list(all_aliases)})

        return updated

    async def list_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "mention_count",
        order_desc: bool = True,
    ) -> Tuple[List[KnowledgeEntity], int]:
        """List entities with pagination. Returns (entities, total_count)."""
        query = self.client.table("knowledge_entities").select("*", count="exact")

        if entity_type:
            query = query.eq("entity_type", entity_type)

        query = query.order(order_by, desc=order_desc).range(offset, offset + limit - 1)
        result = query.execute()

        entities = [self._row_to_entity(row) for row in result.data]
        total = result.count or len(result.data)

        return entities, total

    def _row_to_entity(self, row: Dict[str, Any]) -> KnowledgeEntity:
        """Convert database row to KnowledgeEntity."""
        return KnowledgeEntity(
            id=row["id"],
            canonical_name=row["canonical_name"],
            entity_type=row["entity_type"],
            aliases=row.get("aliases") or [],
            name_hash=row["name_hash"],
            description=row.get("description"),
            profile_data=row.get("profile_data"),
            image_url=row.get("image_url"),
            external_ids=row.get("external_ids"),
            mention_count=row.get("mention_count", 0),
            finding_count=row.get("finding_count", 0),
            is_verified=row.get("is_verified", False),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
