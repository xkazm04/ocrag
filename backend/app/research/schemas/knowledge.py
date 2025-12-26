"""Knowledge base core schemas: topics, entities, claims."""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================
# Knowledge Topics
# ============================================

class KnowledgeTopicBase(BaseModel):
    """Base model for knowledge topics."""
    name: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1)
    description: Optional[str] = None
    topic_type: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class KnowledgeTopicCreate(KnowledgeTopicBase):
    """Create a new knowledge topic."""
    parent_id: Optional[UUID] = None


class KnowledgeTopic(KnowledgeTopicBase):
    """A knowledge topic for categorization."""
    id: UUID
    parent_id: Optional[UUID] = None
    path: List[str] = []
    depth: int = 0
    finding_count: int = 0
    entity_count: int = 0
    last_activity_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    children: Optional[List["KnowledgeTopic"]] = None


# ============================================
# Knowledge Entities
# ============================================

class KnowledgeEntityBase(BaseModel):
    """Base model for knowledge entities."""
    canonical_name: str = Field(..., min_length=1)
    entity_type: str
    aliases: List[str] = []
    description: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    external_ids: Optional[Dict[str, str]] = None


class KnowledgeEntityCreate(KnowledgeEntityBase):
    """Create a new knowledge entity."""
    pass


class KnowledgeEntity(KnowledgeEntityBase):
    """A deduplicated knowledge entity."""
    id: UUID
    name_hash: str
    mention_count: int = 0
    finding_count: int = 0
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime


# ============================================
# Knowledge Claims
# ============================================

class KnowledgeClaimBase(BaseModel):
    """Base model for knowledge claims."""
    claim_type: str
    content: str = Field(..., min_length=10)
    summary: Optional[str] = None
    topic_id: Optional[UUID] = None
    tags: List[str] = []
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    temporal_context: Optional[str] = None
    event_date: Optional[date] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    extracted_data: Optional[Dict[str, Any]] = None


class KnowledgeClaimCreate(KnowledgeClaimBase):
    """Create a new knowledge claim."""
    visibility: str = "public"
    workspace_id: str = "default"


class KnowledgeClaim(KnowledgeClaimBase):
    """A deduplicated knowledge claim (core knowledge unit)."""
    id: UUID
    content_hash: str
    verification_status: str = "unverified"
    corroboration_count: int = 0
    visibility: str = "public"
    created_by_user_id: Optional[str] = None
    workspace_id: str = "default"
    version: int = 1
    superseded_by: Optional[UUID] = None
    is_current: bool = True
    created_at: datetime
    updated_at: datetime

    # Nested data for detailed queries
    topic: Optional[KnowledgeTopic] = None
    entities: Optional[List[KnowledgeEntity]] = None
    sources: Optional[List["ClaimSource"]] = None
    related_claims: Optional[List["ClaimRelationship"]] = None


# Note: model_rebuild() is called in __init__.py after all types are imported
