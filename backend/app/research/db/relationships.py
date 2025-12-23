"""Claim relationship and link database operations."""

from typing import Optional, List, Dict, Any
from uuid import UUID

from .client import BaseSupabaseDB
from ..schemas import (
    ClaimRelationship,
    ClaimRelationshipCreate,
    ClaimEntity,
    ClaimSource,
    KnowledgeEntity,
    KnowledgeClaim,
    FindingClaim,
)


class RelationshipOperations(BaseSupabaseDB):
    """Database operations for claim relationships."""

    async def create_relationship(
        self, relationship: ClaimRelationshipCreate, user_id: Optional[str] = None
    ) -> ClaimRelationship:
        """Create a relationship between two claims."""
        data = {
            "source_claim_id": str(relationship.source_claim_id),
            "target_claim_id": str(relationship.target_claim_id),
            "relationship_type": relationship.relationship_type,
            "strength": relationship.strength,
            "description": relationship.description,
            "created_by_session_id": (
                str(relationship.created_by_session_id)
                if relationship.created_by_session_id
                else None
            ),
            "created_by_user_id": user_id,
        }

        result = self.client.table("claim_relationships").insert(data).execute()

        if result.data:
            return self._row_to_relationship(result.data[0])
        raise Exception("Failed to create relationship")

    async def get_relationships(
        self,
        claim_id: UUID,
        relationship_type: Optional[str] = None,
        direction: str = "both",
    ) -> List[ClaimRelationship]:
        """Get relationships for a claim."""
        relationships = []

        if direction in ("outgoing", "both"):
            q = (
                self.client.table("claim_relationships")
                .select("*")
                .eq("source_claim_id", str(claim_id))
            )
            if relationship_type:
                q = q.eq("relationship_type", relationship_type)
            result = q.execute()
            relationships.extend(
                [self._row_to_relationship(row) for row in result.data]
            )

        if direction in ("incoming", "both"):
            q = (
                self.client.table("claim_relationships")
                .select("*")
                .eq("target_claim_id", str(claim_id))
            )
            if relationship_type:
                q = q.eq("relationship_type", relationship_type)
            result = q.execute()
            relationships.extend(
                [self._row_to_relationship(row) for row in result.data]
            )

        return relationships

    async def get_related_claims(
        self, claim_id: UUID
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all related claims grouped by relationship type."""
        result = self.client.rpc(
            "get_related_claims", {"claim_uuid": str(claim_id)}
        ).execute()

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in result.data:
            rel_type = row["relationship_type"]
            if rel_type not in grouped:
                grouped[rel_type] = []
            grouped[rel_type].append(row)

        return grouped

    async def get_causal_chain(
        self, claim_id: UUID, max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """Get the causal chain leading to a claim."""
        result = self.client.rpc(
            "get_causal_chain", {"claim_uuid": str(claim_id), "max_depth": max_depth}
        ).execute()
        return result.data

    async def get_consequences(
        self, claim_id: UUID, max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """Get the consequences/effects of a claim."""
        result = self.client.rpc(
            "get_consequences", {"claim_uuid": str(claim_id), "max_depth": max_depth}
        ).execute()
        return result.data

    async def delete_relationship(self, relationship_id: UUID) -> None:
        """Delete a claim relationship."""
        self.client.table("claim_relationships").delete().eq(
            "id", str(relationship_id)
        ).execute()

    def _row_to_relationship(self, row: Dict[str, Any]) -> ClaimRelationship:
        """Convert database row to ClaimRelationship."""
        return ClaimRelationship(
            id=row["id"],
            source_claim_id=row["source_claim_id"],
            target_claim_id=row["target_claim_id"],
            relationship_type=row["relationship_type"],
            strength=row.get("strength", 0.5),
            description=row.get("description"),
            created_by_session_id=row.get("created_by_session_id"),
            created_by_user_id=row.get("created_by_user_id"),
            created_at=row["created_at"],
        )


class ClaimEntityOperations(BaseSupabaseDB):
    """Database operations for claim-entity links."""

    async def link_claim_entity(
        self,
        claim_id: UUID,
        entity_id: UUID,
        role: Optional[str] = None,
        context: Optional[str] = None,
    ) -> ClaimEntity:
        """Link a claim to an entity."""
        data = {
            "claim_id": str(claim_id),
            "entity_id": str(entity_id),
            "role": role,
            "context_snippet": context,
        }

        result = (
            self.client.table("claim_entities")
            .upsert(data, on_conflict="claim_id,entity_id,role")
            .execute()
        )

        if result.data:
            row = result.data[0]
            return ClaimEntity(
                id=row["id"],
                claim_id=row["claim_id"],
                entity_id=row["entity_id"],
                role=row.get("role"),
                context_snippet=row.get("context_snippet"),
                created_at=row["created_at"],
            )
        raise Exception("Failed to link claim to entity")

    async def get_claim_entities(
        self, claim_id: UUID, entity_converter
    ) -> List[KnowledgeEntity]:
        """Get all entities linked to a claim."""
        result = (
            self.client.table("claim_entities")
            .select("*, knowledge_entities(*)")
            .eq("claim_id", str(claim_id))
            .execute()
        )

        entities = []
        for row in result.data:
            if row.get("knowledge_entities"):
                entities.append(entity_converter(row["knowledge_entities"]))
        return entities

    async def get_entity_claims(
        self, entity_id: UUID, limit: int = 50
    ) -> List[UUID]:
        """Get claim IDs for an entity."""
        result = self.client.rpc(
            "get_claims_by_entity",
            {"entity_uuid": str(entity_id), "limit_count": limit},
        ).execute()
        return [row["claim_id"] for row in result.data] if result.data else []


class ClaimSourceOperations(BaseSupabaseDB):
    """Database operations for claim sources."""

    async def add_source(
        self,
        claim_id: UUID,
        source_type: str,
        source_id: Optional[UUID] = None,
        source_claim_id: Optional[UUID] = None,
        document_id: Optional[UUID] = None,
        excerpt: Optional[str] = None,
        page_number: Optional[int] = None,
        support_strength: float = 0.5,
    ) -> ClaimSource:
        """Add a source to a claim."""
        data = {
            "claim_id": str(claim_id),
            "source_type": source_type,
            "source_id": str(source_id) if source_id else None,
            "source_claim_id": str(source_claim_id) if source_claim_id else None,
            "document_id": str(document_id) if document_id else None,
            "excerpt": excerpt,
            "page_number": page_number,
            "support_strength": support_strength,
        }

        result = self.client.table("claim_sources").insert(data).execute()

        if result.data:
            row = result.data[0]
            return ClaimSource(
                id=row["id"],
                claim_id=row["claim_id"],
                source_type=row["source_type"],
                source_id=row.get("source_id"),
                source_claim_id=row.get("source_claim_id"),
                document_id=row.get("document_id"),
                excerpt=row.get("excerpt"),
                page_number=row.get("page_number"),
                support_strength=row.get("support_strength", 0.5),
                created_at=row["created_at"],
            )
        raise Exception("Failed to add claim source")

    async def get_sources(self, claim_id: UUID) -> List[ClaimSource]:
        """Get all sources for a claim."""
        result = (
            self.client.table("claim_sources")
            .select("*")
            .eq("claim_id", str(claim_id))
            .order("support_strength", desc=True)
            .execute()
        )

        return [
            ClaimSource(
                id=row["id"],
                claim_id=row["claim_id"],
                source_type=row["source_type"],
                source_id=row.get("source_id"),
                source_claim_id=row.get("source_claim_id"),
                document_id=row.get("document_id"),
                excerpt=row.get("excerpt"),
                page_number=row.get("page_number"),
                support_strength=row.get("support_strength", 0.5),
                created_at=row["created_at"],
            )
            for row in result.data
        ]
