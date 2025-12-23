"""Query Decomposition Module.

Analyzes complex or long-range queries and decomposes them into
smaller, focused sub-queries for batched research.

Uses OpenRouter Gemini 3 Flash Preview for intelligent decomposition.
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple, Callable, Awaitable

# Handle both relative and direct imports
try:
    from .inference_client import InferenceClient
    from .date_utils import DateExtractor, ExtractedDate, DatePrecision
except ImportError:
    from inference_client import InferenceClient
    from date_utils import DateExtractor, ExtractedDate, DatePrecision


class DecompositionStrategy(Enum):
    """Strategy for decomposing queries."""
    NONE = "none"  # No decomposition needed
    TEMPORAL = "temporal"  # Split by time periods
    THEMATIC = "thematic"  # Split by themes/aspects
    ACTOR = "actor"  # Split by key actors
    HYBRID = "hybrid"  # Combination of strategies


@dataclass
class SubQuery:
    """A decomposed sub-query for batched research."""

    id: str
    query: str
    original_query: str

    # Decomposition metadata
    strategy: DecompositionStrategy
    batch_order: int  # Order in which to execute (for dependencies)

    # Temporal bounds
    date_start: Optional[date] = None
    date_end: Optional[date] = None

    # Focus areas
    focus_theme: Optional[str] = None
    focus_actors: List[str] = field(default_factory=list)

    # Composition hints
    composition_role: str = "equal"  # 'equal', 'background', 'primary', 'synthesis'
    depends_on: List[str] = field(default_factory=list)  # IDs of prerequisite queries


@dataclass
class DecompositionResult:
    """Result of query decomposition analysis."""

    original_query: str
    needs_decomposition: bool
    strategy: DecompositionStrategy

    # Sub-queries (empty if no decomposition needed)
    sub_queries: List[SubQuery] = field(default_factory=list)

    # Analysis metadata
    detected_date_range: Optional[Tuple[date, date]] = None
    date_range_years: int = 0
    detected_themes: List[str] = field(default_factory=list)
    detected_actors: List[str] = field(default_factory=list)

    # Reasoning
    decomposition_reasoning: str = ""

    @property
    def query_count(self) -> int:
        return len(self.sub_queries) if self.sub_queries else 1


@dataclass
class SubQueryResult:
    """Result from executing a single sub-query."""

    sub_query_id: str
    query: str

    # Content from search
    findings: List[Any] = field(default_factory=list)
    sources: List[Any] = field(default_factory=list)
    content: str = ""

    # Composition metadata
    composition_role: str = "equal"
    focus_theme: Optional[str] = None

    # Metrics
    token_usage: int = 0
    cost_usd: float = 0.0

    # Status
    success: bool = True
    error: Optional[str] = None


class QueryDecomposer:
    """Decomposes complex queries into manageable sub-queries."""

    # Threshold for year range that triggers temporal decomposition
    YEAR_RANGE_THRESHOLD = 5

    # Maximum recommended sub-queries
    MAX_SUB_QUERIES = 6

    def __init__(self, inference_client: Optional[InferenceClient] = None):
        self.client = inference_client or InferenceClient()
        self.date_extractor = DateExtractor()

    async def analyze_and_decompose(
        self,
        query: str,
        force_decomposition: bool = False,
    ) -> DecompositionResult:
        """Analyze query and decompose if beneficial.

        Args:
            query: The user's research query
            force_decomposition: Force decomposition even if not strictly needed

        Returns:
            DecompositionResult with sub-queries if decomposition is beneficial
        """
        # Step 1: Quick analysis for date range
        dates = self.date_extractor.extract_all(query)
        date_range = self._detect_date_range(dates)
        year_span = self._calculate_year_span(date_range)

        # Step 2: Use LLM to analyze query complexity and decompose
        analysis = await self._llm_analyze_query(query, date_range, year_span)

        # Build result
        result = DecompositionResult(
            original_query=query,
            needs_decomposition=analysis.get("needs_decomposition", False) or force_decomposition,
            strategy=DecompositionStrategy(analysis.get("strategy", "none")),
            detected_date_range=date_range,
            date_range_years=year_span,
            detected_themes=analysis.get("themes", []),
            detected_actors=analysis.get("actors", []),
            decomposition_reasoning=analysis.get("reasoning", ""),
        )

        # Generate sub-queries if decomposition is needed
        if result.needs_decomposition:
            sub_queries = await self._generate_sub_queries(
                query, result.strategy, analysis
            )
            result.sub_queries = sub_queries

        return result

    def _detect_date_range(
        self, dates: List[ExtractedDate]
    ) -> Optional[Tuple[date, date]]:
        """Detect the date range from extracted dates."""
        if not dates:
            return None

        start_dates = [d.date_start for d in dates if d.date_start]
        end_dates = [d.date_end or d.date_start for d in dates if d.date_start]

        if not start_dates:
            return None

        return (min(start_dates), max(end_dates))

    def _calculate_year_span(
        self, date_range: Optional[Tuple[date, date]]
    ) -> int:
        """Calculate the span in years."""
        if not date_range:
            return 0
        return date_range[1].year - date_range[0].year

    async def _llm_analyze_query(
        self,
        query: str,
        date_range: Optional[Tuple[date, date]],
        year_span: int,
    ) -> Dict[str, Any]:
        """Use LLM to analyze query complexity."""

        date_context = ""
        if date_range:
            date_context = f"""
