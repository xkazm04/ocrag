"""Enhanced Test Harness with Perspective Agents and Relationship Building.

Extends the base test harness with:
- Query decomposition for complex queries
- Multi-perspective analysis using specialized agents
- Relationship graph building between findings
- Contradiction detection and gap analysis
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Import base harness components
try:
    from .test_harness import (
        ResearchTestHarness,
        TestResult,
        TestFinding,
        TestPerspective,
        TestSource,
        TokenStats,
    )
    from .gemini_client import GeminiResearchClient, SearchMode, TokenUsage
    from .inference_client import InferenceClient
    from .decomposer import QueryDecomposer, DecompositionResult, SubQuery, SubQueryResult, BatchExecutor
    from .perspectives import PerspectiveRunner, PerspectiveContext
    from .perspectives.runner import TopicPerspectives
    from .schemas.perspective import FindingPerspectives as FindingPerspectivesSchema
    from .relationship_builder import RelationshipBuilder, FindingInfo
    from .schemas.relationship import RelationshipGraph
    from .schemas.perspective import PerspectiveType
except ImportError:
    from test_harness import (
        ResearchTestHarness,
        TestResult,
        TestFinding,
        TestPerspective,
        TestSource,
        TokenStats,
    )
    from gemini_client import GeminiResearchClient, SearchMode, TokenUsage
    from inference_client import InferenceClient
    from decomposer import QueryDecomposer, DecompositionResult, SubQuery, SubQueryResult, BatchExecutor
    from perspectives import PerspectiveRunner, PerspectiveContext
    from perspectives.runner import TopicPerspectives
    from schemas.perspective import FindingPerspectives as FindingPerspectivesSchema
    from relationship_builder import RelationshipBuilder, FindingInfo
    from schemas.relationship import RelationshipGraph
    from schemas.perspective import PerspectiveType


@dataclass
class EnhancedTestResult(TestResult):
    """Extended test result with new analysis components."""

    # Query decomposition
    decomposition: Optional[DecompositionResult] = None
    sub_query_results: Dict[str, Any] = field(default_factory=dict)

    # Enhanced perspectives (from perspective agents)
    topic_perspectives: Optional[TopicPerspectives] = None

    # Finding-level perspectives
    finding_perspectives: List[FindingPerspectivesSchema] = field(default_factory=list)

    # Relationship graph
    relationship_graph: Optional[RelationshipGraph] = None

    # Token breakdown by phase
    tokens_search: int = 0
    tokens_extraction: int = 0
    tokens_perspectives: int = 0
    tokens_relationships: int = 0


class EnhancedResearchHarness(ResearchTestHarness):
    """Enhanced harness with all new features integrated."""

    # New perspective types
    ENHANCED_PERSPECTIVES = [
        PerspectiveType.HISTORICAL,
        PerspectiveType.FINANCIAL,
        PerspectiveType.JOURNALIST,
        PerspectiveType.CONSPIRATOR,
        PerspectiveType.NETWORK,
    ]

    def __init__(
        self,
        gemini_client: Optional[GeminiResearchClient] = None,
        inference_client: Optional[InferenceClient] = None,
    ):
        super().__init__(gemini_client)

        # Initialize inference client for perspective agents
        self.inference_client = inference_client or InferenceClient()

        # Initialize new components
        self.decomposer = QueryDecomposer(self.inference_client)
        self.batch_executor = BatchExecutor(self.inference_client)
        self.relationship_builder = RelationshipBuilder(self.inference_client)
        self.perspective_runner = PerspectiveRunner(
            client=self.inference_client,
            perspectives=self.ENHANCED_PERSPECTIVES,
        )

    async def run_enhanced_test(
        self,
        query: str,
        template_type: str = "investigative",
        max_searches: int = 5,
        granularity: str = "standard",
        run_decomposition: bool = True,
        execute_sub_queries: bool = True,
        run_perspectives: bool = True,
        run_finding_perspectives: bool = False,
        max_finding_perspectives: int = 15,
        run_relationships: bool = True,
    ) -> EnhancedTestResult:
        """Run enhanced research test with all new features."""

        result = EnhancedTestResult(
            query=query,
            template_type=template_type,
            started_at=datetime.now(),
        )

        try:
            print(f"\n{'='*70}")
            print(f"ENHANCED RESEARCH TEST")
            print(f"{'='*70}")
            print(f"Query: {query[:80]}...")

            # Step 0: Query Decomposition (optional)
            use_sub_queries = False
            if run_decomposition:
                print("\n--- Step 0: Query Decomposition ---")
                result.decomposition = await self.decomposer.analyze_and_decompose(query)
                print(f"  Needs decomposition: {result.decomposition.needs_decomposition}")
                print(f"  Strategy: {result.decomposition.strategy.value}")

                if result.decomposition.needs_decomposition:
                    print(f"  Sub-queries: {len(result.decomposition.sub_queries)}")
                    for sq in result.decomposition.sub_queries:
                        print(f"    - {sq.query[:60]}...")
                    use_sub_queries = execute_sub_queries

            # Branch: Execute sub-queries OR standard search
            if use_sub_queries and result.decomposition and result.decomposition.sub_queries:
                # Step 1-3 Alternative: Execute sub-queries
                print("\n--- Step 1-3: Execute Sub-Queries ---")
                sub_results = await self.batch_executor.execute_sub_queries(
                    sub_queries=result.decomposition.sub_queries,
                    search_func=self._run_single_search,
                    original_query=query,
                )
                result.sub_query_results = sub_results

                # Aggregate findings and sources from all sub-queries
                all_sources = []
                all_content = []
                all_findings = []

                for sq_id, sq_result in sub_results.items():
                    # Track sources
                    for s in sq_result.sources:
                        all_sources.append(s)

                    # Track content
                    if sq_result.content:
                        all_content.append(f"[{sq_id}: {sq_result.focus_theme or sq_result.query[:30]}]\n{sq_result.content}")

                    # Track findings with sub-query context
                    for f in sq_result.findings:
                        # Add sub-query context to finding
                        if hasattr(f, 'sub_query_id'):
                            f.sub_query_id = sq_id
                        all_findings.append(f)

                    # Aggregate tokens
                    result.tokens_search += sq_result.token_usage

                result.sources = all_sources
                result.synthesized_content = "\n\n---\n\n".join(all_content)
                result.findings = all_findings
                result.search_queries = [sq.query for sq in result.decomposition.sub_queries]

                print(f"  Total sources: {len(all_sources)}")
                print(f"  Total findings: {len(all_findings)}")

            else:
                # Standard path: Generate queries and search
                # Step 1: Generate search queries
                print("\n--- Step 1: Generate Search Queries ---")
                queries, token_usage, cost = await self._generate_queries(
                    query, max_searches, granularity
                )
                result.search_queries = queries
                result.add_tokens(token_usage, cost)
                result.tokens_search += token_usage.total_tokens if token_usage else 0
                print(f"  Generated {len(queries)} queries")

                # Step 2: Execute searches
                print("\n--- Step 2: Execute Web Searches ---")
                all_sources = []
                all_content = []

                for i, q in enumerate(queries):
                    print(f"  [{i+1}/{len(queries)}] {q[:50]}...")
                    search_response = await self.client.grounded_search(q)
                    result.add_tokens(
                        search_response.token_usage,
                        search_response.cost_usd or 0.0,
                    )
                    result.tokens_search += search_response.token_usage.total_tokens if search_response.token_usage else 0

                    for s in search_response.sources:
                        all_sources.append(TestSource(
                            url=s.url,
                            title=s.title,
                            domain=s.domain,
                            snippet=s.snippet,
                            source_type=s.source_type,
                        ))

                    if search_response.text:
                        all_content.append(search_response.text)

                result.sources = all_sources
                result.synthesized_content = "\n\n---\n\n".join(all_content)
                print(f"  Found {len(all_sources)} sources")

                # Step 3: Extract findings
                print("\n--- Step 3: Extract Findings ---")
                findings, token_usage, cost = await self._extract_findings(
                    query, result.sources, result.synthesized_content
                )
                result.findings = findings
                result.add_tokens(token_usage, cost)
                result.tokens_extraction += token_usage.total_tokens if token_usage else 0
                print(f"  Extracted {len(findings)} findings")

            # Build timeline
            result.timeline = self._build_timeline(result.findings)
            dated_events = len([e for e in result.timeline if e.extracted_date.date_start])
            print(f"  Built timeline: {len(result.timeline)} events ({dated_events} dated)")

            # Step 4: Enhanced Perspective Analysis (optional)
            if run_perspectives:
                print("\n--- Step 4: Enhanced Perspective Analysis ---")
                result.topic_perspectives = await self._run_enhanced_perspectives(
                    query, result
                )
                print(f"  Analyzed {len(result.topic_perspectives.analyses)} perspectives")

                # Also populate legacy perspectives for compatibility
                for ptype, analysis in result.topic_perspectives.analyses.items():
                    result.perspectives.append(TestPerspective(
                        perspective_type=ptype.value,
                        analysis_text=analysis.analysis,
                        key_insights=getattr(analysis, 'implications', []),
                        recommendations=[],
                        warnings=[],
                    ))

            # Step 4b: Finding-Level Perspective Analysis (optional)
            if run_finding_perspectives and result.findings:
                print("\n--- Step 4b: Finding-Level Perspectives ---")
                result.finding_perspectives = await self._run_finding_perspectives(
                    result.findings, query, max_finding_perspectives
                )
                print(f"  Analyzed {len(result.finding_perspectives)} findings with perspectives")

            # Step 5: Build Relationship Graph (optional)
            if run_relationships:
                print("\n--- Step 5: Build Relationship Graph ---")
                result.relationship_graph = await self._build_relationships(
                    query, result.findings
                )
                print(f"  Relationships: {len(result.relationship_graph.relationships)}")
                print(f"  Contradictions: {len(result.relationship_graph.contradictions)}")
                print(f"  Gaps: {len(result.relationship_graph.gaps)}")
                print(f"  Causal chains: {len(result.relationship_graph.causal_chains)}")

            result.completed_at = datetime.now()
            duration = (result.completed_at - result.started_at).seconds

            print(f"\n{'='*70}")
            print(f"Test completed in {duration}s")
            ts = result.token_stats
            print(f"Total tokens: {ts.total_tokens:,}")
            print(f"  Search: {result.tokens_search:,}")
            print(f"  Extraction: {result.tokens_extraction:,}")
            print(f"  Perspectives: {result.tokens_perspectives:,}")
            print(f"  Relationships: {result.tokens_relationships:,}")
            print(f"Total cost: ${result.total_cost_usd:.4f}")
            print(f"{'='*70}")

        except Exception as e:
            result.errors.append(str(e))
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()

        return result

    async def _run_enhanced_perspectives(
        self,
        query: str,
        result: EnhancedTestResult,
    ) -> TopicPerspectives:
        """Run enhanced perspective analysis using perspective agents."""

        # Build context for perspective agents
        context = PerspectiveContext(
            topic=query,
            topic_summary=result.synthesized_content[:2000],
            finding_summaries=[
                f.summary or f.content[:100]
                for f in result.findings[:15]
            ],
            actors=[
                f.content[:50]
                for f in result.findings
                if f.finding_type == "actor"
            ][:10],
            events=[
                f.summary or f.content[:50]
                for f in result.findings
                if f.finding_type == "event"
            ][:10],
            allow_training_data=True,
        )

        # Run all perspectives in parallel
        topic_perspectives = await self.perspective_runner.run_topic_analysis(
            context, parallel=True
        )

        return topic_perspectives

    async def _run_finding_perspectives(
        self,
        findings: List[TestFinding],
        query: str,
        max_findings: int = 15,
    ) -> List[FindingPerspectivesSchema]:
        """Run perspective analysis on individual findings.

        Args:
            findings: List of TestFinding objects
            query: Original query for context
            max_findings: Maximum number of findings to analyze

        Returns:
            List of FindingPerspectivesSchema with typed perspectives
        """
        # Build context
        context = PerspectiveContext(
            topic=query,
            topic_summary="",
            finding_summaries=[f.summary or f.content[:100] for f in findings[:15]],
            actors=[f.content[:50] for f in findings if f.finding_type == "actor"][:10],
            events=[f.summary or f.content[:50] for f in findings if f.finding_type == "event"][:10],
            allow_training_data=True,
        )

        # Convert findings to dict format for runner
        findings_dicts = [
            {
                "id": f"f{i+1}",
                "content": f.content,
                "type": f.finding_type,
                "summary": f.summary,
            }
            for i, f in enumerate(findings)
        ]

        # Run batch finding analysis
        return await self.perspective_runner.run_all_findings_analysis(
            findings=findings_dicts,
            context=context,
            max_findings=max_findings,
            batch_size=5,
            parallel=True,
        )

    async def _build_relationships(
        self,
        query: str,
        findings: List[TestFinding],
    ) -> RelationshipGraph:
        """Build relationship graph from findings."""

        # Convert TestFinding to FindingInfo
        finding_infos = []
        for i, f in enumerate(findings):
            finding_infos.append(FindingInfo(
                id=f"f{i+1}",
                content=f.content,
                finding_type=f.finding_type,
                summary=f.summary,
                date_text=f.date_text,
                actors=[],  # Could extract from finding
            ))

        return await self.relationship_builder.build_graph(finding_infos, query)

    async def _run_single_search(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SubQueryResult:
        """Execute a single search query for sub-query execution.

        Args:
            query: The search query to execute
            context: Optional context including sub-query metadata

        Returns:
            SubQueryResult with findings and sources
        """
        context = context or {}
        sub_query_id = context.get("sub_query_id", "sq_0")

        result = SubQueryResult(
            sub_query_id=sub_query_id,
            query=query,
            composition_role=context.get("composition_role", "equal"),
            focus_theme=context.get("focus_theme"),
        )

        try:
            # Execute grounded search
            search_response = await self.client.grounded_search(query)

            # Collect sources
            sources = []
            for s in search_response.sources:
                sources.append(TestSource(
                    url=s.url,
                    title=s.title,
                    domain=s.domain,
                    snippet=s.snippet,
                    source_type=s.source_type,
                ))
            result.sources = sources
            result.content = search_response.text or ""

            # Track token usage
            if search_response.token_usage:
                result.token_usage = search_response.token_usage.total_tokens
                result.cost_usd = search_response.cost_usd or 0.0

            # Extract findings from this sub-query's results
            if search_response.text:
                findings, token_usage, cost = await self._extract_findings(
                    query, sources, search_response.text
                )
                result.findings = findings
                if token_usage:
                    result.token_usage += token_usage.total_tokens
                    result.cost_usd += cost

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result


async def run_enhanced_test(query: str, **kwargs) -> EnhancedTestResult:
    """Convenience function to run enhanced test."""
    harness = EnhancedResearchHarness()
    return await harness.run_enhanced_test(query, **kwargs)
