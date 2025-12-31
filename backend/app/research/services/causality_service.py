"""Causality Service for temporal cause-effect analysis.

Extracts and manages causal relationships between events/claims.
Builds causal graphs and detects causal patterns.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from uuid import UUID, uuid4

from ..db import SupabaseResearchDB
from ..lib.clients import GeminiResearchClient, SearchMode
from ..schemas.causality import (
    CausalityType,
    CausalMechanism,
    PatternType,
    CausalLink,
    CausalChain,
    CausalPattern,
    CausalGraph,
    GraphNode,
    GraphEdge,
    ExtractCausalityRequest,
    FindCausesRequest,
    FindCausesResponse,
    FindConsequencesRequest,
    FindConsequencesResponse,
    BuildCausalGraphRequest,
    DetectPatternsRequest,
    DetectPatternsResponse,
    PatternSummary,
)

logger = logging.getLogger(__name__)


class CausalityService:
    """
    Extracts and manages causal relationships between events/claims.
    Builds causal graphs and detects causal patterns.

    Key Features:
    - LLM-based causality extraction with counterfactual reasoning
    - Causal chain tracing (causes and consequences)
    - Pattern detection (cover-ups, enabling networks, etc.)
    - Auto-extraction during research (when integrated with recursive service)
    """

    # Prompt for extracting causality between events
    CAUSALITY_EXTRACTION_PROMPT = """Analyze the causal relationship between these two events:

Event A: {event_a}
Event B: {event_b}

Additional context: {context}

Determine:
1. Is there a causal relationship? (yes/no/uncertain)
2. What type of relationship?
   - caused_by: A directly caused B
   - enabled_by: A was necessary for B but didn't directly cause it
   - prevented_by: A prevented B from happening
   - triggered_by: A was the immediate trigger for B
   - preceded: A happened before B but no clear causation
   - resulted_in: B is a consequence of A
   - contributed_to: A partially contributed to B
3. What is the mechanism? (financial, legal, organizational, informational, social, physical, political)
4. Confidence level (0.0-1.0)
5. Counterfactual test: "If A hadn't happened, would B still have occurred?"

Return JSON:
{{
    "has_causal_relationship": true/false,
    "causality_type": "caused_by|enabled_by|prevented_by|triggered_by|preceded|resulted_in|contributed_to",
    "direction": "a_to_b|b_to_a|bidirectional|none",
    "mechanism": "financial|legal|organizational|informational|social|physical|political|null",
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation of the causal link",
    "counterfactual": "If A hadn't happened, then...",
    "temporal_gap_estimate": "days/weeks/months/years/unknown",
    "evidence_needed": ["what additional evidence would confirm this"]
}}"""

    # Prompt for pattern detection
    PATTERN_DETECTION_PROMPT = """Analyze this set of events and relationships for causal patterns:

Events/Claims:
{events}

Known Relationships:
{relationships}

Entities Involved:
{entities}

Look for these pattern types:
1. **Enabling Network**: Multiple people/organizations enabling a single bad outcome
2. **Cover-up**: Sequence of actions to hide wrongdoing or obstruct investigation
3. **Escalation**: Events getting progressively worse over time
4. **Protection**: People/orgs protecting each other from consequences
5. **Retaliation**: Actions taken in response to threats or exposure
6. **Obstruction**: Deliberate interference with investigation or legal process
7. **Money Laundering**: Financial transactions designed to obscure source/destination
8. **Recruitment**: Pattern of bringing new participants into a scheme

