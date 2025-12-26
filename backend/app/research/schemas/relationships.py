"""Relationship schemas: claim relations, entity links, sources."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================
# Claim Relationships
# ============================================

class ClaimRelationshipBase(BaseModel):
    """Base model for claim relationships."""
    source_claim_id: UUID
    target_claim_id: UUID
    relationship_type: str
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    description: Optional[str] = None


class ClaimRelationshipCreate(ClaimRelationshipBase):
    """Create a claim relationship."""
    created_by_session_id: Optional[UUID] = None


class ClaimRelationship(ClaimRelationshipBase):
    """A relationship between two claims in the knowledge graph."""
    id: UUID
    created_by_session_id: Optional[UUID] = None
    created_by_user_id: Optional[str] = None
    created_at: datetime
    source_claim: Optional["KnowledgeClaim"] = None
    target_claim: Optional["KnowledgeClaim"] = None


# ============================================
# Claim-Entity Links
# ============================================

class ClaimEntityBase(BaseModel):
    """Base model for claim-entity links."""
    claim_id: UUID
    entity_id: UUID
    role: Optional[str] = None
    context_snippet: Optional[str] = None


class ClaimEntityCreate(ClaimEntityBase):
    """Create a claim-entity link."""
    pass


class ClaimEntity(ClaimEntityBase):
    """Link between a claim and an entity."""
    id: UUID
    created_at: datetime
    claim: Optional["KnowledgeClaim"] = None
    entity: Optional["KnowledgeEntity"] = None


# ============================================
# Claim Sources
# ============================================

class ClaimSourceBase(BaseModel):
    """Base model for claim sources."""
    claim_id: UUID
    source_type: str
    source_id: Optional[UUID] = None
    source_claim_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    excerpt: Optional[str] = None
    page_number: Optional[int] = None
    support_strength: float = Field(default=0.5, ge=0.0, le=1.0)


class ClaimSourceCreate(ClaimSourceBase):
    """Create a claim source."""
    pass


class ClaimSource(ClaimSourceBase):
    """Source evidence for a claim."""
    id: UUID
    created_at: datetime
    source: Optional["Source"] = None
    referenced_claim: Optional["KnowledgeClaim"] = None


# ============================================
# Finding-Claim Links
# ============================================

class FindingClaimBase(BaseModel):
    """Base model for finding-claim links."""
    finding_id: UUID
    claim_id: UUID
    link_type: Optional[str] = None
    match_score: Optional[float] = None


class FindingClaimCreate(FindingClaimBase):
    """Create a finding-claim link."""
    pass


class FindingClaim(FindingClaimBase):
    """Link between a session finding and a knowledge claim."""
    id: UUID
    created_at: datetime


# ============================================
# Similarity Candidates
# ============================================

class SimilarityCandidate(BaseModel):
    """A candidate pair for potential deduplication."""
    id: UUID
    claim_id: UUID
    similar_claim_id: UUID
    similarity_score: float
    similarity_type: Optional[str] = None
    status: str = "pending"
    reviewed_by_user_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    claim: Optional["KnowledgeClaim"] = None
    similar_claim: Optional["KnowledgeClaim"] = None
