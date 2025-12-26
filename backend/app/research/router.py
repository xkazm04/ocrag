"""FastAPI router for research operations."""

import json
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, File, UploadFile, Form

logger = logging.getLogger(__name__)
from fastapi.responses import StreamingResponse

from .schemas import (
    ResearchRequest,
    ResearchSession,
    ResearchSessionList,
    ResearchProgress,
    ContinueResearchRequest,
    TemplateInfo,
    CacheStats,
    Finding,
    Source,
    Perspective,
)
from .schemas.jobs import (
    SubmitResearchRequest,
    SubmitResearchResponse,
    JobStatusResponse,
    JobStatus,
    JobStats,
    DedupStats,
    ResearchJob,
)
from .schemas.verification import (
    VerifyStatementRequest,
    VerifyStatementResponse,
    ExtractEvidenceRequest,
    ExtractEvidenceResponse,
)
from .services.orchestrator import ResearchOrchestrator
from .db import get_supabase_db, SupabaseResearchDB
from .db.jobs import JobOperations
from .templates import TEMPLATE_REGISTRY
from .services.analysis import MultiPerspectiveAnalyzer
from .reports.router import router as reports_router
from .knowledge_router import router as knowledge_router


router = APIRouter()

# Include reports sub-router
router.include_router(reports_router, prefix="/reports", tags=["Report Generation"])

# Include knowledge explorer sub-router
router.include_router(knowledge_router, prefix="/knowledge", tags=["Knowledge Explorer"])


@router.post("/start")
async def start_research(
    request: ResearchRequest,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db(request.workspace_id if hasattr(request, 'workspace_id') else "default")),
):
    """
    Start a new research session with streaming progress.

    Returns SSE stream of progress updates.
    """
    orchestrator = ResearchOrchestrator(db, workspace_id=request.workspace_id)

    async def event_stream():
        try:
            async for progress in orchestrator.start_research(
                request,
                use_cache=request.parameters.use_cache,
            ):
                yield f"data: {progress.model_dump_json()}\n\n"
        except Exception as e:
            error_progress = ResearchProgress(
                status="failed",
                message=str(e),
                progress=0.0,
            )
            yield f"data: {error_progress.model_dump_json()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/sessions", response_model=ResearchSessionList)
async def list_sessions(
    workspace_id: str = "default",
    template_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
):
    """List research sessions with filtering."""
    db = get_supabase_db(workspace_id)
    sessions = await db.list_sessions(
        workspace_id=workspace_id,
        template_type=template_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return ResearchSessionList(
        sessions=sessions,
        total=len(sessions),  # TODO: Get actual count
        offset=offset,
        limit=limit,
    )


@router.get("/sessions/{session_id}", response_model=ResearchSession)
async def get_session(
    session_id: UUID,
    workspace_id: str = "default",
):
    """Get a specific research session."""
    db = get_supabase_db(workspace_id)
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/findings", response_model=List[Finding])
async def get_findings(
    session_id: UUID,
    finding_type: Optional[str] = None,
    min_confidence: Optional[float] = None,
    workspace_id: str = "default",
):
    """Get findings for a research session."""
    db = get_supabase_db(workspace_id)
    return await db.get_findings(
        session_id,
        finding_type=finding_type,
        min_confidence=min_confidence,
    )


@router.get("/sessions/{session_id}/sources", response_model=List[Source])
async def get_sources(
    session_id: UUID,
    min_credibility: Optional[float] = None,
    source_type: Optional[str] = None,
    workspace_id: str = "default",
):
    """Get sources for a research session."""
    db = get_supabase_db(workspace_id)
    return await db.get_sources(
        session_id,
        min_credibility=min_credibility,
        source_type=source_type,
    )


@router.get("/sessions/{session_id}/perspectives", response_model=List[Perspective])
async def get_perspectives(
    session_id: UUID,
    workspace_id: str = "default",
):
    """Get analysis perspectives for a research session."""
    db = get_supabase_db(workspace_id)
    return await db.get_perspectives(session_id)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    workspace_id: str = "default",
):
    """Delete a research session and all related data."""
    db = get_supabase_db(workspace_id)
    await db.delete_session(session_id)
    return {"status": "deleted", "session_id": str(session_id)}


@router.post("/sessions/{session_id}/continue")
async def continue_research(
    session_id: UUID,
    request: ContinueResearchRequest,
    workspace_id: str = "default",
):
    """
    Continue research with additional queries.

    Allows adding more search queries to an existing session.
    """
    db = get_supabase_db(workspace_id)
    orchestrator = ResearchOrchestrator(db, workspace_id=workspace_id)

    async def event_stream():
        try:
            async for progress in orchestrator.continue_research(
                session_id,
                request.additional_queries,
            ):
                yield f"data: {progress.model_dump_json()}\n\n"
        except Exception as e:
            error_progress = ResearchProgress(
                status="failed",
                message=str(e),
                progress=0.0,
            )
            yield f"data: {error_progress.model_dump_json()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )


