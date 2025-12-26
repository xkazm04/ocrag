"""FastAPI router for Knowledge Explorer features.

Provides 5 key investigation features:
1. Network Graph - Entity relationship visualization
2. Timeline - Chronological event reconstruction
3. Evidence Corroboration - Multi-source verification
4. Pattern Mining - Anomaly and pattern detection
5. Investigative Q&A - RAG-powered question answering
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .db import get_supabase_db
from .db.client import get_supabase_client
from .db.claims import ClaimOperations
from .db.entities import EntityOperations
from .db.relationships import ClaimEntityOperations, ClaimSourceOperations, RelationshipOperations
from .schemas.knowledge_explorer import (
    # Graph
    NetworkGraphRequest,
    NetworkGraphResponse,
    GraphData,
    GraphNode,
    GraphEdge,
    # Timeline
    TimelineRequest,
    TimelineResponse,
    TimelineEvent,
    # Corroboration
    CorroborationRequest,
    CorroborationResponse,
    CorroborationResult,
    SourceEvidence,
    # Pattern Mining
    PatternMiningRequest,
    PatternMiningResponse,
    DetectedPattern,
    PatternType,
    # Q&A
    InvestigativeQuestion,
    InvestigativeAnswer,
    Citation,
    # Entity Profile
    EntityProfileRequest,
    EntityProfile,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# NETWORK GRAPH API
# =============================================================================


@router.post("/graph", response_model=NetworkGraphResponse)
async def get_network_graph(request: NetworkGraphRequest):
    """
    Get entity relationship graph data.

    Returns nodes (entities) and edges (relationships) for visualization.
    Supports filtering by entity types, specific entities, and depth.
    """
    client = get_supabase_client()
    entities_db = EntityOperations(client)
    claim_entities_db = ClaimEntityOperations(client)

    nodes: Dict[str, GraphNode] = {}
    edges: List[GraphEdge] = []
    edge_set: set = set()

    # Query entities
    query = client.table("knowledge_entities").select(
        "id, canonical_name, entity_type, mention_count, description"
    )

    if request.entity_types:
        query = query.in_("entity_type", request.entity_types)

    if request.entity_ids:
        query = query.in_("id", [str(eid) for eid in request.entity_ids])

    query = query.order("mention_count", desc=True).limit(request.max_nodes)
    result = query.execute()

    # Create entity nodes
    for row in result.data:
        entity_id = row["id"]
        nodes[entity_id] = GraphNode(
            id=entity_id,
            label=row["canonical_name"],
            type=row["entity_type"],
            size=min(30, 5 + (row.get("mention_count", 0) // 5)),
            metadata={
                "mention_count": row.get("mention_count", 0),
                "description": row.get("description", ""),
            }
        )

    # Find connections between entities via shared claims
    entity_ids = list(nodes.keys())
    if entity_ids:
        # Get claims that connect entities
        claim_entities_result = client.table("claim_entities").select(
            "claim_id, entity_id, role"
        ).in_("entity_id", entity_ids).execute()

        # Group entities by claim
        claim_to_entities: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        for row in claim_entities_result.data:
            claim_to_entities[row["claim_id"]].append({
                "entity_id": row["entity_id"],
                "role": row.get("role", "mentioned")
            })

        # Create edges between entities that share claims
        for claim_id, entities in claim_to_entities.items():
            if len(entities) >= 2:
                for i, e1 in enumerate(entities):
                    for e2 in entities[i + 1:]:
                        edge_key = tuple(sorted([e1["entity_id"], e2["entity_id"]]))
                        if edge_key not in edge_set:
                            edge_set.add(edge_key)
                            edges.append(GraphEdge(
                                source=e1["entity_id"],
                                target=e2["entity_id"],
                                label=f"co-mentioned",
                                weight=1.0,
                                type="co_mention"
                            ))

        # Count connections and filter by min_connections
        connection_count: Dict[str, int] = defaultdict(int)
        for edge in edges:
            connection_count[edge.source] += 1
            connection_count[edge.target] += 1

        # Filter nodes by minimum connections
        if request.min_connections > 1:
            nodes = {
                nid: node for nid, node in nodes.items()
                if connection_count.get(nid, 0) >= request.min_connections
            }
            # Also filter edges
            valid_ids = set(nodes.keys())
            edges = [e for e in edges if e.source in valid_ids and e.target in valid_ids]

    # Include claims as nodes if requested
    if request.include_claims and nodes:
        # Get top claims for these entities
        claims_result = client.table("claim_entities").select(
            "claim_id, knowledge_claims(id, summary, claim_type, confidence_score)"
        ).in_("entity_id", list(nodes.keys())).limit(50).execute()

        seen_claims = set()
        for row in claims_result.data:
            claim_data = row.get("knowledge_claims")
            if claim_data and claim_data["id"] not in seen_claims:
                seen_claims.add(claim_data["id"])
                nodes[claim_data["id"]] = GraphNode(
                    id=claim_data["id"],
                    label=claim_data.get("summary", "")[:50] or "Claim",
                    type="claim",
                    size=8,
                    metadata={
                        "claim_type": claim_data.get("claim_type"),
                        "confidence": claim_data.get("confidence_score", 0.5)
                    }
                )

    # Detect clusters using simple connectivity
    clusters = _detect_clusters(nodes, edges)

    return NetworkGraphResponse(
        graph=GraphData(nodes=list(nodes.values()), edges=edges),
        stats={
            "node_count": len(nodes),
            "edge_count": len(edges),
            "cluster_count": len(clusters),
            "entity_types": len(set(n.type for n in nodes.values())),
        },
        clusters=clusters
    )


def _detect_clusters(nodes: Dict[str, GraphNode], edges: List[GraphEdge]) -> List[Dict[str, Any]]:
    """Simple connected components clustering."""
    if not nodes:
        return []

    # Build adjacency list
    adj: Dict[str, set] = defaultdict(set)
    for edge in edges:
        adj[edge.source].add(edge.target)
        adj[edge.target].add(edge.source)

    # Find connected components
    visited = set()
    clusters = []

    for node_id in nodes:
        if node_id not in visited:
            component = []
            stack = [node_id]
            while stack:
                current = stack.pop()
                if current not in visited:
                    visited.add(current)
                    component.append(current)
                    stack.extend(adj[current] - visited)

            if len(component) >= 2:
                clusters.append({
                    "id": str(uuid4())[:8],
                    "size": len(component),
                    "members": component[:10],  # Limit to first 10
                    "primary_type": nodes[component[0]].type if component else "unknown"
                })

    return sorted(clusters, key=lambda c: c["size"], reverse=True)[:10]


# =============================================================================
# TIMELINE API
# =============================================================================


@router.post("/timeline", response_model=TimelineResponse)
async def get_timeline(request: TimelineRequest):
    """
    Get chronological timeline of events/claims.

    Returns claims with temporal data, sorted by date.
    Supports filtering by date range, entities, and claim types.
    """
    client = get_supabase_client()

    # Build query for claims with dates
    query = client.table("knowledge_claims").select(
        "id, content, summary, claim_type, confidence_score, event_date, "
        "date_range_start, date_range_end, tags, extracted_data, created_at"
    ).eq("is_current", True)

    if request.topic_id:
        query = query.eq("topic_id", str(request.topic_id))

    if request.claim_types:
        query = query.in_("claim_type", request.claim_types)

    if request.min_confidence > 0:
        query = query.gte("confidence_score", request.min_confidence)

    # Must have some date information
    query = query.or_(
        "event_date.not.is.null,date_range_start.not.is.null"
    )

    if request.start_date:
        query = query.or_(
            f"event_date.gte.{request.start_date},date_range_start.gte.{request.start_date}"
        )

    if request.end_date:
        query = query.or_(
            f"event_date.lte.{request.end_date},date_range_end.lte.{request.end_date}"
        )

    # Get total count
    count_result = query.execute()
    total = len(count_result.data)

    # Apply pagination and ordering
    result = client.table("knowledge_claims").select(
        "id, content, summary, claim_type, confidence_score, event_date, "
        "date_range_start, date_range_end, tags, extracted_data, created_at"
    ).eq("is_current", True).or_(
        "event_date.not.is.null,date_range_start.not.is.null"
    ).order("event_date", desc=False, nullsfirst=False).range(
        request.offset, request.offset + request.limit - 1
    ).execute()

    # Get entity information for each claim
    claim_ids = [row["id"] for row in result.data]
    entities_by_claim: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    if claim_ids:
        entities_result = client.table("claim_entities").select(
            "claim_id, role, knowledge_entities(canonical_name, entity_type)"
        ).in_("claim_id", claim_ids).execute()

        for row in entities_result.data:
            entity_data = row.get("knowledge_entities")
            if entity_data:
                entities_by_claim[row["claim_id"]].append({
                    "name": entity_data["canonical_name"],
                    "type": entity_data["entity_type"],
                    "role": row.get("role", "mentioned")
                })

    # Get source counts
    sources_result = client.table("claim_sources").select(
        "claim_id", count="exact"
    ).in_("claim_id", claim_ids).execute()

    sources_by_claim: Dict[str, int] = {}
    # Count manually since supabase doesn't group
    source_counts: Dict[str, int] = defaultdict(int)
    sources_detail = client.table("claim_sources").select(
        "claim_id"
    ).in_("claim_id", claim_ids).execute()
    for row in sources_detail.data:
        source_counts[row["claim_id"]] += 1

    # Build timeline events
    events: List[TimelineEvent] = []
    entity_activity: Dict[str, int] = defaultdict(int)

    for row in result.data:
        event_date = row.get("event_date")
        date_start = row.get("date_range_start")
        date_end = row.get("date_range_end")

        events.append(TimelineEvent(
            id=row["id"],
            date=event_date,
            date_range_start=date_start,
            date_range_end=date_end,
            title=row.get("summary") or row["content"][:100],
            description=row["content"],
            claim_type=row["claim_type"],
            confidence=row.get("confidence_score", 0.5),
            entities=entities_by_claim.get(row["id"], []),
            sources_count=source_counts.get(row["id"], 0),
            tags=row.get("tags", [])
        ))

        # Track entity activity
        for entity in entities_by_claim.get(row["id"], []):
            entity_activity[entity["name"]] += 1

    # Determine actual date range
    date_range = {"min": None, "max": None}
    if events:
        dates = []
        for e in events:
            if e.date:
                dates.append(str(e.date))
            if e.date_range_start:
                dates.append(str(e.date_range_start))
            if e.date_range_end:
                dates.append(str(e.date_range_end))
        if dates:
            date_range["min"] = min(dates)
            date_range["max"] = max(dates)

    return TimelineResponse(
        events=events,
        total=total,
        date_range=date_range,
        entity_activity=dict(sorted(
            entity_activity.items(),
            key=lambda x: x[1],
            reverse=True
        )[:20])
    )


# =============================================================================
# EVIDENCE CORROBORATION API
# =============================================================================


@router.post("/corroborate", response_model=CorroborationResponse)
async def analyze_corroboration(request: CorroborationRequest):
    """
    Analyze evidence corroboration for claims.

    Calculates corroboration scores based on:
    - Number of independent sources
    - Source diversity (document vs web vs claim)
    - Support strength of each source
    """
    client = get_supabase_client()

    # Get claims to analyze
    claims_query = client.table("knowledge_claims").select(
        "id, content, summary, confidence_score, claim_type"
    ).eq("is_current", True)

    if request.claim_ids:
        claims_query = claims_query.in_("id", [str(cid) for cid in request.claim_ids])

    if request.topic_id:
        claims_query = claims_query.eq("topic_id", str(request.topic_id))

    if request.min_confidence > 0:
        claims_query = claims_query.gte("confidence_score", request.min_confidence)

    claims_query = claims_query.limit(request.limit)
    claims_result = claims_query.execute()

    if not claims_result.data:
        return CorroborationResponse(
            results=[],
            summary={"analyzed": 0},
            well_sourced_count=0,
            weak_sourced_count=0
        )

    claim_ids = [row["id"] for row in claims_result.data]

    # Get all sources for these claims
    sources_result = client.table("claim_sources").select(
        "claim_id, source_type, document_path, excerpt, support_strength, created_at"
    ).in_("claim_id", claim_ids).execute()

    # Group sources by claim
    sources_by_claim: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in sources_result.data:
        sources_by_claim[row["claim_id"]].append(row)

    # Get related claims
    relationships_result = client.table("claim_relationships").select(
        "source_claim_id, target_claim_id, relationship_type, strength"
    ).or_(
        f"source_claim_id.in.({','.join(claim_ids)}),target_claim_id.in.({','.join(claim_ids)})"
    ).execute()

    related_by_claim: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in relationships_result.data:
        if row["source_claim_id"] in claim_ids:
            related_by_claim[row["source_claim_id"]].append({
                "related_id": row["target_claim_id"],
                "type": row["relationship_type"],
                "strength": row.get("strength", 0.5)
            })
        if row["target_claim_id"] in claim_ids:
            related_by_claim[row["target_claim_id"]].append({
                "related_id": row["source_claim_id"],
                "type": row["relationship_type"],
                "strength": row.get("strength", 0.5)
            })

    # Analyze each claim
    results: List[CorroborationResult] = []
    well_sourced_count = 0
    weak_sourced_count = 0

    for claim in claims_result.data:
        claim_id = claim["id"]
        sources = sources_by_claim.get(claim_id, [])
        related = related_by_claim.get(claim_id, [])

        # Calculate metrics
        source_count = len(sources)
        source_types = set(s["source_type"] for s in sources)
        unique_source_types = len(source_types)

        avg_strength = 0.0
        if sources:
            avg_strength = sum(s.get("support_strength", 0.5) for s in sources) / len(sources)

        # Calculate corroboration score
        # Factors: source count, diversity, average strength
        count_factor = min(1.0, source_count / 5)  # Cap at 5 sources
        diversity_factor = min(1.0, unique_source_types / 3)  # Cap at 3 types
        corroboration_score = (count_factor * 0.4 + diversity_factor * 0.3 + avg_strength * 0.3)

        is_well_sourced = source_count >= request.min_source_count and unique_source_types >= 2
        if is_well_sourced:
            well_sourced_count += 1
        else:
            weak_sourced_count += 1

        results.append(CorroborationResult(
            claim_id=claim_id,
            claim_content=claim["content"],
            claim_summary=claim.get("summary"),
            source_count=source_count,
            unique_source_types=unique_source_types,
            average_support_strength=avg_strength,
            corroboration_score=corroboration_score,
            supporting_sources=[
                SourceEvidence(
                    source_type=s["source_type"],
                    source_path=s.get("document_path"),
                    excerpt=s.get("excerpt"),
                    support_strength=s.get("support_strength", 0.5),
                    created_at=s.get("created_at")
                )
                for s in sources[:10]  # Limit to 10 sources
            ],
            related_claims=related[:5],
            is_well_sourced=is_well_sourced,
            has_document_evidence="document" in source_types,
            has_web_evidence="web" in source_types
        ))

    # Sort by corroboration score
    results.sort(key=lambda r: r.corroboration_score, reverse=True)

    return CorroborationResponse(
        results=results,
        summary={
            "analyzed": len(results),
            "average_score": sum(r.corroboration_score for r in results) / len(results) if results else 0,
            "total_sources": sum(r.source_count for r in results),
        },
        well_sourced_count=well_sourced_count,
        weak_sourced_count=weak_sourced_count
    )


# =============================================================================
# PATTERN MINING API
# =============================================================================


@router.post("/patterns", response_model=PatternMiningResponse)
async def mine_patterns(request: PatternMiningRequest):
    """
    Detect patterns and anomalies in the knowledge base.

    Identifies:
    - Entity clusters (entities frequently appearing together)
    - Temporal bursts (spikes in activity)
    - Relationship chains (sequences of connections)
    - Anomalies (unusual patterns)
    """
    client = get_supabase_client()
    patterns: List[DetectedPattern] = []

    # 1. Entity Clusters - Find entities that frequently co-occur
    if not request.pattern_types or PatternType.ENTITY_CLUSTER in request.pattern_types:
        entity_clusters = await _find_entity_clusters(client, request)
        patterns.extend(entity_clusters)

    # 2. Temporal Bursts - Find periods with unusual activity
    if not request.pattern_types or PatternType.TEMPORAL_BURST in request.pattern_types:
        temporal_patterns = await _find_temporal_bursts(client, request)
        patterns.extend(temporal_patterns)

    # 3. Document Type Clusters
    if not request.pattern_types or PatternType.DOCUMENT_TYPE_CLUSTER in request.pattern_types:
        doc_patterns = await _find_document_type_patterns(client, request)
        patterns.extend(doc_patterns)

    # Filter by confidence and limit
    patterns = [p for p in patterns if p.confidence >= request.min_confidence]
    patterns.sort(key=lambda p: (p.significance, p.confidence), reverse=True)
    patterns = patterns[:request.limit]

    return PatternMiningResponse(
        patterns=patterns,
        stats={
            "patterns_found": len(patterns),
            "entity_clusters": sum(1 for p in patterns if p.pattern_type == PatternType.ENTITY_CLUSTER),
            "temporal_bursts": sum(1 for p in patterns if p.pattern_type == PatternType.TEMPORAL_BURST),
        },
        analysis_timestamp=datetime.utcnow()
    )


async def _find_entity_clusters(
    client,
    request: PatternMiningRequest
) -> List[DetectedPattern]:
    """Find entities that frequently appear together."""
    patterns = []

    # Get entity co-occurrence from claim_entities
    result = client.table("claim_entities").select(
        "claim_id, entity_id, knowledge_entities(canonical_name, entity_type)"
    ).limit(1000).execute()

    # Build co-occurrence matrix
    claim_to_entities: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in result.data:
        entity_info = row.get("knowledge_entities")
        if entity_info:
            claim_to_entities[row["claim_id"]].append({
                "id": row["entity_id"],
                "name": entity_info["canonical_name"],
                "type": entity_info["entity_type"]
            })

    # Count co-occurrences
    co_occurrence: Dict[tuple, int] = defaultdict(int)
    for claim_id, entities in claim_to_entities.items():
        if len(entities) >= 2:
            for i, e1 in enumerate(entities):
                for e2 in entities[i + 1:]:
                    key = tuple(sorted([e1["id"], e2["id"]]))
                    co_occurrence[key] += 1

    # Find significant clusters
    for (e1_id, e2_id), count in sorted(co_occurrence.items(), key=lambda x: x[1], reverse=True)[:10]:
        if count >= request.min_evidence_count:
            # Get entity names
            e1_data = next(
                (e for claims in claim_to_entities.values() for e in claims if e["id"] == e1_id),
                {"name": "Unknown", "type": "unknown"}
            )
            e2_data = next(
                (e for claims in claim_to_entities.values() for e in claims if e["id"] == e2_id),
                {"name": "Unknown", "type": "unknown"}
            )

            patterns.append(DetectedPattern(
                pattern_id=f"cluster-{e1_id[:8]}-{e2_id[:8]}",
                pattern_type=PatternType.ENTITY_CLUSTER,
                title=f"{e1_data['name']} ↔ {e2_data['name']}",
                description=f"These entities appear together in {count} claims, suggesting a significant relationship.",
                confidence=min(0.95, 0.5 + (count / 20)),
                significance=min(1.0, count / 10),
                involved_entities=[
                    {"id": e1_id, "name": e1_data["name"], "type": e1_data["type"]},
                    {"id": e2_id, "name": e2_data["name"], "type": e2_data["type"]}
                ],
                evidence_count=count
            ))

    return patterns


async def _find_temporal_bursts(
    client,
    request: PatternMiningRequest
) -> List[DetectedPattern]:
    """Find periods with unusual activity spikes."""
    patterns = []

    # Get claims with dates
    result = client.table("knowledge_claims").select(
        "id, event_date, date_range_start, summary, claim_type"
    ).eq("is_current", True).not_.is_("event_date", "null").order(
        "event_date"
    ).limit(500).execute()

    if not result.data:
        return patterns

    # Group by month
    month_counts: Dict[str, List[Dict]] = defaultdict(list)
    for row in result.data:
        date_str = row.get("event_date") or row.get("date_range_start")
        if date_str:
            month = date_str[:7]  # YYYY-MM
            month_counts[month].append(row)

    # Calculate average and find bursts
    if len(month_counts) >= 3:
        counts = [len(v) for v in month_counts.values()]
        avg_count = sum(counts) / len(counts)

        for month, claims in month_counts.items():
            if len(claims) >= avg_count * 2 and len(claims) >= request.min_evidence_count:
                patterns.append(DetectedPattern(
                    pattern_id=f"burst-{month}",
                    pattern_type=PatternType.TEMPORAL_BURST,
                    title=f"Activity Spike: {month}",
                    description=f"Unusual activity with {len(claims)} events (average: {avg_count:.1f}). "
                                f"This may indicate a significant period.",
                    confidence=min(0.9, 0.5 + (len(claims) / avg_count - 1) * 0.2),
                    significance=min(1.0, len(claims) / avg_count / 3),
                    time_range={"start": f"{month}-01", "end": f"{month}-28"},
                    involved_claims=[c["id"] for c in claims[:10]],
                    evidence_count=len(claims),
                    example_claims=[c.get("summary", c["id"])[:100] for c in claims[:3]]
                ))

    return patterns


async def _find_document_type_patterns(
    client,
    request: PatternMiningRequest
) -> List[DetectedPattern]:
    """Find patterns in document types."""
    patterns = []

    # Get tag distribution
    result = client.table("knowledge_claims").select(
        "id, tags, claim_type, extracted_data"
    ).eq("is_current", True).limit(500).execute()

    # Count document types from extracted_data and tags
    doc_type_counts: Dict[str, int] = defaultdict(int)
    for row in result.data:
        extracted = row.get("extracted_data") or {}
        doc_type = extracted.get("document_type", "unknown")
        doc_type_counts[doc_type] += 1

        for tag in row.get("tags", []):
            if "document" in tag.lower() or "log" in tag.lower() or "record" in tag.lower():
                doc_type_counts[tag] += 1

    # Find significant document type clusters
    total = sum(doc_type_counts.values())
    for doc_type, count in sorted(doc_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        if count >= request.min_evidence_count and doc_type != "unknown":
            percentage = (count / total) * 100 if total > 0 else 0
            patterns.append(DetectedPattern(
                pattern_id=f"doctype-{doc_type[:20].replace(' ', '-')}",
                pattern_type=PatternType.DOCUMENT_TYPE_CLUSTER,
                title=f"Document Type: {doc_type}",
                description=f"{count} documents ({percentage:.1f}% of collection) are classified as {doc_type}.",
                confidence=0.8,
                significance=min(1.0, count / 50),
                evidence_count=count
            ))

    return patterns


# =============================================================================
# INVESTIGATIVE Q&A API
# =============================================================================


@router.post("/ask", response_model=InvestigativeAnswer)
async def ask_question(request: InvestigativeQuestion):
    """
    Answer investigative questions using RAG.

    Searches the knowledge base for relevant claims,
    synthesizes an answer, and provides citations.
    """
    import time
    start_time = time.time()

    client = get_supabase_client()
    claims_db = ClaimOperations(client)

    # Search for relevant claims
    query_terms = request.question.lower().split()

    # Build search query
    search_query = client.table("knowledge_claims").select(
        "id, content, summary, claim_type, confidence_score, tags, extracted_data"
    ).eq("is_current", True)

    if request.topic_id:
        search_query = search_query.eq("topic_id", str(request.topic_id))

    if request.min_citation_confidence > 0:
        search_query = search_query.gte("confidence_score", request.min_citation_confidence)

    # Text search - search in content
    # For now, use simple ilike. Could use full-text search later.
    search_results = []
    for term in query_terms[:5]:  # Limit to 5 terms
        if len(term) >= 3:  # Skip short words
            result = search_query.ilike("content", f"%{term}%").limit(50).execute()
            search_results.extend(result.data)

    # Deduplicate
    seen_ids = set()
    unique_results = []
    for r in search_results:
        if r["id"] not in seen_ids:
            seen_ids.add(r["id"])
            unique_results.append(r)

    claims_searched = len(unique_results)

    # Score results by relevance
    scored_results = []
    for claim in unique_results:
        content_lower = claim["content"].lower()
        score = sum(1 for term in query_terms if term in content_lower)
        score += claim.get("confidence_score", 0.5)
        scored_results.append((score, claim))

    scored_results.sort(key=lambda x: x[0], reverse=True)
    top_claims = [c for _, c in scored_results[:request.max_citations]]

    # Get entity information for top claims
    claim_ids = [c["id"] for c in top_claims]
    entities_by_claim: Dict[str, List[str]] = defaultdict(list)

    if claim_ids:
        entities_result = client.table("claim_entities").select(
            "claim_id, knowledge_entities(canonical_name)"
        ).in_("claim_id", claim_ids).execute()

        for row in entities_result.data:
            entity_data = row.get("knowledge_entities")
            if entity_data:
                entities_by_claim[row["claim_id"]].append(entity_data["canonical_name"])

    # Get source documents
    sources_result = client.table("claim_sources").select(
        "claim_id, document_path"
    ).in_("claim_id", claim_ids).execute()

    sources_by_claim: Dict[str, List[str]] = defaultdict(list)
    for row in sources_result.data:
        if row.get("document_path"):
            sources_by_claim[row["claim_id"]].append(row["document_path"])

    # Build citations
    citations: List[Citation] = []
    for claim in top_claims:
        citations.append(Citation(
            claim_id=claim["id"],
            content_snippet=claim.get("summary") or claim["content"][:200],
            confidence=claim.get("confidence_score", 0.5),
            source_documents=sources_by_claim.get(claim["id"], [])[:3],
            entities_mentioned=entities_by_claim.get(claim["id"], [])[:5]
        ))

    # Generate answer using claims context
    # For now, synthesize from top claims. Could use LLM later.
    if citations:
        answer_parts = []
        for i, cit in enumerate(citations[:5], 1):
            answer_parts.append(f"[{i}] {cit.content_snippet}")
        answer = f"Based on {len(citations)} relevant findings:\n\n" + "\n\n".join(answer_parts)
    else:
        answer = "No relevant information found in the knowledge base for this question."

    # Identify key entities
    all_entities = set()
    for claim in top_claims:
        all_entities.update(entities_by_claim.get(claim["id"], []))

    key_entities = [{"name": e, "type": "person"} for e in list(all_entities)[:10]]

    # Identify gaps
    gaps = []
    if claims_searched < 5:
        gaps.append("Limited information available on this topic")
    if not any("document" in s for sources in sources_by_claim.values() for s in sources):
        gaps.append("No primary document sources found")

    # Generate follow-up questions
    follow_ups = []
    if key_entities:
        entity = key_entities[0]["name"]
        follow_ups.append(f"What is {entity}'s role in this matter?")
    follow_ups.append("What timeline of events can be established?")
    follow_ups.append("Are there corroborating sources for these claims?")

    processing_time = int((time.time() - start_time) * 1000)

    return InvestigativeAnswer(
        question=request.question,
        answer=answer,
        confidence=sum(c.confidence for c in citations) / len(citations) if citations else 0.0,
        citations=citations,
        citation_coverage=len(citations) / request.max_citations if citations else 0.0,
        key_entities=key_entities,
        timeline_context=None,  # Could extract from claims with dates
        gaps_identified=gaps,
        follow_up_questions=follow_ups[:3],
        claims_searched=claims_searched,
        processing_time_ms=processing_time
    )


# =============================================================================
# ENTITY PROFILE API
# =============================================================================


@router.post("/entity-profile", response_model=EntityProfile)
async def get_entity_profile(request: EntityProfileRequest):
    """
    Get comprehensive profile for an entity.

    Includes connections, timeline of mentions, and key claims.
    """
    client = get_supabase_client()

    # Get entity
    entity_result = client.table("knowledge_entities").select("*").eq(
        "id", str(request.entity_id)
    ).execute()

    if not entity_result.data:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity = entity_result.data[0]

    # Get claims for this entity
    claims_result = client.table("claim_entities").select(
        "claim_id, role, knowledge_claims(id, content, summary, claim_type, confidence_score, event_date, created_at)"
    ).eq("entity_id", str(request.entity_id)).limit(request.max_claims).execute()

    key_claims = []
    roles_played = set()
    dates = []

    for row in claims_result.data:
        claim_data = row.get("knowledge_claims")
        if claim_data:
            key_claims.append({
                "id": claim_data["id"],
                "summary": claim_data.get("summary") or claim_data["content"][:100],
                "type": claim_data["claim_type"],
                "confidence": claim_data.get("confidence_score", 0.5),
                "role": row.get("role", "mentioned"),
                "date": claim_data.get("event_date")
            })
            if row.get("role"):
                roles_played.add(row["role"])
            if claim_data.get("event_date"):
                dates.append(claim_data["event_date"])

    # Get connected entities (entities that share claims)
    connected_entities = []
    if request.include_connections and key_claims:
        claim_ids = [c["id"] for c in key_claims]
        connections_result = client.table("claim_entities").select(
            "entity_id, role, knowledge_entities(id, canonical_name, entity_type)"
        ).in_("claim_id", claim_ids).neq("entity_id", str(request.entity_id)).execute()

        entity_connections: Dict[str, Dict[str, Any]] = {}
        for row in connections_result.data:
            entity_data = row.get("knowledge_entities")
            if entity_data:
                eid = entity_data["id"]
                if eid not in entity_connections:
                    entity_connections[eid] = {
                        "id": eid,
                        "name": entity_data["canonical_name"],
                        "type": entity_data["entity_type"],
                        "shared_claims": 0,
                        "roles": set()
                    }
                entity_connections[eid]["shared_claims"] += 1
                if row.get("role"):
                    entity_connections[eid]["roles"].add(row["role"])

        connected_entities = sorted(
            [
                {**v, "roles": list(v["roles"])}
                for v in entity_connections.values()
            ],
            key=lambda x: x["shared_claims"],
            reverse=True
        )[:request.max_connections]

    # Build timeline
    activity_timeline = []
    if request.include_timeline and dates:
        dates.sort()
        first_date = dates[0] if dates else None
        last_date = dates[-1] if dates else None

        # Group by year
        year_counts: Dict[str, int] = defaultdict(int)
        for d in dates:
            year = d[:4] if d else "unknown"
            year_counts[year] += 1

        activity_timeline = [{"year": y, "count": c} for y, c in sorted(year_counts.items())]

    return EntityProfile(
        id=entity["id"],
        canonical_name=entity["canonical_name"],
        entity_type=entity["entity_type"],
        aliases=entity.get("aliases", []),
        description=entity.get("description"),
        mention_count=entity.get("mention_count", 0),
        claim_count=len(key_claims),
        connected_entities=connected_entities,
        first_mention_date=dates[0] if dates else None,
        last_mention_date=dates[-1] if dates else None,
        activity_timeline=activity_timeline,
        key_claims=key_claims[:20],
        roles_played=list(roles_played)
    )


# =============================================================================
# FINANCIAL TRANSACTIONS ENDPOINT
# =============================================================================


class FinancialTransactionQuery(BaseModel):
    """Query parameters for financial transactions."""
    workspace_id: str = Field(default="default")
    min_amount: Optional[float] = Field(default=None, description="Minimum transaction amount")
    max_amount: Optional[float] = Field(default=None, description="Maximum transaction amount")
    payer: Optional[str] = Field(default=None, description="Filter by payer name")
    payee: Optional[str] = Field(default=None, description="Filter by payee name")
    transaction_types: Optional[List[str]] = Field(default=None, description="Transaction types to include")
    start_date: Optional[str] = Field(default=None, description="Start date YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="End date YYYY-MM-DD")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class FinancialTransaction(BaseModel):
    """A financial transaction extracted from documents."""
    claim_id: UUID
    amount: float
    currency: str = "USD"
    payer: Optional[str] = None
    payee: Optional[str] = None
    transaction_type: str
    transaction_date: Optional[str] = None
    institution: Optional[str] = None
    purpose: Optional[str] = None
    source_document: Optional[str] = None
    confidence: float


class FinancialSummary(BaseModel):
    """Summary of financial transactions."""
    transactions: List[FinancialTransaction]
    total_count: int
    total_amount: float
    by_type: Dict[str, float] = Field(default_factory=dict)
    by_payer: Dict[str, float] = Field(default_factory=dict)
    by_payee: Dict[str, float] = Field(default_factory=dict)
    date_range: Dict[str, Optional[str]] = Field(default_factory=dict)


@router.post("/financial", response_model=FinancialSummary)
async def get_financial_transactions(request: FinancialTransactionQuery):
    """
    Query financial transactions from the knowledge base.

    Returns structured transaction data with filtering and aggregation.
    """
    client = get_supabase_client()

    # Query claims with type 'financial'
    query = client.table("knowledge_claims").select(
        "id, content, extracted_data, confidence_score, event_date"
    ).eq("claim_type", "financial").eq("is_current", True)

    result = query.order("event_date", desc=True).limit(request.limit).execute()

    transactions: List[FinancialTransaction] = []
    total_amount = 0.0
    by_type: Dict[str, float] = defaultdict(float)
    by_payer: Dict[str, float] = defaultdict(float)
    by_payee: Dict[str, float] = defaultdict(float)
    dates = []

    for row in result.data:
        extracted = row.get("extracted_data", {}) or {}
        amount = extracted.get("amount", 0)
        payer = extracted.get("payer")
        payee = extracted.get("payee")
        trans_type = extracted.get("transaction_type", "unknown")
        trans_date = extracted.get("transaction_date") or row.get("event_date")

        # Apply filters
        if request.min_amount and amount < request.min_amount:
            continue
        if request.max_amount and amount > request.max_amount:
            continue
        if request.payer and payer and request.payer.lower() not in payer.lower():
            continue
        if request.payee and payee and request.payee.lower() not in payee.lower():
            continue
        if request.transaction_types and trans_type not in request.transaction_types:
            continue
        if request.start_date and trans_date and trans_date < request.start_date:
            continue
        if request.end_date and trans_date and trans_date > request.end_date:
            continue

        transactions.append(FinancialTransaction(
            claim_id=row["id"],
            amount=amount,
            currency=extracted.get("currency", "USD"),
            payer=payer,
            payee=payee,
            transaction_type=trans_type,
            transaction_date=trans_date,
            institution=extracted.get("institution"),
            purpose=extracted.get("purpose"),
            source_document=extracted.get("source_document"),
            confidence=row.get("confidence_score", 0.5)
        ))

        # Aggregate
        total_amount += amount
        by_type[trans_type] += amount
        if payer and payer != "Unknown":
            by_payer[payer] += amount
        if payee and payee != "Unknown":
            by_payee[payee] += amount
        if trans_date:
            dates.append(trans_date)

    # Sort aggregations
    by_type = dict(sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10])
    by_payer = dict(sorted(by_payer.items(), key=lambda x: x[1], reverse=True)[:10])
    by_payee = dict(sorted(by_payee.items(), key=lambda x: x[1], reverse=True)[:10])

    date_range = {"min": None, "max": None}
    if dates:
        date_range["min"] = min(dates)
        date_range["max"] = max(dates)

    return FinancialSummary(
        transactions=transactions,
        total_count=len(transactions),
        total_amount=total_amount,
        by_type=by_type,
        by_payer=by_payer,
        by_payee=by_payee,
        date_range=date_range
    )


# =============================================================================
# ENTITY MANAGEMENT API
# =============================================================================


class EntityListResponse(BaseModel):
    """Response for entity listing."""
    entities: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int


class EntityUpdateRequest(BaseModel):
    """Request to update an entity."""
    canonical_name: Optional[str] = None
    aliases: Optional[List[str]] = None
    description: Optional[str] = None
    entity_type: Optional[str] = None


class EntityMergeRequest(BaseModel):
    """Request to merge entities."""
    target_id: UUID = Field(..., description="Entity to keep (merge into)")
    source_ids: List[UUID] = Field(..., description="Entities to merge and delete")


@router.get("/entities", response_model=EntityListResponse)
async def list_entities(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    search: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order_by: str = Query("mention_count", description="Field to order by"),
    order_desc: bool = Query(True, description="Order descending"),
):
    """List all entities with filtering and pagination."""
    client = get_supabase_client()
    entities_db = EntityOperations(client)

    if search:
        # Use search instead of list
        entities = await entities_db.search_entities(search, entity_type, limit)
        return EntityListResponse(
            entities=[{
                "id": str(e.id),
                "canonical_name": e.canonical_name,
                "entity_type": e.entity_type,
                "aliases": e.aliases,
                "mention_count": e.mention_count,
                "finding_count": e.finding_count,
                "description": e.description,
                "is_verified": e.is_verified,
            } for e in entities],
            total=len(entities),
            offset=offset,
            limit=limit
        )

    entities, total = await entities_db.list_entities(
        entity_type=entity_type,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_desc=order_desc
    )

    return EntityListResponse(
        entities=[{
            "id": str(e.id),
            "canonical_name": e.canonical_name,
            "entity_type": e.entity_type,
            "aliases": e.aliases,
            "mention_count": e.mention_count,
            "finding_count": e.finding_count,
            "description": e.description,
            "is_verified": e.is_verified,
        } for e in entities],
        total=total,
        offset=offset,
        limit=limit
    )


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: UUID):
    """Get a specific entity by ID."""
    client = get_supabase_client()
    entities_db = EntityOperations(client)

    entity = await entities_db.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return {
        "id": str(entity.id),
        "canonical_name": entity.canonical_name,
        "entity_type": entity.entity_type,
        "aliases": entity.aliases,
        "mention_count": entity.mention_count,
        "finding_count": entity.finding_count,
        "description": entity.description,
        "is_verified": entity.is_verified,
        "created_at": entity.created_at,
        "updated_at": entity.updated_at,
    }


@router.patch("/entities/{entity_id}")
async def update_entity(entity_id: UUID, request: EntityUpdateRequest):
    """Update an entity's properties."""
    client = get_supabase_client()
    entities_db = EntityOperations(client)

    updates = {}
    if request.canonical_name is not None:
        updates["canonical_name"] = request.canonical_name
        updates["name_hash"] = entities_db.hash_string(request.canonical_name)
    if request.aliases is not None:
        updates["aliases"] = request.aliases
    if request.description is not None:
        updates["description"] = request.description
    if request.entity_type is not None:
        updates["entity_type"] = request.entity_type

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    try:
        entity = await entities_db.update_entity(entity_id, updates)
        return {
            "id": str(entity.id),
            "canonical_name": entity.canonical_name,
            "entity_type": entity.entity_type,
            "aliases": entity.aliases,
            "message": "Entity updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/entities/{entity_id}")
