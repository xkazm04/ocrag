"""Verification and evidence extraction schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# =============================================================================
# VERIFICATION SCHEMAS
# =============================================================================


class VerificationVerdict(str, Enum):
    """Verdict for fact-check verification."""
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"


class EvidenceItem(BaseModel):
    """A piece of evidence found during verification."""
    source_url: str
    source_title: Optional[str] = None
    source_domain: Optional[str] = None
    excerpt: str
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    supports_statement: bool


class RelatedClaimSummary(BaseModel):
    """Summary of a related claim from the knowledge base."""
    claim_id: UUID
    content: str
    verification_status: str
    confidence_score: float
    relationship: str  # 'supports', 'contradicts', 'related'


class VerifyStatementRequest(BaseModel):
    """Request to verify/fact-check a statement."""
    statement: str = Field(..., min_length=10, max_length=2000)
    workspace_id: str = Field(default="default")
    use_cache: bool = Field(default=True)
    cache_ttl_hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 7 days
    include_related_claims: bool = Field(default=True)
    max_sources: int = Field(default=10, ge=1, le=50)


class VerifyStatementResponse(BaseModel):
    """Response from statement verification."""
    verification_id: UUID
    statement: str
    verdict: VerificationVerdict
    confidence_score: float = Field(ge=0.0, le=1.0)
    supporting_evidence: List[EvidenceItem] = Field(default_factory=list)
    contradicting_evidence: List[EvidenceItem] = Field(default_factory=list)
    related_claims: List[RelatedClaimSummary] = Field(default_factory=list)
    related_claims_summary: Optional[str] = None
    sources_analyzed: int = 0
    cached: bool = False
    processing_time_ms: int = 0


# =============================================================================
# EVIDENCE EXTRACTION SCHEMAS
# =============================================================================


class FindingQuality(str, Enum):
    """Quality level of an extracted finding."""
    HIGH = "high"        # confidence >= 0.8 AND content >= 100 chars
    MEDIUM = "medium"    # confidence >= 0.6
    LOW = "low"          # passes minimum thresholds
    FILTERED = "filtered"  # did not pass quality filter


class ExtractedFinding(BaseModel):
    """A finding extracted from a document with quality assessment."""
    finding_id: str
    content: str
    summary: Optional[str] = None
    finding_type: str = "fact"
    confidence_score: float = Field(default=0.7, ge=0.0, le=1.0)

    # Quality assessment
    quality: FindingQuality
    quality_reasons: List[str] = Field(default_factory=list)

    # Deduplication decision
    action: str  # POST, PUT, SKIP
    existing_claim_id: Optional[UUID] = None
    merge_strategy: Optional[str] = None  # replace, append, merge
    dedup_reasoning: Optional[str] = None

    # Web context (optional)
    web_context: Optional[str] = None
    web_sources: List[Dict[str, str]] = Field(default_factory=list)

    # Perspectives (optional)
    perspectives: List[Dict[str, Any]] = Field(default_factory=list)


class ExtractionStats(BaseModel):
    """Statistics from document extraction."""
    total_extracted: int = 0
    passed_quality_filter: int = 0
    filtered_out: int = 0
    new_findings: int = 0       # action=POST
    update_findings: int = 0    # action=PUT
    skip_findings: int = 0      # action=SKIP
    perspectives_generated: int = 0
    processing_time_ms: int = 0


class ExtractEvidenceRequest(BaseModel):
    """Request to extract evidence from a document."""
    topic_id: UUID = Field(..., description="Topic ID to associate findings with")
    workspace_id: str = Field(default="default")
    text_content: Optional[str] = Field(default=None, description="Text document content")
    # Note: PDF bytes handled separately via Form/File

    # Options
    min_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    run_web_context_search: bool = Field(default=True)
    run_perspective_analysis: bool = Field(default=True)
    check_existing_claims: bool = Field(default=True)
    max_findings: int = Field(default=20, ge=1, le=100)


class ExtractEvidenceResponse(BaseModel):
    """Response from evidence extraction."""
    extraction_id: UUID
    topic_id: UUID
    topic_name: Optional[str] = None
    status: str = "completed"  # processing, completed, failed
    findings: List[ExtractedFinding] = Field(default_factory=list)
    stats: ExtractionStats = Field(default_factory=ExtractionStats)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# DATABASE MODELS (for internal use)
# =============================================================================


class VerificationResultDB(BaseModel):
    """Database model for verification results."""
    id: UUID
    statement: str
    statement_hash: str
    verdict: VerificationVerdict
    confidence_score: float
    supporting_evidence: List[Dict[str, Any]]
    contradicting_evidence: List[Dict[str, Any]]
    related_claim_ids: List[UUID]
    related_claims_summary: Optional[str]
    web_sources: List[Dict[str, Any]]
    grounding_metadata: Optional[Dict[str, Any]]
    expires_at: Optional[datetime]
    hit_count: int
    workspace_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentExtractionDB(BaseModel):
    """Database model for document extractions."""
    id: UUID
    topic_id: Optional[UUID]
    document_type: str
    document_hash: str
    document_preview: Optional[str]
    status: str
    findings_count: int
    quality_filtered_count: int
    new_findings: int
    updated_findings: int
    skipped_findings: int
    processing_time_ms: Optional[int]
    error_message: Optional[str]
    workspace_id: str
    created_at: datetime

    class Config:
        from_attributes = True
