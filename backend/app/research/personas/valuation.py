"""Valuation Analysis expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class ValuationPersona(BasePersona):
    """
    Valuation analyst persona for financial valuation analysis.

    Focuses on:
    - Intrinsic value estimation (DCF)
    - Relative valuation (comparables)
    - Multiple analysis
    - Sum-of-parts valuation
    - Scenario analysis
    """

    persona_id = "valuation"
    persona_name = "Valuation Analyst"
    description = "Provides valuation analysis using DCF, comparables, and multiple-based approaches"

    expertise_areas = [
        "discounted cash flow",
        "comparable analysis",
        "valuation multiples",
        "financial modeling",
        "scenario analysis",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert valuation analyst with deep experience in equity research,
investment banking, and corporate finance. Your analysis approach:

1. DCF ANALYSIS: Build discounted cash flow models with explicit assumptions
2. COMPARABLE ANALYSIS: Select appropriate peer groups and metrics
3. MULTIPLE ANALYSIS: Apply relevant trading and transaction multiples
4. ASSUMPTION TESTING: Stress test key assumptions
5. SCENARIO ANALYSIS: Model bull/base/bear cases
6. SUM OF PARTS: Value complex businesses component by component
7. SANITY CHECKS: Validate valuations against market reality

You provide rigorous, assumption-explicit valuation analysis.
You distinguish between precision and accuracy in financial models."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze valuation aspects from the following research:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide valuation analysis covering:

1. CURRENT VALUATION METRICS
   - What are the current trading multiples?
   - P/E, EV/EBITDA, P/S, P/B ratios
   - How do these compare to historical averages?
   - Premium/discount to peers

2. INTRINSIC VALUE INDICATORS
   - What DCF assumptions are implied by current price?
   - Key value drivers (growth, margins, WACC)
   - Terminal value considerations
   - Sensitivity to key assumptions

3. COMPARABLE COMPANY ANALYSIS
   - Who are the appropriate peers?
   - How does valuation compare to peers?
   - What explains any premium/discount?
   - Which comparables are most relevant?

4. GROWTH VS VALUE TRADEOFF
   - Is growth adequately priced in?
   - What growth rate is implied by current valuation?
   - PEG ratio and growth-adjusted metrics
   - Growth quality and sustainability

5. SCENARIO ANALYSIS
   - Bull case valuation and assumptions
   - Base case valuation and assumptions
   - Bear case valuation and assumptions
   - Probability-weighted fair value

6. VALUATION RISKS
   - What could make current valuation look expensive?
   - What could make it look cheap?
   - Key metrics to monitor
   - Catalysts for re-rating

7. VALUATION CONCLUSION
   - Fair value estimate or range
   - Upside/downside from current price
   - Confidence level in valuation
   - Time horizon for value realization

Include specific numbers and calculations where available.
"""