Return JSON:
{{
    "patterns": [
        {{
            "type": "enabling_network|cover_up|escalation|protection|retaliation|obstruction|money_laundering|recruitment",
            "name": "short descriptive name for this specific instance",
            "description": "detailed description of what this pattern shows",
            "involved_entities": ["entity names involved"],
            "key_events": ["event descriptions that form this pattern"],
            "confidence": 0.0-1.0,
            "significance": "why this pattern matters for the investigation"
        }}
    ]
}}"""

    def __init__(
        self,
        db: SupabaseResearchDB,
        gemini_client: Optional[GeminiResearchClient] = None,
    ):
        self.db = db
        self._gemini = gemini_client

    async def _get_gemini(self) -> Optional[GeminiResearchClient]:
        """Lazy load Gemini client."""
        if self._gemini is None:
            try:
                self._gemini = GeminiResearchClient(search_mode=SearchMode.GROUNDED)
            except (ImportError, ValueError) as e:
                logger.warning("Could not create GeminiResearchClient: %s", e)
        return self._gemini

    async def extract_causality(
        self,
        request: ExtractCausalityRequest,
    ) -> CausalLink:
        """
        Determine causal relationship between two events using LLM.
        Returns the most likely causal link with confidence and reasoning.
        """
        gemini = await self._get_gemini()
        if not gemini:
            return CausalLink(
                source_event=request.event_a,
                target_event=request.event_b,
                causality_type=CausalityType.PRECEDED,
                confidence=0.1,
                reasoning="LLM client not available",
            )

        prompt = self.CAUSALITY_EXTRACTION_PROMPT.format(
            event_a=request.event_a,
            event_b=request.event_b,
            context=request.context or "None provided",
        )

        try:
            result, _ = await gemini.generate_json(prompt, temperature=0.3)

            if not result.get("has_causal_relationship"):
                return CausalLink(
                    source_event=request.event_a,
                    target_event=request.event_b,
                    causality_type=CausalityType.PRECEDED,
                    confidence=0.1,
                    reasoning="No clear causal relationship detected",
                )

            # Determine source and target based on direction
            direction = result.get("direction", "a_to_b")
            if direction == "b_to_a":
                source_event = request.event_b
                target_event = request.event_a
                source_claim_id = request.event_b_claim_id
                target_claim_id = request.event_a_claim_id
            else:
                source_event = request.event_a
                target_event = request.event_b
                source_claim_id = request.event_a_claim_id
                target_claim_id = request.event_b_claim_id

            # Parse mechanism
            mechanism = None
            if result.get("mechanism"):
                try:
                    mechanism = CausalMechanism(result["mechanism"])
                except ValueError:
                    pass

            # Estimate temporal gap in days
            temporal_gap = self._estimate_temporal_gap(result.get("temporal_gap_estimate"))

            link = CausalLink(
                source_event=source_event,
                source_claim_id=source_claim_id,
                target_event=target_event,
                target_claim_id=target_claim_id,
                causality_type=CausalityType(result["causality_type"]),
                confidence=float(result.get("confidence", 0.5)),
                mechanism=mechanism,
                temporal_gap_days=temporal_gap,
                reasoning=result.get("reasoning", ""),
                counterfactual=result.get("counterfactual"),
                evidence=result.get("evidence_needed", []),
            )

            # Save to database
            await self._save_causal_link(link, request.workspace_id)

            return link

        except Exception as e:
            logger.error(f"Causality extraction failed: {e}")
            return CausalLink(
                source_event=request.event_a,
                target_event=request.event_b,
                causality_type=CausalityType.PRECEDED,
                confidence=0.1,
                reasoning=f"Extraction failed: {str(e)}",
            )

    async def find_causes(
        self,
        request: FindCausesRequest,
    ) -> FindCausesResponse:
        """
        Find all causes (direct and indirect) of an event.
        Traces back through causal chains to root causes.
        """
        direct_causes: List[CausalLink] = []
        causal_chains: List[CausalChain] = []
        root_causes: Set[str] = set()
        visited: Set[str] = set()
        max_depth_reached = 0

        async def trace_causes(
            current_event: str,
            current_claim_id: Optional[UUID],
            current_chain: List[CausalLink],
            depth: int,
        ):
            nonlocal max_depth_reached
            max_depth_reached = max(max_depth_reached, depth)

            if depth >= request.max_depth:
                return

            # Avoid cycles
            event_key = f"{current_event}_{current_claim_id or ''}"
            if event_key in visited:
                return
            visited.add(event_key)

            # Get causes from database
            causes = await self._get_causes_of(
                current_event,
                current_claim_id,
                request.min_confidence,
                request.workspace_id,
            )

            if not causes:
                # This is a root cause
                if current_chain:
                    root_causes.add(current_event)
                    chain = self._build_causal_chain(
                        current_chain,
                        "cause_chain",
                    )
                    causal_chains.append(chain)
                return

            if depth == 0:
                direct_causes.extend(causes)

            for cause in causes:
                await trace_causes(
                    cause.source_event,
                    cause.source_claim_id,
                    current_chain + [cause],
                    depth + 1,
                )

        await trace_causes(
            request.event,
            request.event_claim_id,
            [],
            0,
        )

        return FindCausesResponse(
            event=request.event,
            event_claim_id=request.event_claim_id,
            direct_causes=direct_causes,
            causal_chains=causal_chains,
            root_causes=list(root_causes),
            total_causes_found=len(visited) - 1,  # Exclude starting event
            max_depth_reached=max_depth_reached,
        )

    async def find_consequences(
        self,
        request: FindConsequencesRequest,
    ) -> FindConsequencesResponse:
        """
        Find all consequences (direct and indirect) of an event.
        Traces forward through causal chains to final outcomes.
        """
        direct_consequences: List[CausalLink] = []
        consequence_chains: List[CausalChain] = []
        final_outcomes: Set[str] = set()
        visited: Set[str] = set()
        max_depth_reached = 0

        async def trace_consequences(
            current_event: str,
            current_claim_id: Optional[UUID],
            current_chain: List[CausalLink],
            depth: int,
        ):
            nonlocal max_depth_reached
            max_depth_reached = max(max_depth_reached, depth)

            if depth >= request.max_depth:
                return

            event_key = f"{current_event}_{current_claim_id or ''}"
            if event_key in visited:
                return
            visited.add(event_key)

            # Get consequences from database
            consequences = await self._get_consequences_of(
                current_event,
                current_claim_id,
                request.min_confidence,
                request.workspace_id,
            )

            if not consequences:
                # This is a final outcome
                if current_chain:
                    final_outcomes.add(current_event)
                    chain = self._build_causal_chain(
                        current_chain,
                        "consequence_chain",
                    )
                    consequence_chains.append(chain)
                return

            if depth == 0:
                direct_consequences.extend(consequences)

            for consequence in consequences:
                await trace_consequences(
                    consequence.target_event,
                    consequence.target_claim_id,
                    current_chain + [consequence],
                    depth + 1,
                )

        await trace_consequences(
            request.event,
            request.event_claim_id,
            [],
            0,
        )

        return FindConsequencesResponse(
            event=request.event,
            event_claim_id=request.event_claim_id,
            direct_consequences=direct_consequences,
            consequence_chains=consequence_chains,
            final_outcomes=list(final_outcomes),
            total_consequences_found=len(visited) - 1,
            max_depth_reached=max_depth_reached,
        )

    async def build_causal_graph(
        self,
        request: BuildCausalGraphRequest,
    ) -> CausalGraph:
        """
        Build complete causal graph for a topic.
        Identifies patterns and key causal relationships.
        """
        gemini = await self._get_gemini()

        # Get claims related to topic
        claims = await self._get_claims_by_topic(
            request.topic,
            request.topic_id,
            request.workspace_id,
            request.time_start,
            request.time_end,
            request.max_nodes,
        )

        if not claims:
            return CausalGraph(
                topic=request.topic,
                topic_id=request.topic_id,
            )

        # Sort by date
        claims_sorted = sorted(
            claims,
            key=lambda c: c.get("temporal_context", {}).get("date") or "9999",
        )

        # Build nodes
        nodes = []
        for c in claims_sorted[:request.max_nodes]:
            nodes.append(GraphNode(
                id=str(c["id"]),
                label=c["content"][:100],
                type=c.get("claim_type", "fact"),
                date=c.get("temporal_context", {}).get("date"),
                entity_mentions=c.get("entities", []),
            ))

        # Extract causality between adjacent/related events
        edges = []
        for i, claim_a in enumerate(claims_sorted[:20]):  # Limit for performance
            for claim_b in claims_sorted[i+1:i+5]:  # Check next 4 events
                # Check existing relationships first
                existing = await self._get_existing_causal_link(
                    UUID(claim_a["id"]),
                    UUID(claim_b["id"]),
                )

                if existing:
                    edges.append(existing)
                elif gemini:
                    # Extract new causality
                    link = await self.extract_causality(
                        ExtractCausalityRequest(
                            event_a=claim_a["content"],
                            event_a_claim_id=UUID(claim_a["id"]),
                            event_b=claim_b["content"],
                            event_b_claim_id=UUID(claim_b["id"]),
                            workspace_id=request.workspace_id,
                        )
                    )
                    if link.confidence >= request.min_confidence:
                        edges.append(GraphEdge(
                            source=str(link.source_claim_id or claim_a["id"]),
                            target=str(link.target_claim_id or claim_b["id"]),
                            type=link.causality_type.value,
                            confidence=link.confidence,
                            mechanism=link.mechanism.value if link.mechanism else None,
                        ))

        # Detect patterns
        patterns = await self._detect_patterns(
            nodes,
            edges,
            request.entity_focus,
            request.workspace_id,
        )

        # Identify root causes and final outcomes
        node_ids = {n.id for n in nodes}
        source_ids = {e.source for e in edges}
        target_ids = {e.target for e in edges}

        root_nodes = node_ids - target_ids  # No incoming edges
        leaf_nodes = node_ids - source_ids  # No outgoing edges

        key_causes = [n.label for n in nodes if n.id in root_nodes][:5]
        key_consequences = [n.label for n in nodes if n.id in leaf_nodes][:5]

        return CausalGraph(
            topic=request.topic,
            topic_id=request.topic_id,
            nodes=nodes,
            edges=edges,
            key_causes=key_causes,
            key_consequences=key_consequences,
            patterns_detected=patterns,
            total_nodes=len(nodes),
            total_edges=len(edges),
        )

    async def detect_patterns(
        self,
        request: DetectPatternsRequest,
    ) -> DetectPatternsResponse:
        """Detect causal patterns in the knowledge base."""
        # Get relevant events and relationships
        events = await self._get_events_for_pattern_detection(
            request.topic_id,
            request.entity_ids,
            request.workspace_id,
        )

        relationships = await self._get_relationships_for_pattern_detection(
            request.topic_id,
            request.entity_ids,
            request.workspace_id,
        )

        entities = await self._get_entities_for_pattern_detection(
            request.entity_ids,
            request.workspace_id,
        )

        if not events:
            return DetectPatternsResponse(patterns=[], summary_by_type=[], total_patterns=0)

        # Use LLM to detect patterns
        patterns = await self._detect_patterns_with_llm(
            events,
            relationships,
            entities,
            request.pattern_types,
            request.min_confidence,
            request.workspace_id,
        )

        # Build summary by type
        summary = self._build_pattern_summary(patterns)

        return DetectPatternsResponse(
            patterns=patterns,
            summary_by_type=summary,
            total_patterns=len(patterns),
        )

    # ========================================
    # Database Operations
    # ========================================

    async def _save_causal_link(self, link: CausalLink, workspace_id: str):
        """Save a causal link to the database."""
        try:
            self.db.client.table("causal_links").insert({
                "id": str(uuid4()),
                "source_event": link.source_event,
                "source_claim_id": str(link.source_claim_id) if link.source_claim_id else None,
                "target_event": link.target_event,
                "target_claim_id": str(link.target_claim_id) if link.target_claim_id else None,
                "causality_type": link.causality_type.value,
                "confidence": link.confidence,
                "mechanism": link.mechanism.value if link.mechanism else None,
                "temporal_gap_days": link.temporal_gap_days,
                "reasoning": link.reasoning,
                "counterfactual": link.counterfactual,
                "evidence": link.evidence,
                "workspace_id": workspace_id,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save causal link: {e}")

    async def _get_causes_of(
        self,
        event: str,
        claim_id: Optional[UUID],
        min_confidence: float,
        workspace_id: str,
    ) -> List[CausalLink]:
        """Get known causes of an event from database."""
        query = self.db.client.table("causal_links").select("*").eq(
            "workspace_id", workspace_id
        ).gte("confidence", min_confidence)

        if claim_id:
            query = query.eq("target_claim_id", str(claim_id))
        else:
            query = query.ilike("target_event", f"%{event[:50]}%")

        result = query.execute()

        return [
            CausalLink(
                source_event=r["source_event"],
                source_claim_id=UUID(r["source_claim_id"]) if r.get("source_claim_id") else None,
                target_event=r["target_event"],
                target_claim_id=UUID(r["target_claim_id"]) if r.get("target_claim_id") else None,
                causality_type=CausalityType(r["causality_type"]),
                confidence=r["confidence"],
                mechanism=CausalMechanism(r["mechanism"]) if r.get("mechanism") else None,
                temporal_gap_days=r.get("temporal_gap_days"),
                reasoning=r.get("reasoning", ""),
            )
            for r in result.data or []
        ]

    async def _get_consequences_of(
        self,
        event: str,
        claim_id: Optional[UUID],
        min_confidence: float,
        workspace_id: str,
    ) -> List[CausalLink]:
        """Get known consequences of an event from database."""
        query = self.db.client.table("causal_links").select("*").eq(
            "workspace_id", workspace_id
        ).gte("confidence", min_confidence)

        if claim_id:
            query = query.eq("source_claim_id", str(claim_id))
        else:
            query = query.ilike("source_event", f"%{event[:50]}%")

        result = query.execute()

        return [
            CausalLink(
                source_event=r["source_event"],
                source_claim_id=UUID(r["source_claim_id"]) if r.get("source_claim_id") else None,
                target_event=r["target_event"],
                target_claim_id=UUID(r["target_claim_id"]) if r.get("target_claim_id") else None,
                causality_type=CausalityType(r["causality_type"]),
                confidence=r["confidence"],
                mechanism=CausalMechanism(r["mechanism"]) if r.get("mechanism") else None,
                temporal_gap_days=r.get("temporal_gap_days"),
                reasoning=r.get("reasoning", ""),
            )
            for r in result.data or []
        ]

    async def _get_existing_causal_link(
        self,
        claim_a_id: UUID,
        claim_b_id: UUID,
    ) -> Optional[GraphEdge]:
        """Check if a causal link already exists between two claims."""
        result = self.db.client.table("causal_links").select("*").or_(
            f"source_claim_id.eq.{claim_a_id},target_claim_id.eq.{claim_b_id},"
            f"source_claim_id.eq.{claim_b_id},target_claim_id.eq.{claim_a_id}"
        ).limit(1).execute()

        if result.data:
            r = result.data[0]
            return GraphEdge(
                source=r["source_claim_id"] or "",
                target=r["target_claim_id"] or "",
                type=r["causality_type"],
                confidence=r["confidence"],
                mechanism=r.get("mechanism"),
            )
        return None

    async def _get_claims_by_topic(
        self,
        topic: str,
        topic_id: Optional[UUID],
        workspace_id: str,
        time_start: Optional[datetime],
        time_end: Optional[datetime],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Get claims related to a topic."""
        query = self.db.client.table("knowledge_claims").select("*").eq(
            "workspace_id", workspace_id
        )

        # Search by topic name
        query = query.ilike("content", f"%{topic}%")

        result = query.limit(limit).execute()
        return result.data or []

    async def _get_events_for_pattern_detection(
        self,
        topic_id: Optional[UUID],
        entity_ids: Optional[List[UUID]],
        workspace_id: str,
    ) -> List[Dict[str, Any]]:
        """Get events for pattern detection."""
        query = self.db.client.table("knowledge_claims").select("*").eq(
            "workspace_id", workspace_id
        ).eq("claim_type", "event")

        result = query.limit(50).execute()
        return result.data or []

    async def _get_relationships_for_pattern_detection(
        self,
        topic_id: Optional[UUID],
        entity_ids: Optional[List[UUID]],
        workspace_id: str,
    ) -> List[Dict[str, Any]]:
        """Get relationships for pattern detection."""
        result = self.db.client.table("causal_links").select("*").eq(
            "workspace_id", workspace_id
        ).limit(100).execute()
        return result.data or []

    async def _get_entities_for_pattern_detection(
        self,
        entity_ids: Optional[List[UUID]],
        workspace_id: str,
    ) -> List[Dict[str, Any]]:
        """Get entities for pattern detection."""
        query = self.db.client.table("knowledge_entities").select("*").eq(
            "workspace_id", workspace_id
        )

        if entity_ids:
            query = query.in_("id", [str(e) for e in entity_ids])

        result = query.limit(50).execute()
        return result.data or []

    async def _detect_patterns(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        entity_focus: Optional[List[str]],
        workspace_id: str,
    ) -> List[CausalPattern]:
        """Detect patterns using LLM."""
        gemini = await self._get_gemini()
        if not gemini or not nodes:
            return []

        events_text = "\n".join([f"- {n.label} ({n.date or 'unknown date'})" for n in nodes[:20]])
        relationships_text = "\n".join([f"- {e.type}: {e.source[:30]} → {e.target[:30]}" for e in edges[:20]])
        entities_text = ", ".join(set(e for n in nodes for e in n.entity_mentions))[:500]

        prompt = self.PATTERN_DETECTION_PROMPT.format(
            events=events_text,
            relationships=relationships_text or "No relationships identified yet.",
            entities=entities_text or "Various entities",
        )

        try:
            result, _ = await gemini.generate_json(prompt, temperature=0.3)

            patterns = []
            for p in result.get("patterns", []):
                try:
                    pattern = CausalPattern(
                        pattern_id=uuid4(),
                        pattern_name=p["name"],
                        pattern_type=PatternType(p["type"]),
                        description=p.get("description", ""),
                        involved_entities=p.get("involved_entities", []),
                        events=p.get("key_events", []),
                        confidence=float(p.get("confidence", 0.5)),
                        first_detected_at=datetime.utcnow(),
                    )
                    patterns.append(pattern)

                    # Save pattern to database
                    await self._save_pattern(pattern, workspace_id)

                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid pattern format: {e}")

            return patterns

        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return []

    async def _detect_patterns_with_llm(
        self,
        events: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        pattern_types: Optional[List[PatternType]],
        min_confidence: float,
        workspace_id: str,
    ) -> List[CausalPattern]:
        """Detect patterns using LLM with full context."""
        gemini = await self._get_gemini()
        if not gemini:
            return []

        # Format for prompt
        events_text = "\n".join([f"- {e.get('content', '')[:100]}" for e in events[:30]])
        rel_text = "\n".join([f"- {r.get('causality_type', '')}: {r.get('source_event', '')[:50]} → {r.get('target_event', '')[:50]}" for r in relationships[:30]])
        entities_text = ", ".join([e.get("canonical_name", "") for e in entities[:20]])

        prompt = self.PATTERN_DETECTION_PROMPT.format(
            events=events_text,
            relationships=rel_text or "No relationships identified.",
            entities=entities_text or "Various entities",
        )

        try:
            result, _ = await gemini.generate_json(prompt, temperature=0.4)

            patterns = []
            for p in result.get("patterns", []):
                try:
                    p_type = PatternType(p["type"])

                    # Filter by requested types
                    if pattern_types and p_type not in pattern_types:
                        continue

                    confidence = float(p.get("confidence", 0.5))
                    if confidence < min_confidence:
                        continue

                    pattern = CausalPattern(
                        pattern_id=uuid4(),
                        pattern_name=p["name"],
                        pattern_type=p_type,
                        description=p.get("description", ""),
                        involved_entities=p.get("involved_entities", []),
                        events=p.get("key_events", []),
                        confidence=confidence,
                        first_detected_at=datetime.utcnow(),
                    )
                    patterns.append(pattern)

                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid pattern: {e}")

            return patterns

        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return []

    async def _save_pattern(self, pattern: CausalPattern, workspace_id: str):
        """Save a detected pattern to the database."""
        try:
            self.db.client.table("causal_patterns").insert({
                "id": str(pattern.pattern_id),
                "pattern_name": pattern.pattern_name,
                "pattern_type": pattern.pattern_type.value,
                "description": pattern.description,
                "involved_entities": pattern.involved_entity_ids,
                "claim_ids": pattern.claim_ids,
                "confidence": pattern.confidence,
                "first_detected_at": datetime.utcnow().isoformat(),
                "occurrence_count": 1,
                "workspace_id": workspace_id,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to save pattern: {e}")

    # ========================================
    # Helper Methods
    # ========================================

    def _build_causal_chain(
        self,
        links: List[CausalLink],
        chain_type: str,
    ) -> CausalChain:
        """Build a causal chain from a list of links."""
        if not links:
            return CausalChain(
                chain_type=chain_type,
                events=[],
                links=[],
                total_confidence=0.0,
                chain_length=0,
                narrative="Empty chain",
            )

        events = [links[0].source_event]
        events.extend([l.target_event for l in links])

        # Calculate total confidence as product
        total_conf = 1.0
        for l in links:
            total_conf *= l.confidence

        # Build narrative
        narrative_parts = []
        for i, link in enumerate(links):
            if i == 0:
                narrative_parts.append(f"{link.source_event}")
            verb = self._get_causality_verb(link.causality_type)
            narrative_parts.append(f"{verb} {link.target_event}")

        narrative = " → ".join(narrative_parts) if len(narrative_parts) <= 3 else f"{events[0]} → ... → {events[-1]}"

        # Calculate time span
        time_span = None
        if all(l.temporal_gap_days for l in links):
            time_span = sum(l.temporal_gap_days for l in links)

        return CausalChain(
            chain_type=chain_type,
            events=events,
            claim_ids=[l.source_claim_id for l in links if l.source_claim_id] +
                      [links[-1].target_claim_id] if links[-1].target_claim_id else [],
            links=links,
            total_confidence=total_conf,
            chain_length=len(links),
            narrative=narrative,
            time_span_days=time_span,
        )

    def _get_causality_verb(self, causality_type: CausalityType) -> str:
        """Get verb phrase for causality type."""
        verbs = {
            CausalityType.CAUSED_BY: "caused",
            CausalityType.ENABLED_BY: "enabled",
            CausalityType.PREVENTED_BY: "prevented",
            CausalityType.TRIGGERED_BY: "triggered",
            CausalityType.PRECEDED: "preceded",
            CausalityType.RESULTED_IN: "resulted in",
            CausalityType.CONTRIBUTED_TO: "contributed to",
        }
        return verbs.get(causality_type, "led to")

    def _estimate_temporal_gap(self, estimate: Optional[str]) -> Optional[int]:
        """Convert temporal gap estimate to days."""
        if not estimate:
            return None

        estimate_lower = estimate.lower()
        if "day" in estimate_lower:
            return 1
        elif "week" in estimate_lower:
            return 7
        elif "month" in estimate_lower:
            return 30
        elif "year" in estimate_lower:
            return 365
        return None

    def _build_pattern_summary(self, patterns: List[CausalPattern]) -> List[PatternSummary]:
        """Build summary statistics by pattern type."""
        type_groups: Dict[PatternType, List[CausalPattern]] = {}

        for p in patterns:
            if p.pattern_type not in type_groups:
                type_groups[p.pattern_type] = []
            type_groups[p.pattern_type].append(p)

        summaries = []
        for p_type, group in type_groups.items():
            summaries.append(PatternSummary(
                pattern_type=p_type,
                pattern_count=len(group),
                avg_confidence=sum(p.confidence for p in group) / len(group),
                total_occurrences=sum(p.occurrences for p in group),
                pattern_names=[p.pattern_name for p in group],
            ))

        return sorted(summaries, key=lambda s: s.pattern_count, reverse=True)
