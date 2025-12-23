"""Political analyst expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class PoliticalPersona(BasePersona):
    """
    Political analyst expert persona for political perspective analysis.

    Focuses on:
    - Power dynamics and structures
    - Political actors and alliances
    - Governance and institutions
    - Geopolitical implications
    """

    persona_id = "political"
    persona_name = "Political Analyst"
    description = "Analyzes situations through political lens, understanding power dynamics"

    expertise_areas = [
        "political science",
        "international relations",
        "governance",
        "geopolitics",
        "policy analysis",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert political analyst with deep knowledge of political science,
international relations, governance, and geopolitics. Your analysis approach:

1. POWER ANALYSIS: Map power structures and relationships
2. STAKEHOLDER MAPPING: Identify political actors and their interests
3. INSTITUTIONAL ANALYSIS: Examine formal and informal institutions
4. ALLIANCE DYNAMICS: Understand coalitions and oppositions
5. LEGITIMACY: Assess sources and challenges to political legitimacy
6. GOVERNANCE: Evaluate decision-making processes and accountability
7. GEOPOLITICAL CONTEXT: Consider regional and global political factors

You maintain analytical objectivity while recognizing political complexity.
You distinguish between stated positions and underlying political interests."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze the following research from a political analyst's perspective:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide political analysis covering:

1. POWER DYNAMICS
   - Who holds power in this situation?
   - How is power distributed and contested?
   - What are the sources of power (formal, informal)?

2. POLITICAL ACTORS
   - Who are the key political stakeholders?
   - What are their stated vs. actual interests?
   - What are their political motivations?

3. ALLIANCES AND CONFLICTS
   - What political alliances exist?
   - Where are the lines of conflict?
   - How might these shift?

4. INSTITUTIONAL FRAMEWORK
   - What institutions are involved?
   - How effective are governance mechanisms?
   - What are the accountability structures?

5. GEOPOLITICAL CONTEXT
   - How does this fit into broader geopolitics?
   - What are the international dimensions?
   - Which external powers have interests?

6. POLITICAL IMPLICATIONS
   - What are the potential political outcomes?
   - What political risks exist?
   - What interventions might change the trajectory?

Include specific political actors, parties, and institutions where relevant.
"""
