"""Schemas for Knowledge Explorer API endpoints.

Covers 5 key features:
1. Network Graph - Entity relationships visualization
2. Timeline - Chronological event reconstruction
3. Evidence Corroboration - Multi-source verification
4. Pattern Mining - Anomaly and pattern detection
5. Investigative Q&A - RAG-powered question answering
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# NETWORK GRAPH SCHEMAS
# =============================================================================


class GraphNode(BaseModel):
    """Node in the knowledge graph."""
    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Display label")
    type: str = Field(..., description="Node type: person, organization, location, claim")
    size: int = Field(default=10, description="Node size based on importance/connections")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional node data")


class GraphEdge(BaseModel):
    """Edge connecting two nodes."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: Optional[str] = Field(None, description="Relationship label")
    weight: float = Field(default=1.0, description="Edge weight/strength")
    type: str = Field(default="related", description="Relationship type")


class GraphData(BaseModel):
    """Complete graph data structure."""
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class NetworkGraphRequest(BaseModel):
    """Request for network graph data."""
    workspace_id: str = Field(default="default")
    entity_ids: Optional[List[UUID]] = Field(None, description="Specific entities to focus on")
    entity_types: Optional[List[str]] = Field(None, description="Filter by entity types")
    include_claims: bool = Field(default=False, description="Include claim nodes")
    max_nodes: int = Field(default=100, ge=10, le=500)
    min_connections: int = Field(default=1, description="Minimum connections for a node")
    depth: int = Field(default=2, ge=1, le=4, description="Relationship depth to explore")


class NetworkGraphResponse(BaseModel):
    """Response with graph data."""
    graph: GraphData
    stats: Dict[str, int] = Field(default_factory=dict)
    clusters: List[Dict[str, Any]] = Field(default_factory=list, description="Detected communities")


# =============================================================================
# TIMELINE SCHEMAS
# =============================================================================


class TimelineEvent(BaseModel):
    """Single event in the timeline."""
    id: UUID
    date: Optional[str] = Field(default=None, description="Event date (YYYY-MM-DD)")
    date_range_start: Optional[str] = Field(default=None)
    date_range_end: Optional[str] = Field(default=None)
    title: str = Field(..., description="Event title/summary")
    description: Optional[str] = Field(default=None, description="Full description")
    claim_type: str = Field(..., description="Type of claim")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    entities: List[Dict[str, str]] = Field(default_factory=list, description="Related entities with roles")
    sources_count: int = Field(default=0)
    tags: List[str] = Field(default_factory=list)


class TimelineRequest(BaseModel):
    """Request for timeline data."""
    workspace_id: str = Field(default="default")
    topic_id: Optional[UUID] = Field(default=None)
    entity_ids: Optional[List[UUID]] = Field(default=None, description="Filter by related entities")
    start_date: Optional[str] = Field(default=None, description="Start date YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="End date YYYY-MM-DD")
    claim_types: Optional[List[str]] = Field(default=None)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class TimelineResponse(BaseModel):
    """Response with timeline events."""
    events: List[TimelineEvent]
    total: int
    date_range: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Actual date range covered"
    )
    entity_activity: Dict[str, int] = Field(
        default_factory=dict,
        description="Event counts per entity"
    )


# =============================================================================
# EVIDENCE CORROBORATION SCHEMAS
# =============================================================================


class SourceEvidence(BaseModel):
    """Evidence from a single source."""
    source_type: str = Field(..., description="document, web, claim")
    source_path: Optional[str] = None
    excerpt: Optional[str] = None
    support_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: Optional[datetime] = None


class CorroborationResult(BaseModel):
    """Corroboration analysis for a claim."""
    claim_id: UUID
    claim_content: str
    claim_summary: Optional[str] = None

    # Corroboration metrics
    source_count: int = Field(default=0)
    unique_source_types: int = Field(default=0)
    average_support_strength: float = Field(default=0.0)
    corroboration_score: float = Field(default=0.0, description="Overall corroboration strength 0-1")

    # Related evidence
    supporting_sources: List[SourceEvidence] = Field(default_factory=list)
    related_claims: List[Dict[str, Any]] = Field(default_factory=list)

    # Flags
    is_well_sourced: bool = Field(default=False, description="Has 3+ independent sources")
    has_document_evidence: bool = Field(default=False)
    has_web_evidence: bool = Field(default=False)


class CorroborationRequest(BaseModel):
    """Request to analyze evidence corroboration."""
    workspace_id: str = Field(default="default")
    claim_ids: Optional[List[UUID]] = Field(None, description="Specific claims to analyze")
    topic_id: Optional[UUID] = Field(None, description="Analyze all claims in topic")
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    min_source_count: int = Field(default=2, ge=1, description="Minimum sources to be 'well-sourced'")
    limit: int = Field(default=50, ge=1, le=200)


