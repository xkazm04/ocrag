"""Dynamic time scope analysis for research queries.

Uses LLM to determine optimal time scope based on query characteristics,
domain velocity, and user intent signals.
"""

import logging
from datetime import date
from enum import Enum
from typing import Optional, List, Tuple

from pydantic import BaseModel, Field

from ..lib.clients import InferenceClient, get_inference_client

logger = logging.getLogger(__name__)


class ScopeType(str, Enum):
    """Type of time scope for a query."""
    CURRENT = "current"           # Last 1-2 years, recent developments
    RECENT = "recent"             # Last 3-5 years
    HISTORICAL = "historical"     # Comprehensive historical view
    SPECIFIC = "specific"         # Specific date range mentioned
    COMPREHENSIVE = "comprehensive"  # Full timeline needed


class DomainVelocity(str, Enum):
    """How fast information changes in a domain."""
    FAST = "fast"       # Tech, markets, politics - changes rapidly
    MEDIUM = "medium"   # Business, social trends
    SLOW = "slow"       # History, culture, science fundamentals


class TimeScopeDecision(BaseModel):
    """Result of time scope analysis."""
    scope_type: ScopeType
    domain_velocity: DomainVelocity
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)

    # Decomposition hints
    needs_temporal_split: bool = False
    suggested_periods: List[Tuple[int, int]] = Field(default_factory=list)

    # Search guidance
    focus_on_recent: bool = False
    include_historical_context: bool = False

    @property
    def year_span(self) -> int:
        """Calculate the span in years."""
        if self.start_year and self.end_year:
            return self.end_year - self.start_year
        return 0