async def delete_entity(entity_id: UUID):
    """Delete an entity and remove all references."""
    client = get_supabase_client()
    entities_db = EntityOperations(client)

    try:
        deleted = await entities_db.delete_entity(entity_id)
        if deleted:
            return {"message": "Entity deleted successfully", "id": str(entity_id)}
        else:
            raise HTTPException(status_code=404, detail="Entity not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entities/merge")
async def merge_entities(request: EntityMergeRequest):
    """Merge multiple entities into one. Source entities are deleted."""
    client = get_supabase_client()
    entities_db = EntityOperations(client)

    try:
        merged = await entities_db.merge_entities(request.target_id, request.source_ids)
        return {
            "id": str(merged.id),
            "canonical_name": merged.canonical_name,
            "aliases": merged.aliases,
            "merged_count": len(request.source_ids),
            "message": f"Successfully merged {len(request.source_ids)} entities"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATS ENDPOINT
# =============================================================================


@router.get("/stats")
async def get_knowledge_stats(workspace_id: str = "default"):
    """Get overall knowledge base statistics."""
    client = get_supabase_client()

    # Count claims
    claims_result = client.table("knowledge_claims").select(
        "id", count="exact"
    ).eq("is_current", True).execute()

    # Count entities
    entities_result = client.table("knowledge_entities").select(
        "id", count="exact"
    ).execute()

    # Count sources
    sources_result = client.table("claim_sources").select(
        "id", count="exact"
    ).execute()

    # Count topics
    topics_result = client.table("knowledge_topics").select(
        "id", count="exact"
    ).execute()

    # Get entity type distribution
    entity_types_result = client.table("knowledge_entities").select(
        "entity_type"
    ).execute()

    entity_type_counts: Dict[str, int] = defaultdict(int)
    for row in entity_types_result.data:
        entity_type_counts[row["entity_type"]] += 1

    # Get claim type distribution
    claim_types_result = client.table("knowledge_claims").select(
        "claim_type"
    ).eq("is_current", True).execute()

    claim_type_counts: Dict[str, int] = defaultdict(int)
    for row in claim_types_result.data:
        claim_type_counts[row["claim_type"]] += 1

    return {
        "total_claims": claims_result.count or len(claims_result.data),
        "total_entities": entities_result.count or len(entities_result.data),
        "total_sources": sources_result.count or len(sources_result.data),
        "total_topics": topics_result.count or len(topics_result.data),
        "entity_types": dict(entity_type_counts),
        "claim_types": dict(claim_type_counts),
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# PROFILE RESEARCH (LLM-POWERED)
# =============================================================================

class ProfileResearchRequest(BaseModel):
    """Request to research an entity profile."""
    entity_id: UUID
    date_context: Optional[str] = None  # e.g., "1990-2010"


class ConnectionResearchRequest(BaseModel):
    """Request to find connections between entities."""
    source_entity_id: UUID
    target_entity_ids: List[UUID]
    focus_areas: Optional[List[str]] = None  # e.g., ["financial", "ownership"]


@router.post("/profile-research")
async def research_entity_profile(request: ProfileResearchRequest):
    """
    Research an entity profile using LLM with web search.

    Finds:
    - Professional positions and roles over time
    - Company ownership and board memberships
    - Business affiliations
    - Key events and timeline
    """
    from .services.profile_research_service import ProfileResearchService

    client = get_supabase_client()
    db = get_supabase_db()

    # Get entity info
    entity_result = client.table("knowledge_entities").select(
        "id, canonical_name, entity_type"
    ).eq("id", str(request.entity_id)).single().execute()

    if not entity_result.data:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity = entity_result.data

    # Run research
    service = ProfileResearchService(db)
    result = await service.research_profile(
        entity_id=request.entity_id,
        entity_name=entity["canonical_name"],
        entity_type=entity["entity_type"],
        date_context=request.date_context,
    )

    # Save to database
    try:
        client.table("entity_profile_research").insert({
            "entity_id": str(request.entity_id),
            "positions": result.get("positions", []),
            "companies": result.get("companies", []),
            "affiliations": result.get("affiliations", []),
            "events": result.get("events", []),
            "associates": result.get("associates", []),
            "summary": result.get("summary", ""),
            "sources": result.get("sources", []),
            "raw_text": result.get("raw_text", ""),
        }).execute()
    except Exception as e:
        logger.warning("Failed to save profile research: %s", e)

    return result


@router.post("/connection-research")
async def research_entity_connections(request: ConnectionResearchRequest):
    """
    Find connections between a source entity and target entities.

    Searches for:
    - Business relationships and transactions
    - Ownership and investment connections
    - Personal/professional relationships
    - Shared affiliations or events

    Tracks researched pairs to prevent repetition.
    """
    from .services.profile_research_service import ProfileResearchService

    client = get_supabase_client()
    db = get_supabase_db()

    # Get source entity info
    source_result = client.table("knowledge_entities").select(
        "id, canonical_name, entity_type"
    ).eq("id", str(request.source_entity_id)).single().execute()

    if not source_result.data:
        raise HTTPException(status_code=404, detail="Source entity not found")

    source_entity = source_result.data

    # Get target entities info
    target_entities = []
    for target_id in request.target_entity_ids:
        target_result = client.table("knowledge_entities").select(
            "id, canonical_name, entity_type"
        ).eq("id", str(target_id)).single().execute()

        if target_result.data:
            target_entities.append({
                "id": target_result.data["id"],
                "name": target_result.data["canonical_name"],
                "type": target_result.data["entity_type"],
            })

    if not target_entities:
        raise HTTPException(status_code=400, detail="No valid target entities found")

    # Run research
    service = ProfileResearchService(db)
    result = await service.find_connections(
        source_entity_id=request.source_entity_id,
        source_entity_name=source_entity["canonical_name"],
        target_entities=target_entities,
        focus_areas=request.focus_areas,
    )

    return result


@router.get("/research-pairs/{entity_id}")
async def get_entity_research_pairs(
    entity_id: UUID,
    limit: int = Query(default=50, le=200),
):
    """
    Get all entities that have been researched against a given entity.
    Shows connection strength and research date.
    """
    client = get_supabase_client()

    # Query both directions of the pair
    result_a = client.table("entity_research_pairs").select(
        "entity_b_id, connection_strength, connections_count, summary, research_date"
    ).eq("entity_a_id", str(entity_id)).limit(limit).execute()

    result_b = client.table("entity_research_pairs").select(
        "entity_a_id, connection_strength, connections_count, summary, research_date"
    ).eq("entity_b_id", str(entity_id)).limit(limit).execute()

    pairs = []

    for row in result_a.data:
        pairs.append({
            "other_entity_id": row["entity_b_id"],
            "connection_strength": row["connection_strength"],
            "connections_count": row["connections_count"],
            "summary": row["summary"],
            "research_date": row["research_date"],
        })

    for row in result_b.data:
        pairs.append({
            "other_entity_id": row["entity_a_id"],
            "connection_strength": row["connection_strength"],
            "connections_count": row["connections_count"],
            "summary": row["summary"],
            "research_date": row["research_date"],
        })

    # Get entity names for the pairs
    other_ids = [p["other_entity_id"] for p in pairs]
    if other_ids:
        entities_result = client.table("knowledge_entities").select(
            "id, canonical_name"
        ).in_("id", other_ids).execute()

        name_map = {e["id"]: e["canonical_name"] for e in entities_result.data}
        for pair in pairs:
            pair["other_entity_name"] = name_map.get(pair["other_entity_id"], "Unknown")

    return {
        "entity_id": str(entity_id),
        "researched_pairs": pairs,
        "total": len(pairs),
    }


@router.get("/profile-research/{entity_id}")
async def get_entity_profile_research(entity_id: UUID):
    """
    Get previously researched profile information for an entity.
    Returns the most recent research if available.
    """
    client = get_supabase_client()

    result = client.table("entity_profile_research").select(
        "*"
    ).eq("entity_id", str(entity_id)).order(
        "research_date", desc=True
    ).limit(1).execute()

    if not result.data:
        return {"entity_id": str(entity_id), "research": None}

    research = result.data[0]
    return {
        "entity_id": str(entity_id),
        "research": {
            "research_date": research["research_date"],
            "positions": research["positions"],
            "companies": research["companies"],
            "affiliations": research["affiliations"],
            "events": research["events"],
            "associates": research["associates"],
            "summary": research["summary"],
            "sources": research["sources"],
        }
    }