Detected date range: {date_range[0].year} to {date_range[1].year} ({year_span} years)
"""

        prompt = f"""Analyze this research query for complexity and decomposition needs.

QUERY: "{query}"
{date_context}

ANALYSIS CRITERIA:
1. Date Range: Queries spanning >5 years often benefit from temporal decomposition
2. Multiple Themes: Queries asking about many distinct aspects benefit from thematic decomposition
3. Multiple Actors: Queries about many distinct parties benefit from actor-based decomposition
4. Complexity: Very broad questions may need hybrid decomposition

Respond in JSON format:
{{
    "needs_decomposition": true/false,
    "strategy": "none" | "temporal" | "thematic" | "actor" | "hybrid",
    "reasoning": "Brief explanation of why decomposition is/isn't needed",
    "themes": ["theme1", "theme2", ...],  // Major themes in the query
    "actors": ["actor1", "actor2", ...],  // Key actors/entities mentioned
    "suggested_splits": [  // Only if needs_decomposition is true
        {{
            "focus": "description of sub-query focus",
            "time_period": "optional: specific time period",
            "priority": 1-5
        }}
    ]
}}

Be conservative - only recommend decomposition if it would genuinely improve research quality."""

        result, _ = await self.client.generate_json(
            prompt,
            system_prompt="You are a research analyst specializing in query optimization.",
            temperature=0.2,
        )

        return result or {
            "needs_decomposition": False,
            "strategy": "none",
            "reasoning": "Unable to analyze query",
            "themes": [],
            "actors": [],
        }

    async def _generate_sub_queries(
        self,
        original_query: str,
        strategy: DecompositionStrategy,
        analysis: Dict[str, Any],
    ) -> List[SubQuery]:
        """Generate specific sub-queries based on strategy."""

        suggested_splits = analysis.get("suggested_splits", [])
        themes = analysis.get("themes", [])
        actors = analysis.get("actors", [])

        prompt = f"""Generate specific sub-queries for batched research.

ORIGINAL QUERY: "{original_query}"

DECOMPOSITION STRATEGY: {strategy.value}
DETECTED THEMES: {themes}
DETECTED ACTORS: {actors}

SUGGESTED SPLITS:
{suggested_splits}

Generate {min(len(suggested_splits), self.MAX_SUB_QUERIES)} focused sub-queries.

