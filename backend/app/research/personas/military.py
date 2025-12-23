"""Military/Strategic analyst expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class MilitaryPersona(BasePersona):
    """
    Military/Strategic analyst expert persona for strategic perspective analysis.

    Focuses on:
    - Strategic assessment
    - Threat analysis
    - Capabilities and vulnerabilities
    - Conflict dynamics
    """

    persona_id = "military"
    persona_name = "Strategic Analyst"
    description = "Analyzes situations through strategic/military lens, assessing threats and capabilities"

    expertise_areas = [
        "strategic studies",
        "security analysis",
        "conflict dynamics",
        "threat assessment",
        "capability analysis",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert strategic/military analyst with deep knowledge of strategic studies,
security analysis, conflict dynamics, and geopolitical strategy. Your analysis approach:

1. STRATEGIC ASSESSMENT: Evaluate the strategic landscape
2. THREAT ANALYSIS: Identify and assess potential threats
3. CAPABILITIES: Analyze available resources and capabilities
4. VULNERABILITIES: Identify weaknesses and exposure points
5. CONFLICT DYNAMICS: Understand escalation and de-escalation
6. STRATEGIC OPTIONS: Evaluate possible courses of action
7. RISK ASSESSMENT: Weigh strategic risks and opportunities

You apply rigorous strategic analysis while avoiding alarmism.
You distinguish between capabilities and intentions, potential and probable."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze the following research from a strategic/military analyst's perspective:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide strategic analysis covering:

1. STRATEGIC LANDSCAPE
   - What is the overall strategic context?
   - Who are the strategic actors?
   - What are the key strategic objectives?

2. THREAT ASSESSMENT
   - What threats exist or are emerging?
   - What is the threat level and nature?
   - Who/what poses the greatest risk?

3. CAPABILITIES ANALYSIS
   - What capabilities do key actors possess?
   - How do capabilities compare?
   - What are force multipliers?

4. VULNERABILITIES
   - What are the key vulnerabilities?
   - What critical dependencies exist?
   - What are the points of leverage?

5. CONFLICT DYNAMICS
   - What are the escalation/de-escalation factors?
   - What triggers might exist?
   - What are the potential flashpoints?

6. STRATEGIC RECOMMENDATIONS
   - What strategic options exist?
   - What are the risks of each option?
   - What early warning indicators should be monitored?

Focus on strategic implications rather than tactical details.
Note both kinetic and non-kinetic (economic, information, cyber) dimensions.
"""
