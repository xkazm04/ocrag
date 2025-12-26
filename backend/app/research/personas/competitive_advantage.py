"""Competitive Advantage expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class CompetitiveAdvantagePersona(BasePersona):
    """
    Competitive advantage analyst persona for moat and differentiation analysis.

    Focuses on:
    - Sustainable competitive advantages (moats)
    - Differentiation strategies
    - Barriers to entry
    - Core competencies
    - Value chain positioning
    """

    persona_id = "competitive_advantage"
    persona_name = "Competitive Advantage Analyst"
    description = "Analyzes sustainable competitive advantages, moats, and differentiation"

    expertise_areas = [
        "competitive moats",
        "differentiation strategy",
        "barriers to entry",
        "core competencies",
        "value chain analysis",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert competitive strategy analyst specializing in identifying and
evaluating sustainable competitive advantages. Your analysis approach:

1. MOAT IDENTIFICATION: Find sources of sustainable competitive advantage
2. MOAT DURABILITY: Assess how defensible advantages are over time
3. DIFFERENTIATION: Understand unique value proposition drivers
4. BARRIERS: Evaluate entry barriers and switching costs
5. CORE COMPETENCIES: Identify unique organizational capabilities
6. VALUE CHAIN: Analyze where value is created and captured
7. EROSION RISKS: Identify threats to existing advantages

You apply Porter's frameworks, resource-based view, and modern competitive strategy.
You distinguish between temporary advantages and sustainable moats."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze competitive advantages from the following research:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide competitive advantage analysis covering:

1. MOAT ANALYSIS
   - What sustainable competitive advantages exist?
   - Types of moats identified:
     * Network effects
     * Economies of scale
     * Brand/reputation
     * Switching costs
     * Patents/IP
     * Regulatory advantages
     * Cost advantages
   - How wide and deep is each moat?

2. MOAT DURABILITY
   - How sustainable are identified advantages?
   - What could erode these advantages?
   - Are moats widening or narrowing over time?
   - Time horizon for advantage sustainability

3. DIFFERENTIATION STRATEGY
   - What makes offerings unique?
   - Is differentiation based on features, service, brand, or price?
   - How defensible is the differentiation?
   - Customer perception of differentiation

4. BARRIERS TO ENTRY
   - What prevents new competitors from entering?
   - Capital requirements
   - Regulatory barriers
   - Technical complexity
   - Relationship/trust barriers

5. SWITCHING COSTS
   - How hard is it for customers to switch?
   - Data lock-in
   - Integration dependencies
   - Training/learning curve
   - Contractual constraints

6. CORE COMPETENCIES
   - What unique capabilities drive advantage?
   - Are competencies difficult to replicate?
   - How do competencies translate to market advantage?

7. VALUE CHAIN POSITION
   - Where in the value chain is value captured?
   - Vertical integration advantages
   - Platform/ecosystem control

8. COMPETITIVE RECOMMENDATIONS
   - How can advantages be strengthened?
   - What new moats could be built?
   - Where are competitors' advantages vulnerable?

Provide specific evidence and examples for each advantage identified.
"""
