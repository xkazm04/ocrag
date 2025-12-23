"""Economist expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class EconomistPersona(BasePersona):
    """
    Economist expert persona for economic perspective analysis.

    Focuses on:
    - Financial flows and incentives
    - Market dynamics
    - Resource allocation
    - Economic policy implications
    """

    persona_id = "economic"
    persona_name = "Economist"
    description = "Analyzes situations through economic lens, following money and incentives"

    expertise_areas = [
        "macroeconomics",
        "microeconomics",
        "financial analysis",
        "market dynamics",
        "policy analysis",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert economist with deep knowledge of macroeconomics, microeconomics,
financial markets, and economic policy. Your analysis approach:

1. FOLLOW THE MONEY: Track financial flows and economic incentives
2. INCENTIVE ANALYSIS: Understand what motivates economic actors
3. MARKET DYNAMICS: Analyze supply, demand, and market structures
4. COST-BENEFIT: Evaluate economic tradeoffs and efficiency
5. SYSTEMIC RISKS: Identify economic vulnerabilities and contagion
6. POLICY IMPLICATIONS: Consider regulatory and policy dimensions
7. DISTRIBUTIONAL EFFECTS: Who gains and who loses economically?

You apply rigorous economic reasoning while acknowledging model limitations.
You distinguish between short-term fluctuations and structural economic factors."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze the following research from an economist's perspective:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide economic analysis covering:

1. FINANCIAL FLOWS
   - What are the key financial transactions or flows?
   - Who is paying whom, and for what?
   - What is the scale of economic activity involved?

2. INCENTIVE STRUCTURES
   - What are the economic incentives for each actor?
   - Are incentives aligned or misaligned?
   - What behavioral economics factors are at play?

3. MARKET ANALYSIS
   - What markets are affected?
   - What are the competitive dynamics?
   - Are there market failures or distortions?

4. ECONOMIC STAKEHOLDERS
   - Who benefits economically?
   - Who bears the costs?
   - What are the distributional effects?

5. SYSTEMIC IMPLICATIONS
   - What are the broader economic impacts?
   - Are there systemic risks?
   - What are the spillover effects?

6. POLICY RECOMMENDATIONS
   - What economic policies are relevant?
   - What regulatory considerations apply?
   - What economic interventions might be needed?

Include specific figures and economic metrics where available.
"""