class CorroborationResponse(BaseModel):
    """Response with corroboration analysis."""
    results: List[CorroborationResult]
    summary: Dict[str, Any] = Field(default_factory=dict)
    well_sourced_count: int = Field(default=0)
    weak_sourced_count: int = Field(default=0)


# =============================================================================
# PATTERN MINING SCHEMAS
# =============================================================================


class PatternType(str, Enum):
    """Types of patterns that can be detected."""
    ENTITY_CLUSTER = "entity_cluster"  # Entities frequently appearing together
    TEMPORAL_BURST = "temporal_burst"  # Spike in activity during a period
    DOCUMENT_TYPE_CLUSTER = "document_type_cluster"  # Related doc types
    LOCATION_PATTERN = "location_pattern"  # Geographic patterns
    RELATIONSHIP_CHAIN = "relationship_chain"  # Chain of connections
    ANOMALY = "anomaly"  # Unusual patterns


class DetectedPattern(BaseModel):
    """A detected pattern in the data."""
    pattern_id: str
    pattern_type: PatternType
    title: str = Field(..., description="Human-readable pattern title")
    description: str = Field(..., description="Pattern explanation")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    significance: float = Field(default=0.5, description="How notable is this pattern")

    # Pattern-specific data
    involved_entities: List[Dict[str, str]] = Field(default_factory=list)
    involved_claims: List[UUID] = Field(default_factory=list)
    time_range: Optional[Dict[str, str]] = None

    # Supporting evidence
    evidence_count: int = Field(default=0)
    example_claims: List[str] = Field(default_factory=list, max_length=5)


class PatternMiningRequest(BaseModel):
    """Request to mine patterns in the knowledge base."""
    workspace_id: str = Field(default="default")
    topic_id: Optional[UUID] = None
    pattern_types: Optional[List[PatternType]] = Field(None, description="Types to look for")
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    min_evidence_count: int = Field(default=3, ge=2)
    limit: int = Field(default=20, ge=1, le=100)


class PatternMiningResponse(BaseModel):
    """Response with detected patterns."""
    patterns: List[DetectedPattern]
    stats: Dict[str, int] = Field(default_factory=dict)
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# INVESTIGATIVE Q&A SCHEMAS
# =============================================================================


class Citation(BaseModel):
    """Citation for a Q&A response."""
    claim_id: UUID
    content_snippet: str = Field(..., max_length=300)
    confidence: float
    source_documents: List[str] = Field(default_factory=list)
    entities_mentioned: List[str] = Field(default_factory=list)


class InvestigativeQuestion(BaseModel):
    """Request for investigative Q&A."""
    question: str = Field(..., min_length=10, max_length=1000)
    workspace_id: str = Field(default="default")
    topic_id: Optional[UUID] = None
    require_citations: bool = Field(default=True)
    min_citation_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    max_citations: int = Field(default=10, ge=1, le=50)
    include_analysis: bool = Field(default=True, description="Include analytical perspectives")


class InvestigativeAnswer(BaseModel):
    """Response to an investigative question."""
    question: str
    answer: str = Field(..., description="Generated answer")
    confidence: float = Field(default=0.5, description="Overall answer confidence")

    # Citations
    citations: List[Citation] = Field(default_factory=list)
    citation_coverage: float = Field(
        default=0.0,
        description="How much of the answer is backed by citations"
    )

    # Analysis
    key_entities: List[Dict[str, str]] = Field(default_factory=list)
    timeline_context: Optional[str] = None
    gaps_identified: List[str] = Field(
        default_factory=list,
        description="Identified gaps in knowledge"
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        max_length=5
    )

    # Metadata
    claims_searched: int = Field(default=0)
    processing_time_ms: int = Field(default=0)


# =============================================================================
# ENTITY PROFILE SCHEMAS
# =============================================================================


class EntityProfile(BaseModel):
    """Comprehensive profile for an entity."""
    id: UUID
    canonical_name: str
    entity_type: str
    aliases: List[str] = Field(default_factory=list)
    description: Optional[str] = None

    # Statistics
    mention_count: int = Field(default=0)
    claim_count: int = Field(default=0)

    # Connections
    connected_entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Related entities with relationship info"
    )

    # Timeline
    first_mention_date: Optional[str] = Field(default=None)
    last_mention_date: Optional[str] = Field(default=None)
    activity_timeline: List[Dict[str, Any]] = Field(default_factory=list)

    # Key claims
    key_claims: List[Dict[str, Any]] = Field(default_factory=list)
    roles_played: List[str] = Field(default_factory=list)


class EntityProfileRequest(BaseModel):
    """Request for entity profile."""
    entity_id: UUID
    workspace_id: str = Field(default="default")
    include_connections: bool = Field(default=True)
    include_timeline: bool = Field(default=True)
    include_claims: bool = Field(default=True)
    max_connections: int = Field(default=20, ge=1, le=100)
    max_claims: int = Field(default=20, ge=1, le=100)
