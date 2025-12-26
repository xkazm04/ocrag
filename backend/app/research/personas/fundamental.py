"""Fundamental Analysis expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class FundamentalPersona(BasePersona):
    """
    Fundamental analyst persona for business and financial analysis.

    Focuses on:
    - Business model analysis
    - Financial statement analysis
    - Competitive positioning
    - Management quality
    - Growth drivers
    """

    persona_id = "fundamental"
    persona_name = "Fundamental Analyst"
    description = "Provides fundamental business and financial analysis"

    expertise_areas = [
        "financial statement analysis",
        "business model analysis",
        "competitive analysis",
        "management assessment",
        "earnings quality",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert fundamental analyst with deep experience in equity research,
business analysis, and financial statement analysis. Your analysis approach:

1. BUSINESS MODEL: Understand how the company makes money
2. FINANCIAL ANALYSIS: Deep dive into financial statements
3. QUALITY OF EARNINGS: Assess earnings sustainability and quality
4. COMPETITIVE POSITION: Analyze market position and moats
5. MANAGEMENT ASSESSMENT: Evaluate leadership and strategy
6. GROWTH ANALYSIS: Identify and assess growth drivers
7. CAPITAL ALLOCATION: Review investment and return metrics

You provide thorough fundamental analysis grounded in financial data.
You distinguish between reported numbers and underlying business reality."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze fundamentals from the following research:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide fundamental analysis covering:

1. BUSINESS MODEL
   - How does the company generate revenue?
   - What are the key products/services?
   - Customer base and relationships
   - Unit economics and scalability
   - Business model durability

2. REVENUE ANALYSIS
   - Revenue trends and growth drivers
   - Revenue mix by segment/product
   - Recurring vs one-time revenue
   - Customer concentration
   - Pricing power indicators

3. PROFITABILITY ANALYSIS
   - Gross margin trends and drivers
   - Operating leverage
   - EBITDA and operating margins
   - Net margin and EPS trends
   - Margin expansion/contraction factors

4. BALANCE SHEET HEALTH
   - Asset quality and composition
   - Debt levels and structure
   - Working capital efficiency
   - Cash position and burn rate
   - Book value trends

5. CASH FLOW ANALYSIS
   - Operating cash flow quality
   - Free cash flow generation
   - CapEx requirements
   - Cash conversion cycle
   - FCF yield analysis

6. EARNINGS QUALITY
   - Accounting policy assessment
   - One-time items and adjustments
   - Revenue recognition practices
   - Accruals vs cash earnings
   - Management incentive alignment

7. MANAGEMENT & GOVERNANCE
   - Management track record
   - Strategic vision and execution
   - Capital allocation decisions
   - Insider ownership
   - Board composition

8. GROWTH OUTLOOK
   - Organic growth drivers
   - M&A strategy and integration
   - TAM and market share opportunity
   - Investment in growth
   - Guidance credibility

9. FUNDAMENTAL CONCLUSION
   - Overall business quality rating
   - Key fundamental strengths
   - Key fundamental concerns
   - Catalysts for fundamental improvement/deterioration

Include specific financial metrics and trends where available.
"""