@router.get("/templates", response_model=List[TemplateInfo])
async def list_templates():
    """List available research templates."""
    return [
        TemplateInfo(
            id=t.template_id,
            name=t.template_name,
            description=t.description,
            default_perspectives=t.default_perspectives,
            default_max_searches=t.default_max_searches,
            available=True,
        )
        for t in TEMPLATE_REGISTRY.values()
    ]


@router.get("/perspectives")
async def list_perspectives():
    """List available analysis perspectives."""
    analyzer = MultiPerspectiveAnalyzer()
    return analyzer.get_available_perspectives()


@router.get("/cache/stats", response_model=CacheStats)
async def cache_stats(
    workspace_id: str = "default",
):
    """Get research cache statistics."""
    db = get_supabase_db(workspace_id)
    stats = await db.get_cache_stats(workspace_id)
    return CacheStats(**stats)


@router.delete("/cache")
async def clear_cache(
    workspace_id: str = "default",
    template_type: Optional[str] = None,
):
    """Clear research cache."""
    db = get_supabase_db(workspace_id)
    await db.clear_cache(workspace_id, template_type)
    return {"status": "cleared", "workspace_id": workspace_id}


@router.get("/health")
async def health_check():
    """Health check for research module."""
    return {
        "status": "healthy",
        "module": "research",
        "templates_available": len(TEMPLATE_REGISTRY),
    }


# =============================================================================
# ASYNC JOB API ENDPOINTS
# =============================================================================


async def _check_gemini_health() -> bool:
    """Quick check if Gemini API is reachable."""
    try:
        # Import here to avoid circular imports
        from google import genai

        client = genai.Client()
        # Quick test with minimal tokens
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents="Say OK",
            config={"max_output_tokens": 5},
        )
        return bool(response.text)
    except Exception:
        logger.warning("Gemini health check failed")
        return False


@router.post("/submit", response_model=SubmitResearchResponse)
async def submit_research(
    request: SubmitResearchRequest,
    background_tasks: BackgroundTasks,
):
    """
    Submit an async research job.

    Returns job_id immediately. Use /status/{job_id} to poll progress.
    Fails fast with 503 if Gemini API is not reachable.

    Duplicate Detection:
    - Returns cached session if exact query exists and is recent
    - Returns existing job_id if same query is already running
    """
    # Get DB and job operations
    db = get_supabase_db(request.workspace_id)
    jobs = JobOperations(db.client, request.workspace_id)

    # Step 1: Check for cached session (exact query match)
    try:
        cached = await db.get_cached_session(request.query, request.template_type)
        if cached:
            return SubmitResearchResponse(
                job_id=None,
                session_id=cached.id,
                status=JobStatus.COMPLETED,
                message="Results retrieved from cache",
                cached=True,
            )
    except Exception:
        logger.info("Cache lookup failed, proceeding with new job")

    # Step 2: Check for running/pending job with same query
    try:
        existing_jobs = await jobs.find_duplicate_jobs(
            request.query,
            request.workspace_id,
            include_completed=False,
        )
        if existing_jobs:
            existing = existing_jobs[0]  # Most recent
            return SubmitResearchResponse(
                job_id=existing.id,
                status=existing.status,
                message="Query already being processed - returning existing job",
                cached=False,
            )
    except Exception:
        logger.info("Duplicate job detection failed, creating new job")

    # Step 3: Fail fast - Check Gemini availability
    if not await _check_gemini_health():
        raise HTTPException(
            status_code=503,
            detail="Gemini API not reachable. Please try again later."
        )

    # Step 4: Create new job record
    job = await jobs.create_job(
        query=request.query,
        workspace_id=request.workspace_id,
        template_type=request.template_type,
        parameters=request.parameters,
    )

    # Step 5: Start background processing
    try:
        from .services.job_processor import process_research_job
        background_tasks.add_task(process_research_job, job.id, request.workspace_id)
    except ImportError:
        # If job processor not yet implemented, just create the job
        pass

    return SubmitResearchResponse(
        job_id=job.id,
        status=JobStatus.PENDING,
        message="Research job submitted successfully",
        cached=False,
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    workspace_id: str = "default",
):
    """
    Get status of an async research job.

    Poll this endpoint to track progress. When completed, includes stats
    with findings_count, key_summary, token_usage, and deduplication results.
    """
    db = get_supabase_db(workspace_id)
    jobs = JobOperations(db.client, workspace_id)

    job = await jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Build response
    response = JobStatusResponse(
        job_id=job.id,
        status=job.status,
        current_stage=job.current_stage,
        progress_pct=job.progress_pct,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        session_id=job.session_id,
    )

    # Add stats if completed
    if job.status == JobStatus.COMPLETED and job.stats:
        stats_data = job.stats
        dedup_data = stats_data.get("dedup_stats")
        response.stats = JobStats(
            findings_count=stats_data.get("findings_count", 0),
            perspectives_count=stats_data.get("perspectives_count", 0),
            sources_count=stats_data.get("sources_count", 0),
            key_summary=stats_data.get("key_summary"),
            token_usage=stats_data.get("token_usage", {}),
            cost_usd=stats_data.get("cost_usd", 0.0),
            duration_seconds=stats_data.get("duration_seconds", 0.0),
            topic_id=stats_data.get("topic_id"),
            topic_name=stats_data.get("topic_name"),
            dedup_stats=DedupStats(**dedup_data) if dedup_data else None,
        )

    return response


