"""Recursive Chain-of-Investigation Research Service.

Executes N-level recursive research by automatically generating
and pursuing follow-up questions until saturation or limits are reached.
"""

import asyncio
import logging
import time
import hashlib
from datetime import datetime
from typing import AsyncGenerator, Optional, List, Dict, Any, Set, Tuple
from uuid import UUID, uuid4

from ..db import SupabaseResearchDB
from ..lib.clients import GeminiResearchClient, SearchMode
from ..schemas.recursive import (
    RecursiveResearchConfig,
    StartRecursiveResearchRequest,
    FollowUpType,
    FollowUpQuestion,
    NodeStatus,
    TreeStatus,
    SkipReason,
    ResearchNodeStatus,
    ResearchNodeDetail,
    NodeFinding,
    ResearchTreeStatus,
    ResearchTreeResult,
    ReasoningChain,
)

logger = logging.getLogger(__name__)


class RecursiveResearchService:
    """
    Executes N-level recursive research by automatically generating
    and pursuing follow-up questions until saturation or limits.

    Key Features:
    - Automatic follow-up generation (predecessors, consequences, details)
    - Saturation detection to avoid redundant research
    - Parallel node execution within depth levels
    - Cost and token tracking
    - Auto-invocation of financial and causality services
    """

    # Follow-up generation prompt template
    FOLLOW_UP_PROMPT = """Based on this research query and its findings, generate follow-up questions.

Original Query: {query}

Findings:
{findings}

Generate follow-up questions for these types: {follow_up_types}

For PREDECESSOR questions, ask "What caused this?", "What enabled this?", "Who introduced X to Y?", "What was the source of this?"
For CONSEQUENCE questions, ask "What resulted from this?", "What happened next?", "How did this affect X?", "What were the outcomes?"
For DETAIL questions, ask for specific dates, amounts, locations, participants, evidence.
For VERIFICATION questions, ask "Is this claim verified?", "What is the evidence for X?", "Are there contradicting reports?"
For FINANCIAL questions, ask about money flows, transactions, property transfers, company ownership.
For TEMPORAL questions, ask about timeline, sequence of events, what happened before/after.

Already researched (DO NOT repeat these or very similar questions):
{existing_queries}

Return JSON:
{{
    "follow_ups": [
        {{
            "query": "specific question that advances the investigation",
            "type": "predecessor|consequence|detail|verification|financial|temporal",
            "priority": 0.0-1.0 (higher = more important for understanding),
            "reasoning": "why this follow-up matters for the investigation"
        }}
    ]
}}

Generate 3-7 high-quality follow-up questions. Focus on questions that would reveal new, important information."""

    # Saturation check prompt
    SATURATION_PROMPT = """Analyze how much of this query's answer space is already known.

Query: {query}

Existing knowledge on this topic:
{existing_knowledge}

New findings from research:
{new_findings}

Return JSON:
{{
    "saturation_score": 0.0-1.0 (0.0 = completely novel, 1.0 = everything already known),
    "novel_aspects": ["list of new information not in existing knowledge"],
    "redundant_aspects": ["list of information that was already known"],
    "reasoning": "explanation of saturation assessment"
}}"""

    # Keywords that indicate financial analysis would be valuable
    FINANCIAL_KEYWORDS = [
        "money", "payment", "transaction", "transfer", "fund", "invest",
        "donation", "grant", "loan", "salary", "compensation", "fee",
        "account", "bank", "wire", "shell company", "offshore", "trust",
        "foundation", "llc", "corporation", "asset", "property", "real estate",
        "million", "billion", "dollar", "usd", "eur", "gbp", "financial",
        "escrow", "laundering", "embezzlement", "fraud", "bribe", "payoff",
    ]

    def __init__(
        self,
        db: SupabaseResearchDB,
        gemini_client: Optional[GeminiResearchClient] = None,
    ):
        self.db = db
        self._gemini = gemini_client
        self._financial_service = None
        self._causality_service = None

    async def _get_gemini(self) -> Optional[GeminiResearchClient]:
        """Lazy load Gemini client."""
        if self._gemini is None:
            try:
                self._gemini = GeminiResearchClient(search_mode=SearchMode.GROUNDED)
            except (ImportError, ValueError) as e:
                logger.warning("Could not create GeminiResearchClient: %s", e)
        return self._gemini

    async def _get_financial_service(self):
        """Lazy load FinancialResearchService."""
        if self._financial_service is None:
            try:
                from .financial_research_service import FinancialResearchService
                self._financial_service = FinancialResearchService(
                    db=self.db,
                    gemini_client=await self._get_gemini(),
                )
            except Exception as e:
                logger.warning("Could not create FinancialResearchService: %s", e)
        return self._financial_service

    async def _get_causality_service(self):
        """Lazy load CausalityService."""
        if self._causality_service is None:
            try:
                from .causality_service import CausalityService
                self._causality_service = CausalityService(
                    db=self.db,
                    gemini_client=await self._get_gemini(),
                )
            except Exception as e:
                logger.warning("Could not create CausalityService: %s", e)
        return self._causality_service

    def _is_financial_query(self, query: str, findings: List[NodeFinding]) -> bool:
        """Detect if query or findings warrant financial analysis."""
        query_lower = query.lower()

        # Check query for financial keywords
        for keyword in self.FINANCIAL_KEYWORDS:
            if keyword in query_lower:
                return True

        # Check findings for financial indicators
        for finding in findings[:10]:
            content_lower = finding.content.lower()
            keyword_count = sum(1 for kw in self.FINANCIAL_KEYWORDS if kw in content_lower)
            if keyword_count >= 2:
                return True

        return False

    def _extract_financial_entities(
        self,
        query: str,
        findings: List[NodeFinding],
    ) -> List[str]:
        """Extract entity names that should be analyzed financially."""
        entities = set()

        # Collect all mentioned entities from findings
        for finding in findings:
            for entity in finding.entities_mentioned:
                entities.add(entity)

        # Prioritize entities mentioned in financial context
        financial_entities = []
        for finding in findings:
            content_lower = finding.content.lower()
            has_financial = any(kw in content_lower for kw in self.FINANCIAL_KEYWORDS)
            if has_financial:
                for entity in finding.entities_mentioned:
                    if entity not in financial_entities:
                        financial_entities.append(entity)

        return financial_entities[:5] if financial_entities else list(entities)[:3]

    async def _auto_invoke_financial(
        self,
        node_id: UUID,
        query: str,
        findings: List[NodeFinding],
        workspace_id: str,
    ) -> Dict[str, Any]:
        """
        Auto-invoke financial analysis when relevant.
        Returns summary of financial findings.
        """
        financial_service = await self._get_financial_service()
        if not financial_service:
            return {"status": "skipped", "reason": "service_unavailable"}

        entities = self._extract_financial_entities(query, findings)
        if not entities:
            return {"status": "skipped", "reason": "no_entities"}

        results = {
            "status": "completed",
            "traces": [],
            "shell_companies": [],
            "entities_analyzed": entities,
        }

        try:
            # Import request schema
            from ..schemas.financial import TraceMoneyRequest

            # Run trace_money for primary entity
            primary_entity = entities[0]
            request = TraceMoneyRequest(
                entity_name=primary_entity,
                workspace_id=workspace_id,
                max_hops=3,
                include_shell_detection=True,
            )
            trace_result = await financial_service.trace_money(request)

            if trace_result and trace_result.chains_found > 0:
                all_chains = trace_result.forward_chains + trace_result.backward_chains
                results["traces"].append({
                    "entity": primary_entity,
                    "chains_found": trace_result.chains_found,
                    "total_inflow": float(trace_result.total_inflow or 0),
                    "total_outflow": float(trace_result.total_outflow or 0),
                    "suspicious_patterns": trace_result.suspicious_patterns,
                    "shell_companies": [
                        s.name for s in trace_result.shell_companies_detected
                    ] if trace_result.shell_companies_detected else [],
                })

                # Store shell company findings
                if trace_result.shell_companies_detected:
                    results["shell_companies"].extend([
                        {
                            "name": s.name,
                            "jurisdiction": s.jurisdiction,
                            "entity_type": s.entity_type.value if s.entity_type else "unknown",
                        }
                        for s in trace_result.shell_companies_detected
                    ])

            logger.info(f"Node {node_id}: Financial analysis completed for {primary_entity}")

        except Exception as e:
            logger.warning(f"Financial auto-invocation failed: {e}")
            results["status"] = "partial"
            results["error"] = str(e)

        return results

    async def _auto_extract_causality(
        self,
        node_id: UUID,
        findings: List[NodeFinding],
        workspace_id: str,
    ) -> Dict[str, Any]:
        """
        Auto-extract causality from findings.
        Returns summary of causal relationships found.
        """
        causality_service = await self._get_causality_service()
        if not causality_service:
            return {"status": "skipped", "reason": "service_unavailable"}

        if not findings:
            return {"status": "skipped", "reason": "no_findings"}

        # Import request schemas
        from ..schemas.causality import FindCausesRequest, FindConsequencesRequest

        results = {
            "status": "completed",
            "causes_found": 0,
            "consequences_found": 0,
            "root_causes": [],
            "final_outcomes": [],
        }

        try:
            # For findings that represent events, find their causes and consequences
            event_findings = [
                f for f in findings[:5]
                if f.confidence >= 0.5 and f.finding_type in ("event", "fact", "claim")
            ]

            for finding in event_findings:
                # Find causes of this event
                try:
                    causes_request = FindCausesRequest(
                        event=finding.content,
                        workspace_id=workspace_id,
                        max_depth=2,  # Shallow depth for auto-extraction
                        min_confidence=0.4,
                    )
                    causes_result = await causality_service.find_causes(causes_request)
                    if causes_result:
                        results["causes_found"] += len(causes_result.direct_causes)
                        if causes_result.root_causes:
                            results["root_causes"].extend(causes_result.root_causes[:2])
                except Exception as e:
                    logger.debug(f"Find causes failed for finding: {e}")

                # Find consequences of this event
                try:
                    consequences_request = FindConsequencesRequest(
                        event=finding.content,
                        workspace_id=workspace_id,
                        max_depth=2,  # Shallow depth for auto-extraction
                        min_confidence=0.4,
                    )
                    consequences_result = await causality_service.find_consequences(consequences_request)
                    if consequences_result:
                        results["consequences_found"] += len(consequences_result.direct_consequences)
                        if consequences_result.final_outcomes:
                            results["final_outcomes"].extend(consequences_result.final_outcomes[:2])
                except Exception as e:
                    logger.debug(f"Find consequences failed for finding: {e}")

            # Deduplicate and limit
            results["root_causes"] = list(set(results["root_causes"]))[:5]
            results["final_outcomes"] = list(set(results["final_outcomes"]))[:5]

            total_links = results["causes_found"] + results["consequences_found"]
            logger.info(f"Node {node_id}: Causality extraction found {total_links} links")

        except Exception as e:
            logger.warning(f"Causality auto-extraction failed: {e}")
            results["status"] = "partial"
            results["error"] = str(e)

        return results

    async def start_recursive_research(
        self,
        request: StartRecursiveResearchRequest,
    ) -> AsyncGenerator[ResearchTreeStatus, None]:
        """
        Main entry point. Creates tree and processes nodes breadth-first.
        Yields status updates as nodes complete.
        """
        config = request.config or RecursiveResearchConfig()
        start_time = time.time()

        # Create research tree record
        tree_id = await self._create_tree(request, config)

        yield ResearchTreeStatus(
            tree_id=tree_id,
            root_query=request.query,
            status=TreeStatus.RUNNING,
            total_nodes=1,
            completed_nodes=0,
            pending_nodes=1,
            max_depth_reached=0,
            progress_pct=0.0,
        )

        # Create root node
        root_node_id = await self._create_node(
            tree_id=tree_id,
            query=request.query,
            query_type="initial",
            depth=0,
            parent_node_id=None,
        )

        # Track all queries to avoid duplicates
        existing_queries: Set[str] = {request.query.lower().strip()}
        total_tokens = 0

        try:
            # Process nodes level by level (BFS with parallel execution)
            current_depth = 0
            while current_depth <= config.depth_limit:
                # Get pending nodes at current depth
                pending_nodes = await self._get_pending_nodes(tree_id, current_depth)

                if not pending_nodes:
                    # No more nodes at this depth, try next
                    current_depth += 1
                    continue

                # Check total node limit
                total_nodes = await self._get_total_nodes(tree_id)
                if total_nodes >= config.max_nodes:
                    logger.info(f"Tree {tree_id}: Max nodes ({config.max_nodes}) reached")
                    break

                # Process nodes in parallel batches
                batch_size = min(config.parallel_nodes, len(pending_nodes))
                for i in range(0, len(pending_nodes), batch_size):
                    batch = pending_nodes[i:i + batch_size]

                    # Process batch in parallel
                    tasks = [
                        self._process_node(
                            node_id=node["id"],
                            tree_id=tree_id,
                            config=config,
                            existing_queries=existing_queries,
                            focus_entities=request.focus_entities,
                        )
                        for node in batch
                    ]

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Collect results and update queries
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Node processing error: {result}")
                            continue
                        if result:
                            findings, follow_ups, tokens = result
                            total_tokens += tokens
                            for fu in follow_ups:
                                existing_queries.add(fu.query.lower().strip())

                    # Yield progress update
                    completed = await self._get_completed_nodes(tree_id)
                    total = await self._get_total_nodes(tree_id)
                    pending = total - completed

                    yield ResearchTreeStatus(
                        tree_id=tree_id,
                        root_query=request.query,
                        status=TreeStatus.RUNNING,
                        total_nodes=total,
                        completed_nodes=completed,
                        pending_nodes=pending,
                        max_depth_reached=current_depth,
                        progress_pct=(completed / total * 100) if total > 0 else 0,
                        total_tokens_used=total_tokens,
                        estimated_cost_usd=self._estimate_cost(total_tokens),
                    )

                current_depth += 1

            # Mark tree as completed
            duration = time.time() - start_time
            await self._complete_tree(tree_id, duration, total_tokens)

            # Final status
            completed = await self._get_completed_nodes(tree_id)
            total = await self._get_total_nodes(tree_id)
            max_depth = await self._get_max_depth(tree_id)

            yield ResearchTreeStatus(
                tree_id=tree_id,
                root_query=request.query,
                status=TreeStatus.COMPLETED,
                total_nodes=total,
                completed_nodes=completed,
                pending_nodes=0,
                max_depth_reached=max_depth,
                progress_pct=100.0,
                total_tokens_used=total_tokens,
                estimated_cost_usd=self._estimate_cost(total_tokens),
            )

        except Exception as e:
            logger.error(f"Recursive research failed: {e}")
            await self._fail_tree(tree_id, str(e))
            yield ResearchTreeStatus(
                tree_id=tree_id,
                root_query=request.query,
                status=TreeStatus.FAILED,
                total_nodes=0,
                completed_nodes=0,
                pending_nodes=0,
                max_depth_reached=0,
                progress_pct=0.0,
            )

    async def _process_node(
        self,
        node_id: UUID,
        tree_id: UUID,
        config: RecursiveResearchConfig,
        existing_queries: Set[str],
        focus_entities: Optional[List[str]] = None,
    ) -> Optional[Tuple[List[NodeFinding], List[FollowUpQuestion], int]]:
        """
        Execute research for a single node and generate follow-ups.
        """
        gemini = await self._get_gemini()
        if not gemini:
            return None

        # Get node details
        node = await self._get_node(node_id)
        if not node:
            return None

        # Mark node as running
        await self._update_node_status(node_id, NodeStatus.RUNNING)
        start_time = time.time()
        total_tokens = 0

        try:
            # Execute research
            response = await gemini.grounded_search(
                node["query"],
                temperature=0.3,
            )
            total_tokens += response.usage.get("total_tokens", 0) if hasattr(response, "usage") else 1000

            # Extract findings
            findings = await self._extract_findings(gemini, node["query"], response.text)
            total_tokens += 500  # Estimate for extraction

            # Calculate saturation score
            saturation = await self._calculate_saturation(
                gemini,
                node["query"],
                findings,
                node.get("workspace_id", "default"),
            )
            total_tokens += 300  # Estimate for saturation

            # Save findings
            for finding in findings:
                await self._save_finding(node_id, finding)

            # Auto-invoke financial analysis if relevant
            workspace_id = node.get("workspace_id", "default")
            if self._is_financial_query(node["query"], findings):
                financial_results = await self._auto_invoke_financial(
                    node_id=node_id,
                    query=node["query"],
                    findings=findings,
                    workspace_id=workspace_id,
                )
                total_tokens += 1000  # Estimate for financial analysis
                logger.debug(f"Node {node_id}: Financial analysis: {financial_results.get('status')}")

            # Auto-extract causality from all findings
            causality_results = await self._auto_extract_causality(
                node_id=node_id,
                findings=findings,
                workspace_id=workspace_id,
            )
            total_tokens += 500  # Estimate for causality extraction
            logger.debug(f"Node {node_id}: Causality extraction: {causality_results.get('status')}")

            # Generate follow-up questions if not saturated
            follow_ups = []
            if saturation < config.saturation_threshold and node["depth"] < config.depth_limit:
                follow_ups = await self._generate_follow_ups(
                    gemini=gemini,
                    node_query=node["query"],
                    findings=findings,
                    follow_up_types=config.follow_up_types,
                    existing_queries=existing_queries,
                    focus_entities=focus_entities,
                )
                total_tokens += 500  # Estimate for follow-up generation

                # Filter and create child nodes
                filtered = self._filter_follow_ups(follow_ups, config, existing_queries)
                for fu in filtered[:config.max_follow_ups_per_node]:
                    child_id = await self._create_node(
                        tree_id=tree_id,
                        query=fu.query,
                        query_type=fu.follow_up_type.value,
                        depth=node["depth"] + 1,
                        parent_node_id=node_id,
                    )
                    # Save follow-up record
                    await self._save_follow_up(node_id, fu, child_id)

            # Mark node as completed
            execution_time = int((time.time() - start_time) * 1000)
            await self._complete_node(
                node_id=node_id,
                saturation_score=saturation,
                findings_count=len(findings),
                new_entities_count=self._count_entities(findings),
                execution_time_ms=execution_time,
            )

            return findings, follow_ups, total_tokens

        except Exception as e:
            logger.error(f"Node {node_id} processing failed: {e}")
            await self._update_node_status(node_id, NodeStatus.SKIPPED, SkipReason.IRRELEVANT)
            return None

    async def _generate_follow_ups(
        self,
        gemini: GeminiResearchClient,
        node_query: str,
        findings: List[NodeFinding],
        follow_up_types: List[FollowUpType],
        existing_queries: Set[str],
        focus_entities: Optional[List[str]] = None,
    ) -> List[FollowUpQuestion]:
        """Use LLM to generate follow-up questions based on findings."""
        # Format findings for prompt
        findings_text = "\n".join([
            f"- {f.content} (confidence: {f.confidence:.2f})"
            for f in findings[:10]
        ])

        # Format existing queries (sample to avoid token limits)
        existing_sample = list(existing_queries)[:20]
        existing_text = "\n".join([f"- {q}" for q in existing_sample])

        prompt = self.FOLLOW_UP_PROMPT.format(
            query=node_query,
            findings=findings_text or "No specific findings extracted.",
            follow_up_types=", ".join([t.value for t in follow_up_types]),
            existing_queries=existing_text or "None yet.",
        )

        try:
            result, _ = await gemini.generate_json(prompt, temperature=0.4)

            follow_ups = []
            for fu in result.get("follow_ups", []):
                try:
                    follow_up = FollowUpQuestion(
                        query=fu["query"],
                        follow_up_type=FollowUpType(fu["type"]),
                        priority_score=float(fu.get("priority", 0.5)),
                        reasoning=fu.get("reasoning", ""),
                    )

                    # Boost priority if mentions focus entities
                    if focus_entities:
                        for entity in focus_entities:
                            if entity.lower() in fu["query"].lower():
                                follow_up.priority_score = min(1.0, follow_up.priority_score + 0.2)
                                break

                    follow_ups.append(follow_up)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid follow-up format: {e}")
                    continue

            return follow_ups

        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return []

    async def _calculate_saturation(
        self,
        gemini: GeminiResearchClient,
        query: str,
        findings: List[NodeFinding],
        workspace_id: str,
    ) -> float:
        """
        Calculate how much of this query's answer space is already known.
        Returns 0.0 (novel) to 1.0 (fully saturated).
        """
        # Get existing knowledge about this topic
        existing = await self._get_related_claims(query, workspace_id)

        if not existing:
            # No existing knowledge, not saturated
            return 0.0

        findings_text = "\n".join([f.content for f in findings[:10]])
        existing_text = "\n".join(existing[:10])

        prompt = self.SATURATION_PROMPT.format(
            query=query,
            existing_knowledge=existing_text or "No existing knowledge.",
            new_findings=findings_text or "No new findings.",
        )

        try:
            result, _ = await gemini.generate_json(prompt, temperature=0.2)
            return float(result.get("saturation_score", 0.3))
        except Exception as e:
            logger.warning(f"Saturation calculation failed: {e}")
            return 0.3  # Default to moderate saturation

    async def _extract_findings(
        self,
        gemini: GeminiResearchClient,
        query: str,
        raw_text: str,
    ) -> List[NodeFinding]:
        """Extract structured findings from raw research text."""
        prompt = f"""Extract key findings from this research response.

Query: {query}

Research Response:
{raw_text[:6000]}

Return JSON:
{{
    "findings": [
        {{
            "content": "A specific fact, claim, or event",
            "finding_type": "fact|claim|event|relationship|quote",
            "confidence": 0.0-1.0,
            "evidence_strength": "high|medium|low|alleged",
            "entities_mentioned": ["entity names mentioned"],
            "temporal_context": {{"date": "YYYY-MM-DD or null", "period": "description or null"}}
        }}
    ]
}}

Extract 3-10 most important findings. Focus on specific, verifiable information."""

        try:
            result, _ = await gemini.generate_json(prompt, temperature=0.2)

            findings = []
            for f in result.get("findings", []):
                content_hash = hashlib.md5(f.get("content", "").encode()).hexdigest()
                findings.append(NodeFinding(
                    content=f.get("content", ""),
                    finding_type=f.get("finding_type", "fact"),
                    confidence=float(f.get("confidence", 0.5)),
                    evidence_strength=f.get("evidence_strength", "medium"),
                    entities_mentioned=f.get("entities_mentioned", []),
                    temporal_context=f.get("temporal_context", {}),
                ))

            return findings

        except Exception as e:
            logger.warning(f"Finding extraction failed: {e}")
            return []

    def _filter_follow_ups(
        self,
        follow_ups: List[FollowUpQuestion],
        config: RecursiveResearchConfig,
        existing_queries: Set[str],
    ) -> List[FollowUpQuestion]:
        """Filter and prioritize follow-up questions."""
        filtered = []
        for fu in follow_ups:
            # Skip if already researched
            if fu.query.lower().strip() in existing_queries:
                continue
            # Skip if below priority threshold
            if fu.priority_score < config.min_priority_score:
                continue
            # Skip if not in allowed types
            if fu.follow_up_type not in config.follow_up_types:
                continue
            filtered.append(fu)

        # Sort by priority, take top N
        filtered.sort(key=lambda x: x.priority_score, reverse=True)
        return filtered

    async def get_tree_result(self, tree_id: UUID) -> Optional[ResearchTreeResult]:
        """Compile final results from completed tree."""
        tree = await self._get_tree(tree_id)
        if not tree:
            return None

        config = RecursiveResearchConfig(**tree.get("config", {}))

        # Get all nodes
        nodes = await self._get_all_nodes(tree_id)

        # Build reasoning chains (paths from root to leaves)
        reasoning_chains = await self._build_reasoning_chains(tree_id, nodes)

        # Get all findings
        all_findings = []
        total_entities = set()
        for node in nodes:
            findings = await self._get_node_findings(node["id"])
            all_findings.extend(findings)
            for f in findings:
                total_entities.update(f.get("entities_mentioned", []))

        # Generate key insights
        key_insights = await self._generate_key_insights(tree["root_query"], all_findings)

        completed_nodes = len([n for n in nodes if n["status"] == "completed"])
        skipped_nodes = len([n for n in nodes if n["status"] == "skipped"])

        return ResearchTreeResult(
            tree_id=tree_id,
            root_query=tree["root_query"],
            config=config,
            status=TreeStatus(tree["status"]),
            total_nodes=len(nodes),
            completed_nodes=completed_nodes,
            skipped_nodes=skipped_nodes,
            max_depth_reached=tree.get("max_depth_reached", 0),
            total_findings=len(all_findings),
            total_entities_discovered=len(total_entities),
            key_insights=key_insights,
            reasoning_chains=reasoning_chains,
            duration_seconds=tree.get("duration_seconds", 0),
            total_tokens_used=tree.get("total_tokens_used", 0),
            estimated_cost_usd=tree.get("estimated_cost_usd", 0),
            created_at=datetime.fromisoformat(tree["created_at"]) if tree.get("created_at") else datetime.utcnow(),
            completed_at=datetime.fromisoformat(tree["completed_at"]) if tree.get("completed_at") else None,
        )

    async def get_reasoning_chain(
        self,
        tree_id: UUID,
        leaf_node_id: UUID,
    ) -> List[str]:
        """Get the question chain from root to a specific leaf node."""
        chain = []
        current_id = leaf_node_id

        while current_id:
            node = await self._get_node(current_id)
            if not node:
                break
            chain.insert(0, node["query"])
            current_id = node.get("parent_node_id")

        return chain

    # ========================================
    # Database Operations
    # ========================================

    async def _create_tree(
        self,
        request: StartRecursiveResearchRequest,
        config: RecursiveResearchConfig,
    ) -> UUID:
        """Create a new research tree record."""
        tree_id = uuid4()
        result = self.db.client.table("research_trees").insert({
            "id": str(tree_id),
            "root_query": request.query,
            "workspace_id": request.workspace_id,
            "config": config.model_dump(),
            "status": "running",
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
        return tree_id

    async def _create_node(
        self,
        tree_id: UUID,
        query: str,
        query_type: str,
        depth: int,
        parent_node_id: Optional[UUID],
    ) -> UUID:
        """Create a new research node."""
        node_id = uuid4()
        try:
            self.db.client.table("research_nodes").insert({
                "id": str(node_id),
                "tree_id": str(tree_id),
                "parent_node_id": str(parent_node_id) if parent_node_id else None,
                "query": query,
                "query_type": query_type,
                "depth": depth,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            # Handle duplicate query (unique constraint)
            if "duplicate" in str(e).lower():
                logger.debug(f"Duplicate query skipped: {query[:50]}")
                return None
            raise
        return node_id

    async def _get_node(self, node_id: UUID) -> Optional[Dict[str, Any]]:
        """Get node by ID."""
        result = self.db.client.table("research_nodes").select("*").eq(
            "id", str(node_id)
        ).single().execute()
        return result.data if result.data else None

    async def _get_tree(self, tree_id: UUID) -> Optional[Dict[str, Any]]:
        """Get tree by ID."""
        result = self.db.client.table("research_trees").select("*").eq(
            "id", str(tree_id)
        ).single().execute()
        return result.data if result.data else None

    async def _get_pending_nodes(self, tree_id: UUID, depth: int) -> List[Dict[str, Any]]:
        """Get pending nodes at a specific depth."""
        result = self.db.client.table("research_nodes").select("*").eq(
            "tree_id", str(tree_id)
        ).eq("depth", depth).eq("status", "pending").execute()
        return result.data or []

    async def _get_all_nodes(self, tree_id: UUID) -> List[Dict[str, Any]]:
        """Get all nodes in a tree."""
        result = self.db.client.table("research_nodes").select("*").eq(
            "tree_id", str(tree_id)
        ).order("depth").execute()
        return result.data or []

    async def _get_total_nodes(self, tree_id: UUID) -> int:
        """Get total node count for a tree."""
        result = self.db.client.table("research_nodes").select(
            "id", count="exact"
        ).eq("tree_id", str(tree_id)).execute()
        return result.count or 0

    async def _get_completed_nodes(self, tree_id: UUID) -> int:
        """Get completed node count for a tree."""
        result = self.db.client.table("research_nodes").select(
            "id", count="exact"
        ).eq("tree_id", str(tree_id)).eq("status", "completed").execute()
        return result.count or 0

    async def _get_max_depth(self, tree_id: UUID) -> int:
        """Get maximum depth reached in a tree."""
        result = self.db.client.table("research_nodes").select("depth").eq(
            "tree_id", str(tree_id)
        ).eq("status", "completed").order("depth", desc=True).limit(1).execute()
        return result.data[0]["depth"] if result.data else 0

    async def _update_node_status(
        self,
        node_id: UUID,
        status: NodeStatus,
        skip_reason: Optional[SkipReason] = None,
    ):
        """Update node status."""
        data = {"status": status.value}
        if skip_reason:
            data["skip_reason"] = skip_reason.value
        if status == NodeStatus.RUNNING:
            data["started_at"] = datetime.utcnow().isoformat()
        self.db.client.table("research_nodes").update(data).eq(
            "id", str(node_id)
        ).execute()

    async def _complete_node(
        self,
        node_id: UUID,
        saturation_score: float,
        findings_count: int,
        new_entities_count: int,
        execution_time_ms: int,
    ):
        """Mark node as completed with results."""
        self.db.client.table("research_nodes").update({
            "status": "completed",
            "saturation_score": saturation_score,
            "findings_count": findings_count,
            "new_entities_count": new_entities_count,
            "execution_time_ms": execution_time_ms,
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", str(node_id)).execute()

    async def _complete_tree(self, tree_id: UUID, duration: float, total_tokens: int):
        """Mark tree as completed."""
        self.db.client.table("research_trees").update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "total_tokens_used": total_tokens,
            "estimated_cost_usd": self._estimate_cost(total_tokens),
        }).eq("id", str(tree_id)).execute()

    async def _fail_tree(self, tree_id: UUID, error: str):
        """Mark tree as failed."""
        self.db.client.table("research_trees").update({
            "status": "failed",
            "metadata": {"error": error},
        }).eq("id", str(tree_id)).execute()

    async def _save_finding(self, node_id: UUID, finding: NodeFinding):
        """Save a finding for a node."""
        content_hash = hashlib.md5(finding.content.encode()).hexdigest()
        self.db.client.table("node_findings").insert({
            "id": str(uuid4()),
            "node_id": str(node_id),
            "content": finding.content,
            "finding_type": finding.finding_type,
            "confidence": finding.confidence,
            "evidence_strength": finding.evidence_strength,
            "sources": finding.sources,
            "entities_mentioned": finding.entities_mentioned,
            "temporal_context": finding.temporal_context,
            "content_hash": content_hash,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()

    async def _save_follow_up(
        self,
        node_id: UUID,
        follow_up: FollowUpQuestion,
        target_node_id: Optional[UUID],
    ):
        """Save a follow-up question record."""
        self.db.client.table("node_follow_ups").insert({
            "id": str(uuid4()),
            "source_node_id": str(node_id),
            "follow_up_query": follow_up.query,
            "follow_up_type": follow_up.follow_up_type.value,
            "priority_score": follow_up.priority_score,
            "reasoning": follow_up.reasoning,
            "target_node_id": str(target_node_id) if target_node_id else None,
            "status": "executed" if target_node_id else "pending",
            "created_at": datetime.utcnow().isoformat(),
        }).execute()

    async def _get_node_findings(self, node_id: UUID) -> List[Dict[str, Any]]:
        """Get findings for a node."""
        result = self.db.client.table("node_findings").select("*").eq(
            "node_id", str(node_id)
        ).execute()
        return result.data or []

    async def _get_related_claims(self, query: str, workspace_id: str) -> List[str]:
        """Get existing claims related to query topic."""
        # Search for related claims in knowledge base
        # This is a simplified version - could use semantic search
        words = query.lower().split()[:5]
        claims = []
        for word in words:
            if len(word) > 3:
                result = self.db.client.table("knowledge_claims").select("content").eq(
                    "workspace_id", workspace_id
                ).ilike("content", f"%{word}%").limit(5).execute()
                claims.extend([r["content"] for r in result.data or []])
        return list(set(claims))[:20]

    # ========================================
    # Helper Methods
    # ========================================

    def _count_entities(self, findings: List[NodeFinding]) -> int:
        """Count unique entities mentioned in findings."""
        entities = set()
        for f in findings:
            entities.update(f.entities_mentioned)
        return len(entities)

    def _estimate_cost(self, tokens: int) -> float:
        """Estimate cost in USD based on token usage."""
        # Rough estimate: $0.00025 per 1K input, $0.001 per 1K output
        # Assume 60% input, 40% output
        input_cost = (tokens * 0.6 / 1000) * 0.00025
        output_cost = (tokens * 0.4 / 1000) * 0.001
        return round(input_cost + output_cost, 4)

    async def _build_reasoning_chains(
        self,
        tree_id: UUID,
        nodes: List[Dict[str, Any]],
    ) -> List[ReasoningChain]:
        """Build reasoning chains from root to leaf nodes."""
        # Find leaf nodes (nodes with no children)
        node_ids = {n["id"] for n in nodes}
        parent_ids = {n.get("parent_node_id") for n in nodes if n.get("parent_node_id")}
        leaf_ids = node_ids - parent_ids

        chains = []
        for leaf_id in list(leaf_ids)[:10]:  # Limit to 10 chains
            chain = await self.get_reasoning_chain(tree_id, UUID(leaf_id))
            if chain:
                # Get the leaf node details
                leaf_node = next((n for n in nodes if n["id"] == leaf_id), None)
                chains.append(ReasoningChain(
                    chain_id=UUID(leaf_id),
                    queries=chain,
                    query_types=[n.get("query_type", "unknown") for n in nodes if n["query"] in chain],
                    depth=len(chain) - 1,
                ))

        return chains

    async def _generate_key_insights(
        self,
        root_query: str,
        findings: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate key insights from all findings."""
        if not findings:
            return []

        gemini = await self._get_gemini()
        if not gemini:
            return [f["content"] for f in findings[:5]]

        findings_text = "\n".join([
            f"- {f.get('content', '')}"
            for f in findings[:30]
        ])

        prompt = f"""Based on this research question and findings, identify the 3-5 most important insights.

Research Question: {root_query}

All Findings:
{findings_text}

Return JSON:
{{
    "insights": [
        "Key insight 1 - a significant conclusion or discovery",
        "Key insight 2 - another important finding",
        "..."
    ]
}}

Focus on insights that directly answer or illuminate the original question."""

        try:
            result, _ = await gemini.generate_json(prompt, temperature=0.3)
            return result.get("insights", [])[:5]
        except Exception as e:
            logger.warning(f"Key insight generation failed: {e}")
            return [f.get("content", "")[:200] for f in findings[:3]]
