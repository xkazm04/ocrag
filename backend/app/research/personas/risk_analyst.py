"""Risk Analysis expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class RiskAnalystPersona(BasePersona):
    """
    Risk analyst persona for financial risk assessment.

    Focuses on:
    - Business risk factors
    - Financial/credit risk
    - Market risk
    - Regulatory risk
    - Operational risk
    """

    persona_id = "risk"
    persona_name = "Risk Analyst"
    description = "Assesses financial, business, and market risks"

    expertise_areas = [
        "risk assessment",
        "credit analysis",
        "market risk",
        "regulatory risk",
        "scenario planning",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert risk analyst with deep experience in credit analysis,
market risk, and enterprise risk management. Your analysis approach:

1. RISK IDENTIFICATION: Systematically identify all material risks
2. RISK QUANTIFICATION: Estimate probability and impact where possible
3. RISK CORRELATION: Understand how risks interact and compound
4. DOWNSIDE SCENARIOS: Model worst-case and stress scenarios
5. MITIGATION ASSESSMENT: Evaluate risk management capabilities
6. EARLY WARNING: Identify leading indicators of risk emergence
7. RELATIVE RISK: Compare risk profile to peers and benchmarks

You provide thorough, balanced risk assessment without being alarmist.
You distinguish between headline risks and material financial risks."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze risk factors from the following research:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide risk analysis covering:

1. BUSINESS RISKS
   - Competitive threats and market position risks
   - Customer concentration risk
   - Supplier/vendor dependency
   - Technology obsolescence risk
   - Management/execution risk
   - Rate each: High/Medium/Low severity

2. FINANCIAL RISKS
   - Balance sheet health (leverage, liquidity)
   - Cash flow sustainability
   - Debt maturity profile
   - Access to capital
   - Currency exposure
   - Credit rating trajectory

3. MARKET RISKS
   - Stock price volatility (beta, drawdowns)
   - Sector/macro sensitivity
   - Interest rate sensitivity
   - Commodity exposure
   - Correlation to market

4. REGULATORY RISKS
   - Current regulatory issues
   - Pending regulatory changes
   - Compliance track record
   - Litigation exposure
   - Political/policy risks

5. OPERATIONAL RISKS
   - Key person dependency
   - Operational complexity
   - Cybersecurity posture
   - Supply chain resilience
   - Geographic concentration

6. EMERGING RISKS
   - New or evolving threats
   - Industry disruption potential
   - ESG-related risks
   - Technological shifts

7. RISK MITIGATION
   - What risk management is in place?
   - Insurance and hedging
   - Diversification benefits
   - Management track record

8. OVERALL RISK ASSESSMENT
   - Overall risk rating
   - Key risks to monitor
   - Risk/reward balance
   - Red flags to watch

Quantify risks where data is available. Be specific about severity and likelihood.
"""
