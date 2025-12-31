"""FastAPI router for deep research operations.

Includes endpoints for:
- Recursive Chain-of-Investigation
- Financial Trail Blazer
- Temporal Causality Analysis
"""

import logging
from typing import Optional, List, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from .db import get_supabase_db, SupabaseResearchDB
from .schemas.recursive import (
    StartRecursiveResearchRequest,
    RecursiveResearchSubmitResponse,
    ResearchTreeStatus,
    ResearchTreeResult,
    ResearchNodeStatus,
    TreeNodesResponse,
)
from .schemas.financial import (
    TraceMoneyRequest,
    TraceMoneyResponse,
    CorporateStructureRequest,
    CorporateStructureResponse,
    PropertySearchRequest,
    PropertySearchResponse,
    FinancialEntity,
    FinancialTransaction,
    BeneficialOwner,
)
from .schemas.causality import (
    ExtractCausalityRequest,
    CausalityExtractionResponse,
    FindCausesRequest,
    FindCausesResponse,
    FindConsequencesRequest,
    FindConsequencesResponse,
    BuildCausalGraphRequest,
    CausalGraph,
    CausalLink,
    CausalPattern,
    CausalChainsResponse,
    DetectPatternsRequest,
    DetectPatternsResponse,
)
from .services.recursive_research_service import RecursiveResearchService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Recursive Research Endpoints
# ============================================

@router.post("/recursive/start", tags=["Recursive Research"])
async def start_recursive_research(
    request: StartRecursiveResearchRequest,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> StreamingResponse:
    """
    Start recursive research session with automatic follow-up generation.
    Returns SSE stream with progress updates.

    The recursive research will:
    1. Execute the initial query
    2. Generate follow-up questions (predecessors, consequences, etc.)
    3. Recursively research follow-ups until saturation or limits
    4. Return a tree of findings with reasoning chains
    """
    service = RecursiveResearchService(db)

    async def event_generator():
        try:
            async for status in service.start_recursive_research(request):
                yield f"data: {status.model_dump_json()}\n\n"
        except Exception as e:
            logger.error(f"Recursive research stream error: {e}")
            error_status = ResearchTreeStatus(
                tree_id=UUID("00000000-0000-0000-0000-000000000000"),
                root_query=request.query,
                status="failed",
                total_nodes=0,
                completed_nodes=0,
                pending_nodes=0,
                max_depth_reached=0,
                progress_pct=0.0,
            )
            yield f"data: {error_status.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/recursive/submit", response_model=RecursiveResearchSubmitResponse, tags=["Recursive Research"])
