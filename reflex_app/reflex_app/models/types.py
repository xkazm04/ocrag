"""Data types for the Investigation Board.

Ported from TypeScript interfaces in detective_board/types.ts
"""
from typing import Optional, Literal
from pydantic import BaseModel


# Type aliases
RiskLevel = Literal["minimal", "low", "medium", "high", "critical"]
ActorStatus = Literal["active", "inactive", "detained", "missing", "deceased", "surveillance"]
ConnectionType = Literal["financial", "travel", "communication", "business", "personal", "criminal", "family"]
EventType = Literal["transaction", "meeting", "travel", "document", "arrest", "evidence", "witness", "incident"]
EventSeverity = Literal["info", "low", "medium", "high", "critical"]


class Actor(BaseModel):
    """Individual person in the investigation."""
    id: str
    name: str
    alias: Optional[str] = None
    role: str
    organization: Optional[str] = None
    risk_level: RiskLevel
    status: ActorStatus
    photo_url: Optional[str] = None
    last_known_location: Optional[str] = None
    last_activity: Optional[str] = None
    notes: Optional[str] = None


class Connection(BaseModel):
    """Relationship between actors."""
    id: str
    source_id: str  # Primary suspect or actor ID
    target_id: str  # Actor ID
    type: ConnectionType
    strength: int  # 1-10 scale
    label: str
    description: Optional[str] = None
    date_established: Optional[str] = None
    last_activity: Optional[str] = None
    evidence: Optional[list[str]] = None
    amount: Optional[str] = None
    is_confirmed: bool


class TimelineEvent(BaseModel):
    """Historical incident in the case."""
    id: str
    date: str
    timestamp: Optional[str] = None
    title: str
    description: str
    type: EventType
    severity: EventSeverity
    actors_involved: list[str]
    location: Optional[str] = None
    evidence: Optional[list[str]] = None
    amount: Optional[str] = None
    is_key_event: Optional[bool] = False


class TimelineMarker(BaseModel):
    """Month/year grouping for timeline."""
    year: str
    month: Optional[str] = None
    event_count: int
    is_active: bool
    severity: EventSeverity


class CaseInsight(BaseModel):
    """AI-generated insight about the case."""
    id: str
    type: Literal["pattern", "anomaly", "prediction", "warning"]
    title: str
    description: str
    confidence: int
    related_actors: Optional[list[str]] = None
    priority: Literal["low", "medium", "high"]


class CaseSummary(BaseModel):
    """Summary statistics for the case."""
    total_connections: int
    confirmed_connections: int
    suspicious_activities: int
    total_actors: int
    high_risk_actors: int
    documents_analyzed: int
    evidence_count: int
    ai_confidence: int
    estimated_value: str
    case_progress: int  # 0-100


class InvestigationCase(BaseModel):
    """Complete investigation case data."""
    case_id: str
    case_name: str
    case_code: str
    status: Literal["open", "active", "pending", "closed", "archived"]
    priority: Literal["low", "medium", "high", "urgent"]
    created_date: str
    last_updated: str
    primary_suspect: Actor
    actors: list[Actor]
    connections: list[Connection]
    events: list[TimelineEvent]
    timeline: list[TimelineMarker]
    insights: list[CaseInsight]
    summary: CaseSummary


class ActorPosition(BaseModel):
    """Position for actor placement on the board."""
    x: float
    y: float
    angle: float
    ring: int  # 1 = inner ring, 2 = outer ring
    actor_id: str
