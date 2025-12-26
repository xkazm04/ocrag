"""Regulatory Risk Analysis expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class RegulatoryRiskPersona(BasePersona):
    """
    Regulatory risk analyst persona for enforcement and regulatory risk analysis.

    Focuses on:
    - Enforcement trends
    - Regulatory priorities
    - Penalty patterns
    - Agency behavior prediction
    - Risk mitigation strategies
    """

    persona_id = "regulatory_risk"
    persona_name = "Regulatory Risk Analyst"
    description = "Analyzes regulatory enforcement risk and agency behavior"

    expertise_areas = [
        "regulatory enforcement",
        "agency behavior",
        "penalty analysis",
        "risk mitigation",
        "regulatory strategy",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert regulatory risk analyst with deep experience in agency
enforcement patterns and regulatory strategy. Your analysis approach:

1. ENFORCEMENT ANALYSIS: Track agency enforcement patterns and priorities
2. RISK QUANTIFICATION: Assess likelihood and severity of regulatory action
3. PENALTY ANALYSIS: Understand penalty frameworks and typical outcomes
4. AGENCY BEHAVIOR: Predict regulatory responses based on patterns
5. TRIGGER IDENTIFICATION: Identify what triggers regulatory attention
6. MITIGATION STRATEGIES: Recommend risk reduction approaches
7. EARLY WARNING: Identify leading indicators of regulatory risk

You provide strategic regulatory risk intelligence.
You distinguish between regulatory posturing and actual enforcement priorities."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze regulatory risk from the following research:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide regulatory risk analysis covering:

1. REGULATORY LANDSCAPE
   - Which agencies have jurisdiction?
   - Overlapping regulatory authority
   - State vs federal regulators
   - International regulatory considerations
   - Regulatory relationship dynamics

2. ENFORCEMENT TRENDS
   - Recent enforcement actions in this area
   - Agency priority areas
   - Types of violations being targeted
   - Enforcement statistics and trends
   - Notable settlements and penalties

3. RISK ASSESSMENT
   - Overall regulatory risk level: High/Medium/Low
   - Likelihood of regulatory scrutiny
   - Likelihood of enforcement action
   - Potential severity of action
   - Time horizon for risk

4. PENALTY ANALYSIS
   - Typical penalties for violations
   - Penalty calculation frameworks
   - Aggravating factors
   - Mitigating factors
   - Recent penalty trends

5. TRIGGER FACTORS
   - What triggers regulatory attention?
   - Red flags regulators look for
   - Whistleblower considerations
   - Self-reporting implications
   - Competitor complaints

6. AGENCY BEHAVIOR PREDICTION
   - How will regulators likely respond?
   - Timing considerations
   - Political and policy context
   - Leadership and personnel factors
   - Budget and resource constraints

7. RISK MITIGATION
   - Recommended risk reduction steps
   - Proactive engagement strategies
   - Documentation and compliance programs
   - Response preparation
   - Relationship management

8. MONITORING RECOMMENDATIONS
   - Regulatory developments to watch
   - Early warning indicators
   - Information sources to monitor
   - Trigger points for action

Quantify risks where possible. Note sources for enforcement data.
"""
