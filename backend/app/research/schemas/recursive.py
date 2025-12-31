"""Schemas for recursive chain-of-investigation research."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class FollowUpType(str, Enum):
    """Types of follow-up questions generated during recursive research."""
    PREDECESSOR = "predecessor"      # What caused/enabled this?
    CONSEQUENCE = "consequence"      # What resulted from this?
    DETAIL = "detail"                # More specific information
    VERIFICATION = "verification"    # Confirm/verify this claim
    FINANCIAL = "financial"          # Follow money trail
    TEMPORAL = "temporal"            # What happened before/after?


class NodeStatus(str, Enum):
    """Status of a research node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class TreeStatus(str, Enum):
    """Status of a research tree."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SkipReason(str, Enum):
    """Reasons for skipping a research node."""
    DUPLICATE = "duplicate"
    SATURATED = "saturated"
    DEPTH_LIMIT = "depth_limit"
    IRRELEVANT = "irrelevant"
    MAX_NODES = "max_nodes"


# ============================================
# Configuration
# ============================================

class RecursiveResearchConfig(BaseModel):
    """Configuration for recursive research execution."""
    depth_limit: int = Field(default=5, ge=1, le=10, description="Maximum depth of recursion")
    saturation_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Stop when saturation exceeds this")
    max_nodes: int = Field(default=50, ge=1, le=200, description="Maximum total nodes to explore")
    max_follow_ups_per_node: int = Field(default=5, ge=1, le=10, description="Max follow-up questions per node")
    follow_up_types: List[FollowUpType] = Field(
        default=[FollowUpType.PREDECESSOR, FollowUpType.CONSEQUENCE],
        description="Types of follow-ups to generate"
    )
    min_priority_score: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum priority to pursue follow-up")
    parallel_nodes: int = Field(default=3, ge=1, le=10, description="Max nodes to process in parallel per depth")


# ============================================
# Request Schemas
# ============================================

class StartRecursiveResearchRequest(BaseModel):
    """Request to start a new recursive research session."""
    query: str = Field(..., min_length=5, description="The initial research query")
    workspace_id: str = Field(default="default", description="Workspace identifier")
    config: Optional[RecursiveResearchConfig] = Field(default=None, description="Custom configuration")
    template_type: str = Field(default="investigative", description="Research template to use")
    focus_entities: Optional[List[str]] = Field(default=None, description="Entities to prioritize in follow-ups")


# ============================================
# Follow-up Schemas
# ============================================

class FollowUpQuestion(BaseModel):
    """A generated follow-up question."""
    id: Optional[UUID] = None
    query: str = Field(..., description="The follow-up question")
    follow_up_type: FollowUpType = Field(..., description="Type of follow-up")
    priority_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Priority 0-1")
    reasoning: str = Field(..., description="Why this follow-up was generated")
    source_finding_id: Optional[UUID] = Field(default=None, description="Finding that triggered this")
    status: str = Field(default="pending", description="Current status")


class GeneratedFollowUps(BaseModel):
    """Collection of generated follow-up questions from a node."""
    node_id: UUID
    follow_ups: List[FollowUpQuestion]
    total_generated: int
    filtered_count: int  # After applying priority threshold


# ============================================
# Node Schemas
# ============================================

class NodeFinding(BaseModel):
    """A finding extracted from a research node."""
    id: Optional[UUID] = None
    content: str
    finding_type: str = "fact"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_strength: str = "medium"
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    entities_mentioned: List[str] = Field(default_factory=list)
    temporal_context: Dict[str, Any] = Field(default_factory=dict)
    is_duplicate: bool = False


class ResearchNodeStatus(BaseModel):
    """Status of a single research node."""
    id: UUID
    query: str
    query_type: str
    depth: int
    status: NodeStatus
    saturation_score: float = 0.0
    findings_count: int = 0
    new_entities_count: int = 0
    children_count: int = 0
    skip_reason: Optional[SkipReason] = None
    execution_time_ms: Optional[int] = None


class ResearchNodeDetail(ResearchNodeStatus):
    """Detailed information about a research node including findings."""
    parent_node_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    findings: List[NodeFinding] = Field(default_factory=list)
    follow_ups_generated: List[FollowUpQuestion] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ============================================
# Tree Schemas
# ============================================

class ResearchTreeStatus(BaseModel):
    """Current status of a research tree."""
    tree_id: UUID
    root_query: str
    status: TreeStatus
    total_nodes: int
    completed_nodes: int
    pending_nodes: int
    max_depth_reached: int
    progress_pct: float
    current_depth_nodes: List[ResearchNodeStatus] = Field(default_factory=list)
    estimated_cost_usd: float = 0.0
    total_tokens_used: int = 0


class ResearchTreeSummary(BaseModel):
    """Summary of a completed research tree."""
    tree_id: UUID
    root_query: str
    status: TreeStatus
    config: RecursiveResearchConfig
    total_nodes: int
    completed_nodes: int
    skipped_nodes: int
    max_depth_reached: int
    total_findings: int
    total_entities_discovered: int
    duration_seconds: float
    total_tokens_used: int
    estimated_cost_usd: float
    created_at: datetime
    completed_at: Optional[datetime] = None


class ReasoningChain(BaseModel):
    """A chain of questions from root to a leaf node."""
    chain_id: UUID  # ID of the leaf node
    queries: List[str]
    query_types: List[str]
    depth: int
    key_findings: List[str] = Field(default_factory=list)


class ResearchTreeResult(BaseModel):
    """Complete results of a recursive research session."""
    tree_id: UUID
    root_query: str
    config: RecursiveResearchConfig
    status: TreeStatus

    # Statistics
    total_nodes: int
    completed_nodes: int
    skipped_nodes: int
    max_depth_reached: int
    total_findings: int
    total_entities_discovered: int

    # Key outputs
    key_insights: List[str] = Field(default_factory=list)
    reasoning_chains: List[ReasoningChain] = Field(default_factory=list)

    # Metrics
    duration_seconds: float
    total_tokens_used: int
    estimated_cost_usd: float

    # Timestamps
    created_at: datetime
    completed_at: Optional[datetime] = None


# ============================================
# Response Schemas
# ============================================

class RecursiveResearchSubmitResponse(BaseModel):
    """Response when submitting recursive research as background job."""
    tree_id: UUID
    status: str = "pending"
    message: str = "Recursive research submitted successfully"


class TreeNodesResponse(BaseModel):
    """Response with list of tree nodes."""
    tree_id: UUID
    total_nodes: int
    nodes: List[ResearchNodeStatus]
    filter_depth: Optional[int] = None
    filter_status: Optional[str] = None