@router.get("/jobs", response_model=List[ResearchJob])
async def list_jobs(
    workspace_id: str = "default",
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
):
    """List research jobs with optional status filter."""
    db = get_supabase_db(workspace_id)
    jobs = JobOperations(db.client, workspace_id)

    job_status = JobStatus(status) if status else None
    return await jobs.list_jobs(
        workspace_id=workspace_id,
        status=job_status,
        limit=limit,
        offset=offset,
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: UUID,
    workspace_id: str = "default",
):
    """Cancel a pending or running job."""
    db = get_supabase_db(workspace_id)
    jobs = JobOperations(db.client, workspace_id)

    job = await jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status.value}"
        )

    await jobs.cancel_job(job_id)
    return {"status": "cancelled", "job_id": str(job_id)}


# =============================================================================
# VERIFICATION & EVIDENCE EXTRACTION ENDPOINTS
# =============================================================================


@router.post("/verify", response_model=VerifyStatementResponse)
async def verify_statement(request: VerifyStatementRequest):
    """
    Fact-check a statement using web search and knowledge base.

    Uses Gemini grounded search to find evidence, queries existing claims
    in the knowledge base, and synthesizes a verdict.

    Returns:
        - verdict: supported/contradicted/inconclusive
        - confidence_score: 0.0-1.0
        - supporting_evidence: List of evidence items that support the statement
        - contradicting_evidence: List of evidence items that contradict the statement
        - related_claims: Similar claims from knowledge base

    Results are cached. Does NOT modify knowledge_claims table.
    """
    from .services.verification_service import VerificationService

    db = get_supabase_db(request.workspace_id)
    service = VerificationService(db)
    return await service.verify_statement(request)


@router.post("/extract-evidence", response_model=ExtractEvidenceResponse)
async def extract_evidence(
    topic_id: UUID = Form(..., description="Topic ID to associate findings with"),
    workspace_id: str = Form(default="default"),
    document: Optional[UploadFile] = File(default=None, description="PDF document to process"),
    text_content: Optional[str] = Form(default=None, description="Text content to process"),
    min_confidence_threshold: float = Form(default=0.6, ge=0.0, le=1.0),
    run_web_context_search: bool = Form(default=True),
    run_perspective_analysis: bool = Form(default=True),
    check_existing_claims: bool = Form(default=True),
    max_findings: int = Form(default=20, ge=1, le=100),
):
    """
    Extract evidence from a document (text or PDF).

    Processes the document through quality filtering and deduplication:
    1. Extracts structured findings using Gemini
    2. Applies quality filter (confidence, length, vagueness)
    3. Searches web for context on high-quality findings
    4. Compares against existing claims for deduplication
    5. Runs perspective analysis on valuable findings

    Returns structured findings with POST/PUT/SKIP decisions.
    The caller is responsible for executing the saves.

    Quality Levels:
    - HIGH: confidence >= 0.8 AND content >= 100 chars
    - MEDIUM: confidence >= 0.6
    - LOW: passes minimum thresholds
    - FILTERED: did not pass quality filter (not returned)
    """
    from .services.evidence_extraction_service import EvidenceExtractionService

    db = get_supabase_db(workspace_id)
    service = EvidenceExtractionService(db)

    # Process PDF if provided
    pdf_bytes = None
    if document and document.content_type == "application/pdf":
        pdf_bytes = await document.read()
    elif document:
        # Try to read as text
        text_content = (await document.read()).decode("utf-8")

    # Build options
    options = ExtractEvidenceRequest(
        topic_id=topic_id,
        workspace_id=workspace_id,
        text_content=text_content,
        min_confidence_threshold=min_confidence_threshold,
        run_web_context_search=run_web_context_search,
        run_perspective_analysis=run_perspective_analysis,
        check_existing_claims=check_existing_claims,
        max_findings=max_findings,
    )

    return await service.extract_evidence(
        topic_id=topic_id,
        document_text=text_content,
        pdf_bytes=pdf_bytes,
        options=options,
    )
