"""Report generation service."""

import logging
from typing import Optional, Dict, Any
from uuid import UUID

from .schemas import (
    GenerateReportRequest,
    ReportResponse,
    ReportMetadata,
    ReportFormat,
    ReportVariant,
    ReportData,
)
from .data.aggregator import ReportDataAggregator
from .composers import get_composer
from .generators import create_html_generator


logger = logging.getLogger(__name__)


class ReportGenerationService:
    """
    Service for generating research reports in various formats.

    Orchestrates the report generation pipeline:
    1. Aggregate research data from database
    2. Compose markdown using variant-specific composer
    3. Optionally convert to HTML via LLM
    4. Optionally convert to PDF via WeasyPrint
    """

    def __init__(self, db):
        self.db = db
        self.aggregator = ReportDataAggregator(db)

    async def generate_report(
        self,
        request: GenerateReportRequest
    ) -> ReportResponse:
        """
        Generate a report based on the request.

        Args:
            request: Report generation request with variant and format

        Returns:
            ReportResponse with generated content
        """
        logger.info(f"Generating {request.variant} report for session {request.session_id}")

        # Step 1: Aggregate all research data
        data = await self.aggregator.aggregate(request.session_id)

        # Step 2: Get appropriate composer and generate markdown
        composer = get_composer(request.variant.value)
        markdown_content = composer.compose(
            data=data,
            variant=request.variant,
            title=request.title,
            include_sections=request.include_sections,
        )

        # Determine report title
        report_title = request.title or self._generate_title(data, request.variant)

        # Step 3: Build metadata
        metadata = ReportMetadata(
            template_type=data.template_type,
            findings_count=len(data.findings),
            sources_count=len(data.sources),
            perspectives_count=len(data.perspectives),
            high_confidence_count=len(data.high_confidence_findings),
            research_status=data.status,
        )

        # Step 4: Generate HTML if needed (for HTML or PDF format)
        # PDF format returns HTML for frontend-based PDF generation
        html_content = None

        if request.format in (ReportFormat.HTML, ReportFormat.PDF):
            html_content = await self._generate_html(
                markdown_content=markdown_content,
                template_type=data.template_type,
                title=report_title,
                style_overrides=request.style_overrides,
            )

        # Build response
        response = ReportResponse(
            session_id=request.session_id,
            variant=request.variant.value,
            format=request.format.value,
            title=report_title,
            markdown_content=markdown_content,
            html_content=html_content,
            metadata=metadata,
        )

        logger.info(f"Report generated: {len(markdown_content)} chars markdown")
        return response

    async def _generate_html(
        self,
        markdown_content: str,
        template_type: str,
        title: str,
        style_overrides: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate styled HTML from markdown using LLM."""
        try:
            generator = create_html_generator()
            html = await generator.generate(
                markdown_content=markdown_content,
                template_type=template_type,
                title=title,
                style_overrides=style_overrides,
            )
            logger.info(f"Generated HTML: {len(html)} chars")
            return html
        except Exception as e:
            logger.warning(f"LLM HTML generation failed, using fallback: {e}")
            # Use fallback
            generator = create_html_generator()
            return generator.generate_fallback_html(
                markdown_content=markdown_content,
                title=title,
                template_type=template_type,
            )

    def _generate_title(self, data: ReportData, variant: ReportVariant) -> str:
        """Generate a default title based on data and variant."""
        variant_names = {
            ReportVariant.EXECUTIVE_SUMMARY: "Executive Summary",
            ReportVariant.FULL_REPORT: "Research Report",
            ReportVariant.FINDINGS_ONLY: "Research Findings",
            ReportVariant.SOURCE_BIBLIOGRAPHY: "Source Bibliography",
            ReportVariant.TIMELINE_REPORT: "Timeline Report",
            ReportVariant.ACTOR_DOSSIER: "Actor Dossier",
            ReportVariant.EVIDENCE_BRIEF: "Evidence Brief",
            ReportVariant.COMPETITIVE_MATRIX: "Competitive Matrix",
            ReportVariant.SWOT_ANALYSIS: "SWOT Analysis",
            ReportVariant.BATTLECARD: "Sales Battlecard",
            ReportVariant.INVESTMENT_THESIS: "Investment Thesis",
            ReportVariant.EARNINGS_SUMMARY: "Earnings Summary",
            ReportVariant.RISK_ASSESSMENT: "Risk Assessment",
            ReportVariant.LEGAL_BRIEF: "Legal Brief",
            ReportVariant.CASE_DIGEST: "Case Digest",
            ReportVariant.COMPLIANCE_CHECKLIST: "Compliance Checklist",
        }

        variant_name = variant_names.get(variant, "Report")
        query_short = data.session_query[:50] if data.session_query else "Research"

        return f"{variant_name}: {query_short}"

    def get_available_variants(self, template_type: str) -> list:
        """Get available report variants for a template type."""
        # Universal variants
        variants = [
            {"id": "executive_summary", "name": "Executive Summary", "description": "1-2 page high-level overview"},
            {"id": "full_report", "name": "Full Report", "description": "Comprehensive research document"},
            {"id": "findings_only", "name": "Findings Only", "description": "Findings grouped by type/confidence"},
            {"id": "source_bibliography", "name": "Source Bibliography", "description": "Annotated source list"},
        ]

        # Template-specific variants
        template_variants = {
            "investigative": [
                {"id": "timeline_report", "name": "Timeline Report", "description": "Chronological event narrative"},
                {"id": "actor_dossier", "name": "Actor Dossier", "description": "Entity profiles and relationships"},
                {"id": "evidence_brief", "name": "Evidence Brief", "description": "Evidence chain summary"},
            ],
            "competitive": [
                {"id": "competitive_matrix", "name": "Competitive Matrix", "description": "Side-by-side comparison"},
                {"id": "swot_analysis", "name": "SWOT Analysis", "description": "Structured SWOT format"},
                {"id": "battlecard", "name": "Battlecard", "description": "Sales enablement format"},
            ],
            "financial": [
                {"id": "investment_thesis", "name": "Investment Thesis", "description": "Bull/bear case with valuation"},
                {"id": "earnings_summary", "name": "Earnings Summary", "description": "Metrics and guidance"},
                {"id": "risk_assessment", "name": "Risk Assessment", "description": "Risk factors and severity"},
            ],
            "legal": [
                {"id": "legal_brief", "name": "Legal Brief", "description": "IRAC format memorandum"},
                {"id": "case_digest", "name": "Case Digest", "description": "Holdings and precedents"},
                {"id": "compliance_checklist", "name": "Compliance Checklist", "description": "Requirements matrix"},
            ],
        }

        # Add template-specific variants
        normalized = template_type.lower().replace("-", "_").replace(" ", "_")
        for key, specific_variants in template_variants.items():
            if key in normalized:
                variants.extend(specific_variants)

        return variants