For each sub-query, provide:
1. A clear, specific query that can be researched independently
2. The focus theme or time period
3. Which actors are relevant
4. Execution order (queries providing context should run first)
5. Composition role: 'background' (context), 'primary' (main content), or 'synthesis' (connecting findings)

Respond in JSON:
{{
    "sub_queries": [
        {{
            "query": "Specific research question",
            "focus_theme": "Theme being explored",
            "focus_actors": ["Actor1", "Actor2"],
            "time_period_start": "YYYY-MM-DD or null",
            "time_period_end": "YYYY-MM-DD or null",
            "batch_order": 1,
            "composition_role": "background" | "primary" | "synthesis",
            "depends_on_indices": []  // Indices of queries this depends on
        }}
    ]
}}"""

        result, _ = await self.client.generate_json(
            prompt,
            system_prompt="You are a research analyst creating focused sub-queries.",
            temperature=0.3,
        )

        sub_queries = []
        if result and "sub_queries" in result:
            for i, sq in enumerate(result["sub_queries"]):
                sub_query = SubQuery(
                    id=f"sq_{i+1}",
                    query=sq.get("query", ""),
                    original_query=original_query,
                    strategy=strategy,
                    batch_order=sq.get("batch_order", i + 1),
                    focus_theme=sq.get("focus_theme"),
                    focus_actors=sq.get("focus_actors", []),
                    composition_role=sq.get("composition_role", "equal"),
                )

                # Parse time periods
                if sq.get("time_period_start"):
                    try:
                        sub_query.date_start = date.fromisoformat(sq["time_period_start"])
                    except ValueError:
                        pass

                if sq.get("time_period_end"):
                    try:
                        sub_query.date_end = date.fromisoformat(sq["time_period_end"])
                    except ValueError:
                        pass

                # Set dependencies
                deps = sq.get("depends_on_indices", [])
                sub_query.depends_on = [f"sq_{idx+1}" for idx in deps]

                sub_queries.append(sub_query)

        # Sort by batch order
        sub_queries.sort(key=lambda x: x.batch_order)

        return sub_queries


class BatchExecutor:
    """Executes batched sub-queries and composes results."""

    def __init__(self, inference_client: Optional[InferenceClient] = None):
        self.client = inference_client or InferenceClient()

    def get_execution_order(
        self, sub_queries: List[SubQuery]
    ) -> List[List[SubQuery]]:
        """Get execution batches respecting dependencies.

        Returns list of batches that can be executed in parallel.
        """
        executed: set = set()
        batches: List[List[SubQuery]] = []
        remaining = sub_queries.copy()

        while remaining:
            # Find queries whose dependencies are all satisfied
            batch = []
            for sq in remaining:
                if all(dep in executed for dep in sq.depends_on):
                    batch.append(sq)

            if not batch:
                # Circular dependency or error - just add remaining
                batches.append(remaining)
                break

            batches.append(batch)
            for sq in batch:
                executed.add(sq.id)
                remaining.remove(sq)

        return batches

    async def execute_sub_queries(
        self,
        sub_queries: List[SubQuery],
        search_func: Callable[[str, Optional[Dict[str, Any]]], Awaitable[SubQueryResult]],
        original_query: str,
    ) -> Dict[str, SubQueryResult]:
        """Execute sub-queries in dependency order.

        Args:
            sub_queries: List of SubQuery objects to execute
            search_func: Async function that takes (query, context) and returns SubQueryResult
            original_query: The original query for context

        Returns:
            Dict mapping sub-query IDs to their results
        """
        batches = self.get_execution_order(sub_queries)
        results: Dict[str, SubQueryResult] = {}

        print(f"  Executing {len(sub_queries)} sub-queries in {len(batches)} batches")

        for batch_idx, batch in enumerate(batches):
            print(f"    Batch {batch_idx + 1}/{len(batches)}: {len(batch)} queries")

            # Build context from previous results
            context = {
                "original_query": original_query,
                "previous_results": {
                    sq_id: {
                        "query": res.query,
                        "finding_count": len(res.findings),
                        "summary": res.content[:500] if res.content else "",
                    }
                    for sq_id, res in results.items()
                },
            }

            # Execute batch in parallel
            tasks = [
                self._execute_single(sq, search_func, context)
                for sq in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for sq, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results[sq.id] = SubQueryResult(
                        sub_query_id=sq.id,
                        query=sq.query,
                        composition_role=sq.composition_role,
                        focus_theme=sq.focus_theme,
                        success=False,
                        error=str(result),
                    )
                    print(f"      [{sq.id}] ERROR: {result}")
                else:
                    results[sq.id] = result
                    print(f"      [{sq.id}] {len(result.findings)} findings, {len(result.sources)} sources")

        return results

    async def _execute_single(
        self,
        sub_query: SubQuery,
        search_func: Callable[[str, Optional[Dict[str, Any]]], Awaitable[SubQueryResult]],
        context: Dict[str, Any],
    ) -> SubQueryResult:
        """Execute a single sub-query."""
        # Add sub-query metadata to context
        sq_context = {
            **context,
            "sub_query_id": sub_query.id,
            "focus_theme": sub_query.focus_theme,
            "focus_actors": sub_query.focus_actors,
            "composition_role": sub_query.composition_role,
            "date_start": sub_query.date_start.isoformat() if sub_query.date_start else None,
            "date_end": sub_query.date_end.isoformat() if sub_query.date_end else None,
        }

        result = await search_func(sub_query.query, sq_context)

        # Ensure result has correct metadata
        result.sub_query_id = sub_query.id
        result.query = sub_query.query
        result.composition_role = sub_query.composition_role
        result.focus_theme = sub_query.focus_theme

        return result

    async def compose_synthesis(
        self,
        original_query: str,
        sub_results: Dict[str, SubQueryResult],
    ) -> str:
        """Compose final synthesis from sub-query results.

        Args:
            original_query: The original user query
            sub_results: Dict mapping sub-query IDs to their SubQueryResults

        Returns:
            Synthesized answer combining all sub-query findings
        """
        # Build context from sub-results
        context_parts = []
        for sq_id, result in sorted(sub_results.items()):
            role_label = f" ({result.composition_role})" if result.composition_role != "equal" else ""
            theme_label = f" - {result.focus_theme}" if result.focus_theme else ""

            findings_summary = "\n".join([
                f"- {f.summary if hasattr(f, 'summary') and f.summary else str(f)[:100]}"
                for f in result.findings[:10]
            ]) if result.findings else "No findings"

            context_parts.append(
                f"### {sq_id}{role_label}{theme_label}\n"
                f"Query: {result.query}\n"
                f"Findings ({len(result.findings)}):\n{findings_summary}"
            )

        context = "\n\n".join(context_parts)

        prompt = f"""Synthesize the following research findings into a comprehensive answer.

ORIGINAL QUESTION: {original_query}

RESEARCH FINDINGS BY SUB-QUERY:
{context}

Create a unified, coherent synthesis that:
1. Integrates findings from all sub-queries
2. Identifies connections and patterns across findings
3. Notes any contradictions or tensions between findings
4. Presents a complete answer to the original question
5. Gives appropriate weight based on composition roles (background, primary, synthesis)

Provide the synthesis in clear, well-organized prose."""

        response = await self.client.generate(
            prompt,
            system_prompt="You are a research analyst synthesizing findings into comprehensive reports.",
            temperature=0.3,
            max_tokens=2000,
        )

        return response.text


# Convenience functions
async def decompose_query(
    query: str,
    client: Optional[InferenceClient] = None,
) -> DecompositionResult:
    """Decompose a query if beneficial."""
    decomposer = QueryDecomposer(client)
    return await decomposer.analyze_and_decompose(query)


async def should_decompose(query: str) -> bool:
    """Quick check if query should be decomposed."""
    result = await decompose_query(query)
    return result.needs_decomposition