async def submit_recursive_research(
    request: StartRecursiveResearchRequest,
    background_tasks: BackgroundTasks,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> RecursiveResearchSubmitResponse:
    """
    Submit recursive research as background job.
    Returns tree_id for polling status.
    """
    service = RecursiveResearchService(db)

    # Create tree and get ID
    from .schemas.recursive import RecursiveResearchConfig
    config = request.config or RecursiveResearchConfig()
    tree_id = await service._create_tree(request, config)

    # Add background task
    async def run_research():
        async for _ in service.start_recursive_research(request):
            pass  # Just consume the generator

    background_tasks.add_task(run_research)

    return RecursiveResearchSubmitResponse(
        tree_id=tree_id,
        status="pending",
        message="Recursive research submitted. Poll /recursive/{tree_id}/status for updates.",
    )


@router.get("/recursive/{tree_id}/status", response_model=ResearchTreeStatus, tags=["Recursive Research"])
async def get_recursive_status(
    tree_id: UUID,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> ResearchTreeStatus:
    """Get current status of recursive research tree."""
    service = RecursiveResearchService(db)
    tree = await service._get_tree(tree_id)

    if not tree:
        raise HTTPException(status_code=404, detail="Research tree not found")

    completed = await service._get_completed_nodes(tree_id)
    total = await service._get_total_nodes(tree_id)
    max_depth = await service._get_max_depth(tree_id)

    return ResearchTreeStatus(
        tree_id=tree_id,
        root_query=tree["root_query"],
        status=tree["status"],
        total_nodes=total,
        completed_nodes=completed,
        pending_nodes=total - completed,
        max_depth_reached=max_depth,
        progress_pct=(completed / total * 100) if total > 0 else 0,
        total_tokens_used=tree.get("total_tokens_used", 0),
        estimated_cost_usd=tree.get("estimated_cost_usd", 0),
    )


@router.get("/recursive/{tree_id}/result", response_model=ResearchTreeResult, tags=["Recursive Research"])
async def get_recursive_result(
    tree_id: UUID,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> ResearchTreeResult:
    """Get final result of completed recursive research."""
    service = RecursiveResearchService(db)
    result = await service.get_tree_result(tree_id)

    if not result:
        raise HTTPException(status_code=404, detail="Research tree not found")

    return result


@router.get("/recursive/{tree_id}/nodes", response_model=TreeNodesResponse, tags=["Recursive Research"])
async def get_tree_nodes(
    tree_id: UUID,
    depth: Optional[int] = None,
    status: Optional[str] = None,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> TreeNodesResponse:
    """Get nodes in tree, optionally filtered by depth or status."""
    service = RecursiveResearchService(db)

    # Build query
    query = db.client.table("research_nodes").select("*").eq("tree_id", str(tree_id))

    if depth is not None:
        query = query.eq("depth", depth)
    if status:
        query = query.eq("status", status)

    result = query.order("depth").execute()
    nodes = result.data or []

    return TreeNodesResponse(
        tree_id=tree_id,
        total_nodes=len(nodes),
        nodes=[
            ResearchNodeStatus(
                id=UUID(n["id"]),
                query=n["query"],
                query_type=n["query_type"],
                depth=n["depth"],
                status=n["status"],
                saturation_score=n.get("saturation_score", 0),
                findings_count=n.get("findings_count", 0),
                new_entities_count=n.get("new_entities_count", 0),
                children_count=0,  # Would need additional query
                skip_reason=n.get("skip_reason"),
                execution_time_ms=n.get("execution_time_ms"),
            )
            for n in nodes
        ],
        filter_depth=depth,
        filter_status=status,
    )


@router.get("/recursive/{tree_id}/chain/{node_id}", tags=["Recursive Research"])
async def get_reasoning_chain(
    tree_id: UUID,
    node_id: UUID,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> List[str]:
    """Get question chain from root to specific node."""
    service = RecursiveResearchService(db)
    return await service.get_reasoning_chain(tree_id, node_id)


# ============================================
# Financial Research Endpoints
# ============================================

@router.post("/financial/trace-money", response_model=TraceMoneyResponse, tags=["Financial Research"])
async def trace_money(
    request: TraceMoneyRequest,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> TraceMoneyResponse:
    """
    Trace financial transactions forward/backward from an entity.
    Identifies transaction chains and shell company patterns.

    Uses LLM-guided source discovery to find appropriate financial records
    based on jurisdiction (SEC for US, Companies House for UK, etc.).
    """
    # Import here to avoid circular imports
    from .services.financial_research_service import FinancialResearchService

    service = FinancialResearchService(db)
    return await service.trace_money(request)


@router.post("/financial/corporate-structure", response_model=CorporateStructureResponse, tags=["Financial Research"])
async def get_corporate_structure(
    request: CorporateStructureRequest,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> CorporateStructureResponse:
    """
    Build corporate ownership hierarchy for an entity.
    Identifies subsidiaries, officers, and beneficial owners.
    """
    from .services.financial_research_service import FinancialResearchService

    service = FinancialResearchService(db)
    return await service.get_corporate_structure(request)


@router.post("/financial/property-search", response_model=PropertySearchResponse, tags=["Financial Research"])
async def search_properties(
    request: PropertySearchRequest,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> PropertySearchResponse:
    """Find real estate holdings and transfers for an entity."""
    from .services.financial_research_service import FinancialResearchService

    service = FinancialResearchService(db)
    return await service.find_property_transfers(request)


@router.get("/financial/entity/{entity_id}/transactions", tags=["Financial Research"])
async def get_entity_transactions(
    entity_id: UUID,
    direction: Literal["inbound", "outbound", "all"] = "all",
    limit: int = Query(default=100, le=500),
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> List[FinancialTransaction]:
    """Get transactions for a financial entity."""
    query = db.client.table("financial_transactions").select("*")

    if direction == "inbound":
        query = query.eq("target_entity_id", str(entity_id))
    elif direction == "outbound":
        query = query.eq("source_entity_id", str(entity_id))
    else:
        query = query.or_(f"source_entity_id.eq.{entity_id},target_entity_id.eq.{entity_id}")

    result = query.limit(limit).order("transaction_date", desc=True).execute()

    return [FinancialTransaction(**tx) for tx in result.data or []]


@router.get("/financial/entity/{entity_id}/beneficial-owners", tags=["Financial Research"])
async def get_beneficial_owners(
    entity_id: UUID,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> List[BeneficialOwner]:
    """Get beneficial owners of a company."""
    result = db.client.table("beneficial_owners").select("*").eq(
        "company_entity_id", str(entity_id)
    ).execute()

    return [BeneficialOwner(**bo) for bo in result.data or []]


# ============================================
# Causality Endpoints
# ============================================

@router.post("/causality/extract", response_model=CausalityExtractionResponse, tags=["Causality Analysis"])
async def extract_causality(
    request: ExtractCausalityRequest,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> CausalityExtractionResponse:
    """
    Determine causal relationship between two events.
    Uses LLM reasoning with counterfactual analysis.
    """
    from .services.causality_service import CausalityService

    service = CausalityService(db)
    link = await service.extract_causality(request)

    return CausalityExtractionResponse(
        event_a=request.event_a,
        event_b=request.event_b,
        has_causal_relationship=link.confidence > 0.3,
        causal_link=link if link.confidence > 0.3 else None,
    )


@router.post("/causality/find-causes", response_model=FindCausesResponse, tags=["Causality Analysis"])
async def find_causes(
    request: FindCausesRequest,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> FindCausesResponse:
    """
    Find all causes (direct and indirect) of an event.
    Traces back through causal chains to root causes.
    """
    from .services.causality_service import CausalityService

    service = CausalityService(db)
    return await service.find_causes(request)


@router.post("/causality/find-consequences", response_model=FindConsequencesResponse, tags=["Causality Analysis"])
async def find_consequences(
    request: FindConsequencesRequest,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> FindConsequencesResponse:
    """
    Find all consequences (direct and indirect) of an event.
    Traces forward through causal chains to final outcomes.
    """
    from .services.causality_service import CausalityService

    service = CausalityService(db)
    return await service.find_consequences(request)


@router.post("/causality/build-graph", response_model=CausalGraph, tags=["Causality Analysis"])
async def build_causal_graph(
    request: BuildCausalGraphRequest,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> CausalGraph:
    """
    Build complete causal graph for a topic.
    Identifies patterns and key causal relationships.
    """
    from .services.causality_service import CausalityService

    service = CausalityService(db)
    return await service.build_causal_graph(request)


@router.post("/causality/detect-patterns", response_model=DetectPatternsResponse, tags=["Causality Analysis"])
async def detect_patterns(
    request: DetectPatternsRequest,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> DetectPatternsResponse:
    """Detect causal patterns (cover-ups, enabling networks, etc.)."""
    from .services.causality_service import CausalityService

    service = CausalityService(db)
    return await service.detect_patterns(request)


@router.get("/causality/patterns/{topic_id}", tags=["Causality Analysis"])
async def get_causal_patterns(
    topic_id: UUID,
    pattern_type: Optional[str] = None,
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> List[CausalPattern]:
    """Get detected causal patterns for a topic."""
    query = db.client.table("causal_patterns").select("*")

    # Filter by topic (checking if topic_id is in involved_entities or claim_ids)
    # This is a simplified version - would need proper topic linking

    if pattern_type:
        query = query.eq("pattern_type", pattern_type)

    result = query.execute()
    return [CausalPattern(**p) for p in result.data or []]


@router.get("/causality/chain/{claim_id}", response_model=CausalChainsResponse, tags=["Causality Analysis"])
async def get_causal_chain(
    claim_id: UUID,
    direction: Literal["causes", "consequences", "both"] = "both",
    max_depth: int = Query(default=5, ge=1, le=10),
    db: SupabaseResearchDB = Depends(lambda: get_supabase_db("default")),
) -> CausalChainsResponse:
    """Get pre-computed causal chains for a claim."""
    as_cause = []
    as_consequence = []
    in_chain = []

    if direction in ["causes", "both"]:
        result = db.client.table("causal_chains").select("*").eq(
            "end_claim_id", str(claim_id)
        ).execute()
        as_consequence = result.data or []

    if direction in ["consequences", "both"]:
        result = db.client.table("causal_chains").select("*").eq(
            "start_claim_id", str(claim_id)
        ).execute()
        as_cause = result.data or []

    # Also find chains where this claim is in the middle
    result = db.client.table("causal_chains").select("*").contains(
        "claim_ids", [str(claim_id)]
    ).execute()
    in_chain = [c for c in (result.data or []) if c not in as_cause and c not in as_consequence]

    return CausalChainsResponse(
        claim_id=claim_id,
        as_cause=[],  # Would need to convert to CausalChainSummary
        as_consequence=[],
        in_chain=[],
        total_chains=len(as_cause) + len(as_consequence) + len(in_chain),
    )
