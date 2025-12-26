"""Report generation schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ReportFormat(str, Enum):
    """Output formats for generated reports."""
    JSON = "json"           # Markdown + metadata as JSON
    MARKDOWN = "markdown"   # Raw markdown text
    HTML = "html"          # LLM-styled HTML
    PDF = "pdf"            # PDF binary from HTML


class ReportVariant(str, Enum):
    """Report variants available for generation."""
    # Universal variants (all templates)
    EXECUTIVE_SUMMARY = "executive_summary"
    FULL_REPORT = "full_report"
    FINDINGS_ONLY = "findings_only"
    SOURCE_BIBLIOGRAPHY = "source_bibliography"

    # Investigative template variants
    TIMELINE_REPORT = "timeline_report"
    ACTOR_DOSSIER = "actor_dossier"
    EVIDENCE_BRIEF = "evidence_brief"

    # Competitive intelligence variants
    COMPETITIVE_MATRIX = "competitive_matrix"
    SWOT_ANALYSIS = "swot_analysis"
    BATTLECARD = "battlecard"

    # Financial analysis variants
    INVESTMENT_THESIS = "investment_thesis"
    EARNINGS_SUMMARY = "earnings_summary"
    RISK_ASSESSMENT = "risk_assessment"

    # Legal research variants
    LEGAL_BRIEF = "legal_brief"
    CASE_DIGEST = "case_digest"
    COMPLIANCE_CHECKLIST = "compliance_checklist"


# Map variants to compatible templates
VARIANT_TEMPLATE_COMPATIBILITY = {
    # Universal - works with all
    ReportVariant.EXECUTIVE_SUMMARY: None,  # None means all templates
    ReportVariant.FULL_REPORT: None,
    ReportVariant.FINDINGS_ONLY: None,
    ReportVariant.SOURCE_BIBLIOGRAPHY: None,

    # Investigative specific
    ReportVariant.TIMELINE_REPORT: ["investigative"],
    ReportVariant.ACTOR_DOSSIER: ["investigative"],
    ReportVariant.EVIDENCE_BRIEF: ["investigative"],

    # Competitive specific
    ReportVariant.COMPETITIVE_MATRIX: ["competitive"],
    ReportVariant.SWOT_ANALYSIS: ["competitive"],
    ReportVariant.BATTLECARD: ["competitive"],

    # Financial specific
    ReportVariant.INVESTMENT_THESIS: ["financial"],
    ReportVariant.EARNINGS_SUMMARY: ["financial"],
    ReportVariant.RISK_ASSESSMENT: ["financial"],

    # Legal specific
    ReportVariant.LEGAL_BRIEF: ["legal"],
    ReportVariant.CASE_DIGEST: ["legal"],
    ReportVariant.COMPLIANCE_CHECKLIST: ["legal"],
}


class GenerateReportRequest(BaseModel):
    """Request to generate a report from a research session."""
    session_id: UUID = Field(..., description="Research session ID to generate report from")
    variant: ReportVariant = Field(
        default=ReportVariant.FULL_REPORT,
        description="Type of report to generate"
    )
    format: ReportFormat = Field(
        default=ReportFormat.JSON,
        description="Output format for the report"
    )
    title: Optional[str] = Field(
        default=None,
        description="Custom title for the report (defaults to session query)"
    )
    include_sections: Optional[List[str]] = Field(
        default=None,
        description="Specific sections to include (if None, include all)"
    )
    style_overrides: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Custom style parameters to override template defaults"
    )
    workspace_id: str = Field(default="default")


class ReportSection(BaseModel):
    """A section within the report."""
    id: str
    title: str
    content: str
    order: int
    subsections: Optional[List["ReportSection"]] = None


class ReportMetadata(BaseModel):
    """Metadata about the generated report."""
    template_type: str
    findings_count: int = 0
    sources_count: int = 0
    perspectives_count: int = 0
    claims_count: int = 0
    high_confidence_count: int = 0
    research_status: str = "unknown"
    word_count: Optional[int] = None
    sections: Optional[List[str]] = None
    generation_time_ms: Optional[int] = None


class ReportResponse(BaseModel):
    """Response containing the generated report."""
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: UUID
    variant: str
    format: str
    title: str
    generated_at: datetime = Field(default_factory=datetime.now)
    markdown_content: str
    html_content: Optional[str] = None
    metadata: ReportMetadata


class ReportData(BaseModel):
    """Aggregated data for report generation."""
    session_id: UUID
    session_title: str
    session_query: str
    template_type: str
    status: str
    parameters: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime]

    # Research data
    findings: List[Dict[str, Any]]
    perspectives: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    claims: List[Dict[str, Any]] = []

    # Computed
    @property
    def high_confidence_findings(self) -> List[Dict[str, Any]]:
        """Findings with confidence >= 0.7."""
        return [f for f in self.findings if f.get("confidence_score", 0) >= 0.7]

    @property
    def findings_by_type(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group findings by type."""
        grouped = {}
        for f in self.findings:
            ftype = f.get("finding_type", "unknown")
            if ftype not in grouped:
                grouped[ftype] = []
            grouped[ftype].append(f)
        return grouped

    @property
    def sources_by_credibility(self) -> List[Dict[str, Any]]:
        """Sources sorted by credibility score (descending)."""
        return sorted(
            self.sources,
            key=lambda s: s.get("credibility_score", 0),
            reverse=True
        )


# Rebuild for forward references
ReportSection.model_rebuild()
