"""Finding and perspective schemas."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class Finding(BaseModel):
    """An extracted research finding."""
    id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    finding_type: str
    content: str
    summary: Optional[str] = None
    perspective: Optional[str] = None
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_sources: List[UUID] = []
    temporal_context: Optional[str] = None
    event_date: Optional[date] = None
    related_findings: List[UUID] = []
    contradicts: List[UUID] = []
    extracted_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class Perspective(BaseModel):
    """An expert perspective analysis."""
    id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    perspective_type: str
    analysis_text: str
    key_insights: List[str] = []
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    findings_analyzed: List[UUID] = []
    sources_cited: List[UUID] = []
    recommendations: List[str] = []
    warnings: List[str] = []
    created_at: Optional[datetime] = None
