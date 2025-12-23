"""Research session and related schemas."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class ResearchParameters(BaseModel):
    """Parameters for research configuration."""
    max_searches: int = Field(default=5, ge=1, le=20)
    max_sources_per_search: int = Field(default=10, ge=1, le=30)
    granularity: str = Field(default="standard")  # quick, standard, deep
    perspectives: List[str] = Field(default=["historical", "economic", "political"])
    use_cache: bool = Field(default=True)


class ResearchRequest(BaseModel):
    """Request to start a new research session."""
    query: str = Field(..., min_length=10, description="Research question or topic")
    title: Optional[str] = Field(default=None, description="Optional title")
    template_type: str = Field(default="investigative")
    parameters: ResearchParameters = Field(default_factory=ResearchParameters)
    workspace_id: str = Field(default="default")


class ContinueResearchRequest(BaseModel):
    """Request to continue research with additional queries."""
    additional_queries: List[str] = Field(..., min_length=1)


class ResearchProgress(BaseModel):
    """Progress update during research."""
    status: str
    message: str
    session_id: Optional[UUID] = None
    phase: Optional[int] = None
    total_phases: Optional[int] = None
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    is_cached: bool = False


class ResearchQuery(BaseModel):
    """A search query executed during research."""
    id: Optional[UUID] = None
    session_id: UUID
    query_text: str
    query_purpose: Optional[str] = None
    query_round: int = 1
    executed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None
    result_count: int = 0
    model_used: str = "gemini-2.0-flash"
    grounding_metadata: Optional[Dict[str, Any]] = None


class ResearchSession(BaseModel):
    """A complete research session."""
    id: UUID
    user_id: Optional[str] = None
    workspace_id: str = "default"
    title: str
    query: str
    template_type: str
    status: str = "active"
    parameters: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    # Optional nested data (populated on detail requests)
    queries: Optional[List[ResearchQuery]] = None
    sources: Optional[List["Source"]] = None
    findings: Optional[List["Finding"]] = None
    perspectives: Optional[List["Perspective"]] = None


class ResearchSessionList(BaseModel):
    """List of research sessions."""
    sessions: List[ResearchSession]
    total: int
    offset: int
    limit: int


# Forward references for type hints
from .sources import Source
from .findings import Finding, Perspective

ResearchSession.model_rebuild()
