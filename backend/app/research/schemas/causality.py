"""Schemas for temporal causality analysis."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from datetime import datetime
from enum import Enum


class CausalityType(str, Enum):
    """Types of causal relationships."""
    CAUSED_BY = "caused_by"           # Direct causation
    ENABLED_BY = "enabled_by"         # Necessary condition
    PREVENTED_BY = "prevented_by"     # Blocked outcome
    TRIGGERED_BY = "triggered_by"     # Immediate trigger
    PRECEDED = "preceded"             # Temporal only (no causation)
    RESULTED_IN = "resulted_in"       # Consequence
    CONTRIBUTED_TO = "contributed_to" # Partial cause


class CausalMechanism(str, Enum):
    """Mechanisms by which causality operates."""
    FINANCIAL = "financial"           # Money enabled/caused
    LEGAL = "legal"                   # Legal authority/constraint
    ORGANIZATIONAL = "organizational" # Hierarchy/control
    INFORMATIONAL = "informational"   # Knowledge transfer
    SOCIAL = "social"                 # Relationship/trust
    PHYSICAL = "physical"             # Physical presence/action
    POLITICAL = "political"           # Political power/influence


class PatternType(str, Enum):
    """Types of causal patterns."""
    ENABLING_NETWORK = "enabling_network"   # Multiple entities enabling outcome
    COVER_UP = "cover_up"                   # Actions to hide wrongdoing
    ESCALATION = "escalation"               # Progressive worsening
    RETALIATION = "retaliation"             # Response to threats
    PROTECTION = "protection"               # Mutual protection
    OBSTRUCTION = "obstruction"             # Blocking investigation
    MONEY_LAUNDERING = "money_laundering"   # Financial obfuscation
    RECRUITMENT = "recruitment"             # Bringing in new participants


# ============================================
# Causal Link Schemas
# ============================================

class CausalLink(BaseModel):
    """A causal relationship between two events/claims."""
    id: Optional[UUID] = None
    source_event: str
    source_claim_id: Optional[UUID] = None
    target_event: str
    target_claim_id: Optional[UUID] = None
    causality_type: CausalityType
    confidence: float = Field(ge=0.0, le=1.0)
    mechanism: Optional[CausalMechanism] = None
    temporal_gap_days: Optional[int] = None
    reasoning: str
    counterfactual: Optional[str] = None  # "If X hadn't happened, Y would not have occurred"
    evidence: List[str] = Field(default_factory=list)


class CausalLinkCreate(BaseModel):
    """Request to create a causal link."""
    source_event: str = Field(..., min_length=5)
    source_claim_id: Optional[UUID] = None
    target_event: str = Field(..., min_length=5)
    target_claim_id: Optional[UUID] = None
    causality_type: CausalityType
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    mechanism: Optional[CausalMechanism] = None
    reasoning: str = Field(..., min_length=10)
    counterfactual: Optional[str] = None
    workspace_id: str = "default"


# ============================================
# Causal Chain Schemas
# ============================================

class CausalChain(BaseModel):
    """A chain of causally connected events."""
    chain_id: Optional[UUID] = None
    chain_type: str  # cause_chain, consequence_chain, enabling_chain
    events: List[str]  # Human-readable event descriptions
    claim_ids: List[UUID] = Field(default_factory=list)
    links: List[CausalLink] = Field(default_factory=list)
    total_confidence: float = Field(ge=0.0, le=1.0)
    chain_length: int
    narrative: str  # "A led to B, which enabled C, resulting in D"
    time_span_days: Optional[int] = None


class CausalChainSummary(BaseModel):
    """Summary of a causal chain for list views."""
    chain_id: UUID
    chain_type: str
    chain_length: int
    total_confidence: float
    start_event: str
    end_event: str
    narrative: str


# ============================================
# Causal Pattern Schemas
# ============================================

class CausalPattern(BaseModel):
    """A detected causal pattern."""
    pattern_id: Optional[UUID] = None
    pattern_name: str
    pattern_type: PatternType
    description: str
    involved_entities: List[str] = Field(default_factory=list)
    involved_entity_ids: List[UUID] = Field(default_factory=list)
    events: List[str] = Field(default_factory=list)
    claim_ids: List[UUID] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    occurrences: int = 1
    first_detected_at: Optional[datetime] = None


class PatternSummary(BaseModel):
    """Summary of patterns by type."""
    pattern_type: PatternType
    pattern_count: int
    avg_confidence: float
    total_occurrences: int
    pattern_names: List[str] = Field(default_factory=list)


# ============================================
# Causal Graph Schemas
# ============================================

class GraphNode(BaseModel):
    """A node in a causal graph."""
    id: str
    label: str
    type: str  # claim_type
    date: Optional[str] = None
    entity_mentions: List[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    """An edge in a causal graph."""
    source: str
    target: str
    type: str  # causality_type
    confidence: float
    mechanism: Optional[str] = None


class CausalGraph(BaseModel):
    """A complete causal graph for a topic."""
    topic: str
    topic_id: Optional[UUID] = None
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    key_causes: List[str] = Field(default_factory=list)  # Root causes
    key_consequences: List[str] = Field(default_factory=list)  # Final outcomes
    patterns_detected: List[CausalPattern] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0


# ============================================
# Request Schemas
# ============================================

class ExtractCausalityRequest(BaseModel):
    """Request to extract causality between two events."""
    event_a: str = Field(..., min_length=5, description="First event description")
    event_a_claim_id: Optional[UUID] = None
    event_b: str = Field(..., min_length=5, description="Second event description")
    event_b_claim_id: Optional[UUID] = None
    context: Optional[str] = None  # Additional context
    workspace_id: str = "default"


class FindCausesRequest(BaseModel):
    """Request to find causes of an event."""
    event: str = Field(..., min_length=5)
    event_claim_id: Optional[UUID] = None
    max_depth: int = Field(default=5, ge=1, le=10)
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    include_indirect: bool = True
    workspace_id: str = "default"


class FindConsequencesRequest(BaseModel):
    """Request to find consequences of an event."""
    event: str = Field(..., min_length=5)
    event_claim_id: Optional[UUID] = None
    max_depth: int = Field(default=5, ge=1, le=10)
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    include_indirect: bool = True
    workspace_id: str = "default"


class BuildCausalGraphRequest(BaseModel):
    """Request to build a causal graph for a topic."""
    topic: str = Field(..., min_length=3)
    topic_id: Optional[UUID] = None
    entity_focus: Optional[List[str]] = None  # Focus on specific entities
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    max_nodes: int = Field(default=100, ge=10, le=500)
    workspace_id: str = "default"


class DetectPatternsRequest(BaseModel):
    """Request to detect causal patterns."""
    topic_id: Optional[UUID] = None
    entity_ids: Optional[List[UUID]] = None
    pattern_types: Optional[List[PatternType]] = None  # Filter to specific types
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    workspace_id: str = "default"


# ============================================
# Response Schemas
# ============================================

class FindCausesResponse(BaseModel):
    """Response from finding causes."""
    event: str
    event_claim_id: Optional[UUID] = None
    direct_causes: List[CausalLink] = Field(default_factory=list)
    causal_chains: List[CausalChain] = Field(default_factory=list)
    root_causes: List[str] = Field(default_factory=list)  # Ultimate causes
    total_causes_found: int = 0
    max_depth_reached: int = 0


class FindConsequencesResponse(BaseModel):
    """Response from finding consequences."""
    event: str
    event_claim_id: Optional[UUID] = None
    direct_consequences: List[CausalLink] = Field(default_factory=list)
    consequence_chains: List[CausalChain] = Field(default_factory=list)
    final_outcomes: List[str] = Field(default_factory=list)  # Terminal consequences
    total_consequences_found: int = 0
    max_depth_reached: int = 0


class CausalityExtractionResponse(BaseModel):
    """Response from causality extraction."""
    event_a: str
    event_b: str
    has_causal_relationship: bool
    causal_link: Optional[CausalLink] = None
    alternative_interpretations: List[str] = Field(default_factory=list)


class CausalChainsResponse(BaseModel):
    """Response with causal chains for a claim."""
    claim_id: UUID
    as_cause: List[CausalChainSummary] = Field(default_factory=list)
    as_consequence: List[CausalChainSummary] = Field(default_factory=list)
    in_chain: List[CausalChainSummary] = Field(default_factory=list)
    total_chains: int = 0


class DetectPatternsResponse(BaseModel):
    """Response from pattern detection."""
    patterns: List[CausalPattern] = Field(default_factory=list)
    summary_by_type: List[PatternSummary] = Field(default_factory=list)
    total_patterns: int = 0
