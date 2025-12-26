"""Async job schemas for research API."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of an async research job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStage(str, Enum):
    """Processing stages for research jobs."""
    HEALTH_CHECK = "health_check"
    TOPIC_MATCHING = "topic_matching"
    DECOMPOSITION = "decomposition"
    SEARCHING = "searching"
    EXTRACTION = "extraction"
    PERSPECTIVES = "perspectives"
    RELATIONSHIPS = "relationships"
    DEDUPLICATION = "deduplication"
    COMPLETED = "completed"


# Progress percentages for each stage
STAGE_PROGRESS = {
    JobStage.HEALTH_CHECK: 5.0,
    JobStage.TOPIC_MATCHING: 10.0,
    JobStage.DECOMPOSITION: 20.0,
    JobStage.SEARCHING: 35.0,
    JobStage.EXTRACTION: 50.0,
    JobStage.PERSPECTIVES: 70.0,
    JobStage.RELATIONSHIPS: 85.0,
    JobStage.DEDUPLICATION: 95.0,
    JobStage.COMPLETED: 100.0,
}


class SubmitResearchRequest(BaseModel):
    """Request to submit an async research job."""
    query: str = Field(..., min_length=10, description="Research question or topic")
    workspace_id: str = Field(default="default")
    template_type: str = Field(default="investigative")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class SubmitResearchResponse(BaseModel):
    """Response from job submission."""
    job_id: Optional[UUID] = Field(default=None, description="Job ID for new jobs")
    session_id: Optional[UUID] = Field(default=None, description="Session ID if cached")
    status: JobStatus
    message: str
    cached: bool = Field(default=False, description="True if result is from cache")


class DedupStats(BaseModel):
    """Statistics from deduplication process."""
    new: int = Field(default=0, description="Findings added as new")
    updated: int = Field(default=0, description="Existing findings updated")
    discarded: int = Field(default=0, description="Duplicate findings discarded")


class JobStats(BaseModel):
    """Statistics for a completed job."""
    findings_count: int = Field(default=0)
    perspectives_count: int = Field(default=0)
    sources_count: int = Field(default=0)
    key_summary: Optional[str] = Field(default=None, description="Brief summary of research findings")
    token_usage: Dict[str, int] = Field(default_factory=dict)
    cost_usd: float = Field(default=0.0)
    duration_seconds: float = Field(default=0.0)
    topic_id: Optional[UUID] = Field(default=None, description="Matched topic ID if found")
    topic_name: Optional[str] = Field(default=None, description="Matched topic name")
    dedup_stats: Optional[DedupStats] = Field(default=None)


class JobStatusResponse(BaseModel):
    """Response for job status polling."""
    job_id: UUID
    status: JobStatus
    current_stage: Optional[str] = None
    progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    stats: Optional[JobStats] = None
    session_id: Optional[UUID] = Field(default=None, description="Research session ID when completed")


class TopicMatchResult(BaseModel):
    """Result of LLM-based topic matching."""
    topic_id: Optional[UUID] = Field(default=None, description="Matched topic ID or null")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="")


class DeduplicationAction(str, Enum):
    """Actions for deduplication decisions."""
    POST = "POST"      # Add as new finding
    PUT = "PUT"        # Update existing finding
    DISCARD = "DISCARD"  # Discard duplicate


class MergeStrategy(str, Enum):
    """Strategies for merging findings."""
    REPLACE = "replace"  # New finding replaces existing
    APPEND = "append"    # Append new content to existing
    MERGE = "merge"      # Merge complementary information


class DeduplicationDecision(BaseModel):
    """LLM decision for a finding during deduplication."""
    finding_id: str = Field(..., description="ID of the new finding")
    action: DeduplicationAction = Field(..., description="Action to take")
    existing_finding_id: Optional[UUID] = Field(
        default=None,
        description="ID of existing finding for PUT action"
    )
    merge_strategy: Optional[MergeStrategy] = Field(
        default=None,
        description="Strategy for PUT action"
    )
    reasoning: str = Field(default="")


class TopicContext(BaseModel):
    """Context from existing topic for query decomposition."""
    topic_id: UUID
    topic_name: str
    existing_claims_count: int = 0
    existing_summaries: List[str] = Field(default_factory=list)
    known_entities: List[str] = Field(default_factory=list)
    date_range: Optional[str] = None


class ResearchJob(BaseModel):
    """Full research job model."""
    id: UUID
    session_id: Optional[UUID] = None
    query: str
    workspace_id: str = "default"
    template_type: str = "investigative"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    current_stage: Optional[str] = None
    progress_pct: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    stats: Optional[Dict[str, Any]] = None
    matched_topic_id: Optional[UUID] = None
    topic_match_confidence: Optional[float] = None
    topic_match_reasoning: Optional[str] = None
