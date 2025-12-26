"""Response schemas for knowledge base API."""

from __future__ import annotations

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from uuid import UUID
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .knowledge import KnowledgeTopic, KnowledgeEntity, KnowledgeClaim
    from .relationships import ClaimRelationship


class TopicTreeResponse(BaseModel):
    """Hierarchical topic tree response."""
    topics: List[KnowledgeTopic]
    total_count: int


class ClaimSearchRequest(BaseModel):
    """Request to search claims."""
    query: Optional[str] = None
    topic_id: Optional[UUID] = None
    entity_id: Optional[UUID] = None
    claim_types: Optional[List[str]] = None
    verification_status: Optional[str] = None
    min_confidence: Optional[float] = None
    include_relationships: bool = False
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ClaimSearchResponse(BaseModel):
    """Response from claim search."""
    claims: List[KnowledgeClaim]
    total: int
    limit: int
    offset: int


class CausalChainResponse(BaseModel):
    """Response for causal chain query."""
    root_claim: KnowledgeClaim
    chain: List[Dict[str, Any]]
    max_depth: int


class RelatedClaimsResponse(BaseModel):
    """Response for related claims query."""
    claim: KnowledgeClaim
    relationships: List[ClaimRelationship]
    by_type: Dict[str, List[ClaimRelationship]]


class EntityClaimsResponse(BaseModel):
    """Response for entity's claims."""
    entity: KnowledgeEntity
    claims: List[KnowledgeClaim]
    total: int


class SimilarClaimsRequest(BaseModel):
    """Request to find similar claims."""
    content: str = Field(..., min_length=10)
    threshold: float = Field(default=0.85, ge=0.5, le=1.0)
    limit: int = Field(default=10, ge=1, le=50)
    exclude_claim_id: Optional[UUID] = None


class SimilarClaimsResponse(BaseModel):
    """Response from similar claims search."""
    similar_claims: List[Dict[str, Any]]


class PromoteToKnowledgeBaseRequest(BaseModel):
    """Request to promote a finding to the knowledge base."""
    finding_id: UUID
    topic_id: Optional[UUID] = None
    claim_type: str = "fact"
    visibility: str = "public"


class MergeClaimsRequest(BaseModel):
    """Request to merge duplicate claims."""
    source_claim_id: UUID
    target_claim_id: UUID
    keep_both_sources: bool = True


class TemplateInfo(BaseModel):
    """Information about a research template."""
    id: str
    name: str
    description: str
    default_perspectives: List[str]
    default_max_searches: int
    available: bool = True


class CacheStats(BaseModel):
    """Statistics about research cache."""
    total_entries: int
    hit_count: int
    expired_entries: int
    cache_size_mb: float
