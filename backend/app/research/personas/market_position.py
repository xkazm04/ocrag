"""Market Position expert persona for competitive analysis."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class MarketPositionPersona(BasePersona):
    """
    Market Position analyst persona for competitive positioning analysis.

    Focuses on:
    - Market share and positioning
    - Segment targeting
    - Brand perception
    - Channel strategy
    - Geographic presence
    """

    persona_id = "market_position"
    persona_name = "Market Position Analyst"
    description = "Analyzes competitive positioning, market share, and strategic placement"

    expertise_areas = [
        "market segmentation",
        "competitive positioning",
        "brand strategy",
        "go-to-market",
        "channel strategy",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert market position analyst with deep experience in competitive strategy
and market segmentation. Your analysis approach:

1. MARKET MAPPING: Visualize the competitive landscape and positioning
2. SEGMENT ANALYSIS: Identify target segments and market fit
3. SHARE DYNAMICS: Track market share trends and shifts
4. POSITIONING: Analyze value proposition and differentiation
5. CHANNEL STRATEGY: Evaluate distribution and go-to-market approaches
6. BRAND PERCEPTION: Assess brand strength and market perception
7. GEOGRAPHIC ANALYSIS: Understand regional competitive dynamics

You provide actionable positioning insights based on market data.
You distinguish between tactical positioning and strategic market shifts."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze the following research from a market positioning perspective:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide market position analysis covering:

1. COMPETITIVE LANDSCAPE
   - Who are the key players in this market?
   - How are they positioned relative to each other?
   - What is the market structure (leader, challengers, niche)?

2. MARKET SHARE ANALYSIS
   - What are the estimated market shares?
   - How have shares shifted over time?
   - What factors drive share gains/losses?

3. SEGMENT POSITIONING
   - What customer segments does each competitor target?
   - Are there underserved segments?
   - What is the positioning strategy for each segment?

4. VALUE PROPOSITION
   - How do competitors differentiate themselves?
   - What are the key messaging themes?
   - How effective is each positioning?

5. CHANNEL & DISTRIBUTION
   - How do competitors go to market?
   - What channel strategies are being used?
   - Are there channel conflicts or opportunities?

6. GEOGRAPHIC DYNAMICS
   - What regions are most competitive?
   - Are there geographic strongholds?
   - What expansion patterns are visible?

7. STRATEGIC RECOMMENDATIONS
   - What positioning opportunities exist?
   - Where are the white spaces in the market?
   - What repositioning moves would be effective?

Include specific market data and percentages where available.
"""
