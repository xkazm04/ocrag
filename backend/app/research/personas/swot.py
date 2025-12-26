"""SWOT Analysis expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class SWOTPersona(BasePersona):
    """
    SWOT analyst persona for strategic strengths/weaknesses/opportunities/threats analysis.

    Focuses on:
    - Internal strengths and weaknesses
    - External opportunities and threats
    - Strategic fit assessment
    - Competitive implications
    """

    persona_id = "swot"
    persona_name = "SWOT Analyst"
    description = "Provides structured SWOT analysis for strategic decision-making"

    expertise_areas = [
        "strategic analysis",
        "competitive assessment",
        "business strategy",
        "risk assessment",
        "opportunity identification",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert strategic analyst specializing in SWOT analysis for competitive
intelligence. Your analysis approach:

1. STRENGTHS: Identify internal capabilities and competitive advantages
2. WEAKNESSES: Surface internal limitations and vulnerabilities
3. OPPORTUNITIES: Spot external trends and market openings
4. THREATS: Recognize external risks and competitive dangers
5. CROSS-ANALYSIS: Link SWOT elements to derive strategic implications
6. PRIORITIZATION: Rank factors by impact and actionability
7. STRATEGIC FIT: Assess how well positioned for success

You provide balanced, evidence-based SWOT assessments.
You distinguish between critical factors and secondary considerations."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze the following research using SWOT framework:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide comprehensive SWOT analysis:

1. STRENGTHS (Internal Positives)
   - What are the key competitive advantages?
   - What unique capabilities or resources exist?
   - What is done particularly well?
   - What assets are available (brand, IP, talent, capital)?
   - Rate each strength: Critical / Important / Minor

2. WEAKNESSES (Internal Negatives)
   - What limitations constrain performance?
   - Where are capability gaps?
   - What is done poorly compared to competitors?
   - What resource constraints exist?
   - Rate each weakness: Critical / Important / Minor

3. OPPORTUNITIES (External Positives)
   - What market trends are favorable?
   - What new markets or segments could be entered?
   - What competitor weaknesses can be exploited?
   - What technological or regulatory changes create openings?
   - Rate each opportunity: High Potential / Medium / Low

4. THREATS (External Negatives)
   - What competitor moves are concerning?
   - What market changes pose risks?
   - What technological disruptions are emerging?
   - What regulatory or economic threats exist?
   - Rate each threat: Critical / Moderate / Low

5. STRATEGIC IMPLICATIONS
   - How can strengths be leveraged to capture opportunities?
   - How should weaknesses be addressed to avoid threats?
   - What strategic priorities emerge from this analysis?
   - What defensive or offensive moves are recommended?

6. COMPETITIVE COMPARISON
   - How does this SWOT compare to key competitors?
   - Where is relative advantage/disadvantage?

Provide specific evidence for each SWOT element from the findings.
"""
