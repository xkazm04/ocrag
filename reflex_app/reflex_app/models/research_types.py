"""Pydantic models for research data in Reflex app."""

from typing import Optional, List, Dict, Any, Tuple, Literal
from datetime import datetime
from pydantic import BaseModel


# ============================================================================
# Board Visualization Models (for Next-Gen Detective Board)
# ============================================================================

FindingType = Literal["event", "actor", "relationship", "pattern", "evidence", "gap"]
RiskLevel = Literal["minimal", "low", "medium", "high", "critical"]
EventSeverity = Literal["info", "low", "medium", "high", "critical"]
ConnectionType = Literal["political", "military", "economic", "diplomatic", "conflict", "alliance", "support"]


class BoardActor(BaseModel):
    """Actor entity extracted from research findings."""
    id: str
    name: str
    role: Optional[str] = None
    organization: Optional[str] = None
    first_mentioned_date: Optional[str] = None  # ISO date for timeline reveal
    mention_count: int = 0
    risk_level: RiskLevel = "medium"
    is_primary: bool = False
    summary: Optional[str] = None
    photo_url: Optional[str] = None


class BoardEvent(BaseModel):
    """Event extracted from research findings/timeline."""
    id: str
    title: str
    summary: str
    content: str
    date: str  # ISO date for sorting
    date_text: str  # Human readable date
    precision: str = "exact"  # exact, month, year
    confidence: float = 1.0
    actors_involved: List[str] = []  # actor IDs
    severity: EventSeverity = "medium"
    finding_type: FindingType = "event"


class BoardConnection(BaseModel):
    """Relationship between actors/entities."""
    id: str
    source_id: str
    target_id: str
    type: ConnectionType
    label: str
    description: Optional[str] = None
    strength: int = 5  # 1-10
    first_established_date: Optional[str] = None


class BoardPerspective(BaseModel):
    """Expert perspective analysis."""
    type: str
    analysis: str
    insights: List[str] = []
    recommendations: List[str] = []
    warnings: List[str] = []
    confidence: float = 1.0


class PerspectiveView(BaseModel):
    """Precomputed perspective data for Reflex rendering."""
    type: str
    type_upper: str
    analysis: str
    analysis_truncated: str
    insights: List[str] = []
    recommendations: List[str] = []
    warnings: List[str] = []
    confidence: float = 1.0
    has_insights: bool = False
    has_recommendations: bool = False
    has_warnings: bool = False


class BoardSource(BaseModel):
    """Research source with credibility info."""
    title: str
    url: str
    domain: str
    snippet: Optional[str] = None
    credibility_score: float = 0.5


class BoardData(BaseModel):
    """Complete board visualization data."""
    case_name: str
    query: str
    timestamp: str
    primary_actor: Optional[BoardActor] = None
    actors: List[BoardActor] = []
    events: List[BoardEvent] = []
    connections: List[BoardConnection] = []
    perspectives: List[BoardPerspective] = []
    sources: List[BoardSource] = []
    date_range: Tuple[str, str] = ("", "")  # (earliest_date, latest_date)
    finding_count: int = 0
    source_count: int = 0


# ============================================================================
# Original Research Models (for API integration)
# ============================================================================

class ResearchSource(BaseModel):
    """A web source discovered during research."""
    id: Optional[str] = None
    url: str
    title: Optional[str] = None
    domain: Optional[str] = None
    snippet: Optional[str] = None
    credibility_score: Optional[float] = None
    credibility_factors: Optional[Dict[str, float]] = None
    source_type: Optional[str] = None


class ResearchFinding(BaseModel):
    """An extracted research finding."""
    id: Optional[str] = None
    finding_type: str
    content: str
    summary: Optional[str] = None
    perspective: Optional[str] = None
    confidence_score: float = 0.5
    temporal_context: Optional[str] = None


class ResearchPerspective(BaseModel):
    """An expert perspective analysis."""
    id: Optional[str] = None
    perspective_type: str
    analysis_text: str
    key_insights: List[str] = []
    confidence: float = 0.5
    recommendations: List[str] = []
    warnings: List[str] = []


class ResearchSession(BaseModel):
    """A complete research session."""
    id: str
    title: str
    query: str
    template_type: str
    status: str = "active"
    parameters: Dict[str, Any] = {}
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class ResearchProgress(BaseModel):
    """Progress update during research."""
    status: str
    message: str
    session_id: Optional[str] = None
    phase: Optional[int] = None
    total_phases: Optional[int] = None
    progress: float = 0.0
    is_cached: bool = False


class ResearchTemplate(BaseModel):
    """Information about a research template."""
    id: str
    name: str
    description: str
    default_perspectives: List[str] = []
    default_max_searches: int = 5
    available: bool = True
