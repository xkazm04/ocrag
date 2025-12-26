"""FastAPI router for report generation."""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
import io

from .schemas import (
    GenerateReportRequest,
    ReportResponse,
    ReportFormat,
    ReportVariant,
)
from .service import ReportGenerationService
from ..db import get_supabase_db, SupabaseResearchDB


router = APIRouter()


def get_report_service(workspace_id: str = "default") -> ReportGenerationService:
    """Get report generation service with database."""
    db = get_supabase_db(workspace_id)
    return ReportGenerationService(db)


@router.post("/generate")
async def generate_report(
    request: GenerateReportRequest,
    workspace_id: str = Query(default="default"),
):
    """
    Generate a report from a research session.

    Supports multiple formats:
    - json: Returns ReportResponse with markdown and metadata
    - markdown: Returns raw markdown text
    - html: Returns LLM-styled HTML document
    - pdf: Returns PDF binary (requires weasyprint)

    Supports multiple variants per template type:
    - Universal: executive_summary, full_report, findings_only, source_bibliography
    - Investigative: timeline_report, actor_dossier, evidence_brief
    - Competitive: competitive_matrix, swot_analysis, battlecard
    - Financial: investment_thesis, earnings_summary, risk_assessment
    - Legal: legal_brief, case_digest, compliance_checklist
    """
    service = get_report_service(workspace_id)

    try:
        response = await service.generate_report(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")

    # Return based on requested format
    if request.format == ReportFormat.JSON:
        return response

    elif request.format == ReportFormat.MARKDOWN:
        return Response(
            content=response.markdown_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{_safe_filename(response.title)}.md"'
            }
        )

    elif request.format == ReportFormat.HTML:
        if not response.html_content:
            raise HTTPException(status_code=500, detail="HTML generation failed")
        return Response(
            content=response.html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f'inline; filename="{_safe_filename(response.title)}.html"'
            }
        )

    elif request.format == ReportFormat.PDF:
        # Return HTML for frontend PDF generation (using html2pdf.js or similar)
        if not response.html_content:
            raise HTTPException(status_code=500, detail="HTML generation failed for PDF export")

        return Response(
            content=response.html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f'inline; filename="{_safe_filename(response.title)}.html"',
                "X-PDF-Method": "frontend",
                "X-Suggested-Filename": f"{_safe_filename(response.title)}.pdf",
            }
        )

    raise HTTPException(status_code=400, detail=f"Unknown format: {request.format}")


@router.get("/variants")
async def list_variants(
    template_type: Optional[str] = Query(default=None, description="Filter by template type"),
    workspace_id: str = Query(default="default"),
):
    """
    List available report variants.

    Optionally filter by template type to see template-specific variants.
    """
    service = get_report_service(workspace_id)

    if template_type:
        return service.get_available_variants(template_type)

    # Return all variants grouped by category
    return {
        "universal": [
            {"id": "executive_summary", "name": "Executive Summary", "description": "1-2 page high-level overview"},
            {"id": "full_report", "name": "Full Report", "description": "Comprehensive research document"},
            {"id": "findings_only", "name": "Findings Only", "description": "Findings grouped by type/confidence"},
            {"id": "source_bibliography", "name": "Source Bibliography", "description": "Annotated source list"},
        ],
        "investigative": [
            {"id": "timeline_report", "name": "Timeline Report", "description": "Chronological event narrative"},
            {"id": "actor_dossier", "name": "Actor Dossier", "description": "Entity profiles and relationships"},
            {"id": "evidence_brief", "name": "Evidence Brief", "description": "Evidence chain summary"},
        ],
        "competitive": [
            {"id": "competitive_matrix", "name": "Competitive Matrix", "description": "Side-by-side competitor comparison"},
            {"id": "swot_analysis", "name": "SWOT Analysis", "description": "Structured SWOT format"},
            {"id": "battlecard", "name": "Battlecard", "description": "Sales enablement format"},
        ],
        "financial": [
            {"id": "investment_thesis", "name": "Investment Thesis", "description": "Bull/bear case with valuation"},
            {"id": "earnings_summary", "name": "Earnings Summary", "description": "Metrics, guidance, analyst views"},
            {"id": "risk_assessment", "name": "Risk Assessment", "description": "Risk factors and severity"},
        ],
        "legal": [
            {"id": "legal_brief", "name": "Legal Brief", "description": "IRAC format memorandum"},
            {"id": "case_digest", "name": "Case Digest", "description": "Holdings and precedents"},
            {"id": "compliance_checklist", "name": "Compliance Checklist", "description": "Requirements × Status matrix"},
        ],
    }


@router.get("/formats")
async def list_formats():
    """List available output formats and their requirements."""
    return {
        "formats": [
            {
                "id": "json",
                "name": "JSON",
                "description": "Structured response with markdown and metadata",
                "media_type": "application/json",
                "available": True,
            },
            {
                "id": "markdown",
                "name": "Markdown",
                "description": "Raw markdown text file",
                "media_type": "text/markdown",
                "available": True,
            },
            {
                "id": "html",
                "name": "HTML",
                "description": "Styled HTML document (LLM-generated)",
                "media_type": "text/html",
                "available": True,
                "note": "Requires OpenRouter API key",
            },
            {
                "id": "pdf",
                "name": "PDF",
                "description": "Returns HTML for frontend PDF generation (use html2pdf.js)",
                "media_type": "text/html",
                "available": True,
                "note": "Returns HTML with X-PDF-Method: frontend header. Use html2pdf.js or browser print for PDF export.",
            },
        ]
    }


@router.get("/preview/{session_id}")
async def preview_report(
    session_id: UUID,
    variant: ReportVariant = Query(default=ReportVariant.EXECUTIVE_SUMMARY),
    workspace_id: str = Query(default="default"),
):
    """
    Quick preview of a report in markdown format.

    Useful for checking content before generating full HTML/PDF.
    """
    request = GenerateReportRequest(
        session_id=session_id,
        variant=variant,
        format=ReportFormat.JSON,
    )

    service = get_report_service(workspace_id)

    try:
        response = await service.generate_report(request)
        return {
            "title": response.title,
            "variant": response.variant,
            "markdown_preview": response.markdown_content[:2000] + "..." if len(response.markdown_content) > 2000 else response.markdown_content,
            "metadata": response.metadata,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {e}")


def _safe_filename(title: str) -> str:
    """Convert title to safe filename."""
    import re
    # Remove or replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = safe.replace(' ', '_')
    # Limit length
    return safe[:100]
