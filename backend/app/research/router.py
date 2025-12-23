"""FastAPI router for research operations."""

import json
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
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
from .services.orchestrator import ResearchOrchestrator
from .db import get_supabase_db, SupabaseResearchDB
from .templates import TEMPLATE_REGISTRY
from .services.analysis import MultiPerspectiveAnalyzer


router = APIRouter()


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
