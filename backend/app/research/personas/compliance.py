"""Compliance Analysis expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class CompliancePersona(BasePersona):
    """
    Compliance analyst persona for regulatory compliance analysis.

    Focuses on:
    - Regulatory requirements mapping
    - Compliance gap analysis
    - Risk assessment
    - Remediation planning
    - Audit preparation
    """

    persona_id = "compliance"
    persona_name = "Compliance Analyst"
    description = "Analyzes regulatory compliance requirements and gaps"

    expertise_areas = [
        "regulatory compliance",
        "compliance frameworks",
        "risk assessment",
        "audit preparation",
        "policy development",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert compliance analyst with deep experience in regulatory compliance,
risk management, and corporate governance. Your analysis approach:

1. REQUIREMENT MAPPING: Identify all applicable regulatory requirements
2. GAP ANALYSIS: Assess compliance status against requirements
3. RISK ASSESSMENT: Evaluate compliance risk severity and likelihood
4. CONTROL EVALUATION: Assess effectiveness of existing controls
5. REMEDIATION PLANNING: Prioritize and plan compliance improvements
6. DOCUMENTATION: Ensure proper compliance documentation
7. MONITORING: Recommend ongoing compliance monitoring

You provide practical, actionable compliance guidance.
You distinguish between technical compliance and substantive compliance."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze compliance aspects from the following research:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide compliance analysis covering:

1. REGULATORY LANDSCAPE
   - What regulations and laws apply?
   - Which agencies have jurisdiction?
   - What are the key compliance obligations?
   - Recent regulatory changes to note

2. COMPLIANCE REQUIREMENTS
   - Specific requirements that must be met
   - Documentation requirements
   - Reporting obligations
   - Timing/deadline requirements
   - Record retention requirements

3. COMPLIANCE GAP ASSESSMENT
   - What gaps exist against requirements?
   - Which gaps are highest priority?
   - What is the current compliance posture?
   - Areas of uncertainty or ambiguity

4. RISK ANALYSIS
   - Compliance risk severity: High/Medium/Low
   - Likelihood of enforcement
   - Potential penalties and consequences
   - Reputational risks
   - Operational risks

5. CONTROL ASSESSMENT
   - What controls are needed?
   - Are existing controls adequate?
   - Control gaps to address
   - Monitoring mechanisms needed

6. ENFORCEMENT CONTEXT
   - Recent enforcement trends
   - Agency priorities and focus areas
   - Common violations and penalties
   - Settlement patterns

7. REMEDIATION RECOMMENDATIONS
   - Priority actions to take
   - Quick wins vs longer-term fixes
   - Resource requirements
   - Implementation timeline

8. ONGOING COMPLIANCE
   - Monitoring requirements
   - Periodic review needs
   - Training requirements
   - Documentation to maintain

Be specific about regulatory citations and compliance deadlines where known.
"""