class TimeScopeAnalyzer:
    """Dynamically determines appropriate time scope for research queries."""

    def __init__(self, inference_client=None):
        """
        Initialize analyzer.

        Args:
            inference_client: InferenceClient instance (will create if None)
        """
        self.client = inference_client

    async def _get_client(self):
        """Lazy load inference client."""
        if self.client is None:
            try:
                self.client = InferenceClient()
            except (ImportError, ValueError) as e:
                logger.warning("Could not create InferenceClient: %s", e)
                self.client = None
        return self.client

    async def analyze(self, query: str) -> TimeScopeDecision:
        """
        Analyze query to determine optimal time scope.

        Args:
            query: The research query

        Returns:
            TimeScopeDecision with scope type, date range, and guidance
        """
        client = await self._get_client()
        today = date.today()

        prompt = f"""Analyze this research query to determine the optimal time scope for investigation.

QUERY: "{query}"
TODAY'S DATE: {today.isoformat()} (Year: {today.year})

ANALYSIS FRAMEWORK:

1. EXPLICIT TIME REFERENCES
   - Does the query mention specific years, dates, or periods?
   - Are there implicit time markers ("recent", "current", "history of")?

2. DOMAIN VELOCITY (how fast this topic evolves)
   - FAST: Technology, cryptocurrency, politics, breaking news (1-2 years relevant)
   - MEDIUM: Business trends, social movements, regulations (3-5 years relevant)
   - SLOW: Historical events, scientific principles, cultural analysis (10+ years)

3. USER INTENT SIGNALS
   - "current/latest/recent/now" → Focus on last 1-2 years
   - "history of/evolution/timeline/origins" → Comprehensive scope
   - "what happened in [specific time]" → Specific period
   - "why did X happen" → May need historical context
   - "future/prediction/forecast" → Recent + projections

4. QUERY TYPE
   - Breaking news investigation → Very recent (months)
   - Background research → Broader scope needed
   - Fact-checking specific claims → Depends on claim date
   - Trend analysis → Multiple years for patterns
   - Causal analysis ("why") → Often needs historical context

Return JSON:
{{
    "scope_type": "current" | "recent" | "historical" | "specific" | "comprehensive",
    "domain_velocity": "fast" | "medium" | "slow",
    "start_year": {today.year - 10} to {today.year} or null,
    "end_year": {today.year} or null,
    "reasoning": "Brief explanation of scope decision",
    "confidence": 0.0 to 1.0,
    "needs_temporal_split": true/false,
    "suggested_periods": [[start1, end1], [start2, end2]] or [],
    "focus_on_recent": true/false,
    "include_historical_context": true/false
}}

EXAMPLES:

Query: "What's the current situation with AI regulations in EU?"
→ scope_type: "current", domain_velocity: "fast", start_year: {today.year - 1}, end_year: {today.year}
   (Fast-moving policy area, user wants current state)

Query: "History of the Russia-Ukraine conflict"
→ scope_type: "comprehensive", domain_velocity: "medium", start_year: 2014, end_year: {today.year}
   needs_temporal_split: true, suggested_periods: [[2014, 2021], [2022, {today.year}]]
   (Historical query, major phase change in 2022)

Query: "Bitcoin price in March 2023"
→ scope_type: "specific", domain_velocity: "fast", start_year: 2023, end_year: 2023
   (Specific time period mentioned)

Query: "Why did the 2008 financial crisis happen?"
→ scope_type: "historical", domain_velocity: "medium", start_year: 2006, end_year: 2010
   include_historical_context: true
   (Causal query about past event, needs context before and after)

Be precise about date ranges - don't default to overly broad scopes."""

        result, error = await client.generate_json(
            prompt,
            system_prompt="You are a research analyst specializing in temporal scoping of investigations. Be precise about time ranges.",
            temperature=0.2,
        )

        if error or not result:
            # Fallback to reasonable defaults
            return TimeScopeDecision(
                scope_type=ScopeType.RECENT,
                domain_velocity=DomainVelocity.MEDIUM,
                start_year=today.year - 3,
                end_year=today.year,
                reasoning="Unable to analyze query - using default 3-year scope",
                confidence=0.3,
            )

        # Parse result
        try:
            scope_type = ScopeType(result.get("scope_type", "recent"))
        except ValueError:
            scope_type = ScopeType.RECENT

        try:
            domain_velocity = DomainVelocity(result.get("domain_velocity", "medium"))
        except ValueError:
            domain_velocity = DomainVelocity.MEDIUM

        # Parse suggested periods
        periods = []
        for period in result.get("suggested_periods", []):
            if isinstance(period, (list, tuple)) and len(period) == 2:
                try:
                    periods.append((int(period[0]), int(period[1])))
                except (ValueError, TypeError):
                    pass

        return TimeScopeDecision(
            scope_type=scope_type,
            domain_velocity=domain_velocity,
            start_year=result.get("start_year"),
            end_year=result.get("end_year"),
            reasoning=result.get("reasoning", ""),
            confidence=float(result.get("confidence", 0.7)),
            needs_temporal_split=result.get("needs_temporal_split", False),
            suggested_periods=periods,
            focus_on_recent=result.get("focus_on_recent", False),
            include_historical_context=result.get("include_historical_context", False),
        )

    def get_search_date_filter(self, decision: TimeScopeDecision) -> Optional[str]:
        """
        Generate a date filter string for search APIs.

        Returns:
            String like "after:2022-01-01 before:2024-12-31" or None
        """
        if not decision.start_year:
            return None

        parts = []
        if decision.start_year:
            parts.append(f"after:{decision.start_year}-01-01")
        if decision.end_year:
            parts.append(f"before:{decision.end_year}-12-31")

        return " ".join(parts) if parts else None

    def should_include_in_query(self, decision: TimeScopeDecision) -> bool:
        """
        Determine if date constraints should be added to the search query.

        Returns:
            True if the scope is narrow enough to benefit from date filtering
        """
        # Only add date constraints for specific/current scopes
        if decision.scope_type in (ScopeType.SPECIFIC, ScopeType.CURRENT):
            return True

        # Or if year span is small
        if decision.year_span > 0 and decision.year_span <= 3:
            return True

        return False


# Convenience function
async def analyze_time_scope(query: str, client=None) -> TimeScopeDecision:
    """Analyze a query's time scope."""
    analyzer = TimeScopeAnalyzer(client)
    return await analyzer.analyze(query)
