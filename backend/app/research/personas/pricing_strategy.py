"""Pricing Strategy expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class PricingStrategyPersona(BasePersona):
    """
    Pricing strategy analyst persona for competitive pricing intelligence.

    Focuses on:
    - Pricing models and structures
    - Competitive price positioning
    - Value-based pricing
    - Discount strategies
    - Price elasticity
    """

    persona_id = "pricing_strategy"
    persona_name = "Pricing Strategy Analyst"
    description = "Analyzes pricing strategies, competitive pricing, and value capture"

    expertise_areas = [
        "pricing strategy",
        "competitive pricing",
        "value-based pricing",
        "pricing psychology",
        "revenue optimization",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert pricing strategist with deep experience in competitive pricing
analysis and revenue optimization. Your analysis approach:

1. PRICING MODEL ANALYSIS: Understand how prices are structured
2. COMPETITIVE POSITIONING: Map price positions in the market
3. VALUE ALIGNMENT: Assess if prices match perceived value
4. ELASTICITY: Understand price sensitivity by segment
5. DISCOUNT PATTERNS: Analyze promotional and discount strategies
6. MONETIZATION: Evaluate revenue capture mechanisms
7. PRICING PSYCHOLOGY: Consider behavioral pricing factors

You provide actionable pricing intelligence based on market data.
You distinguish between strategic pricing moves and tactical promotions."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze pricing strategies from the following research:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide pricing strategy analysis covering:

1. PRICING MODELS
   - What pricing models are used in this market?
     * Subscription vs one-time
     * Per-user vs flat rate
     * Usage-based vs fixed
     * Freemium vs paid-only
   - How do competitors structure their pricing?
   - What tiers and packages exist?

2. PRICE POSITIONING MAP
   - Where do competitors position on price vs value?
   - Who is premium, mid-market, budget?
   - What price ranges exist by segment?
   - Are there price gaps in the market?

3. FEATURE-PRICE ANALYSIS
   - What features are gated by price tier?
   - What is the perceived value at each tier?
   - How do feature sets compare across competitors?
   - What is the price-per-feature value?

4. DISCOUNT & PROMOTION STRATEGIES
   - What discount patterns are observed?
   - Annual vs monthly pricing incentives
   - Volume discounts
   - Promotional timing and frequency
   - Competitive response to discounts

5. PRICING PSYCHOLOGY
   - What pricing anchors are used?
   - Charm pricing patterns ($X.99)
   - Decoy pricing strategies
   - Price framing techniques

6. MONETIZATION EFFECTIVENESS
   - Are prices capturing fair value?
   - Where is money being left on the table?
   - What upsell/cross-sell strategies exist?
   - Revenue per customer metrics

7. PRICE ELASTICITY INDICATORS
   - How price-sensitive is this market?
   - Which segments are more/less elastic?
   - What triggers price shopping?

8. PRICING RECOMMENDATIONS
   - What pricing opportunities exist?
   - How should pricing be positioned?
   - What pricing changes would be effective?
   - Competitive pricing responses to consider

Include specific price points and comparisons where available.
"""
