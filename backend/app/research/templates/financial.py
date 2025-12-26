"""Financial Analysis research template."""

from typing import List

from .base import BaseResearchTemplate
from ..schemas import Source, Finding, ResearchParameters


class FinancialAnalysisTemplate(BaseResearchTemplate):
    """
    Template for financial and stock analysis research.

    Features:
    - Earnings and financial metrics analysis
    - SEC filings and regulatory documents
    - Analyst reports and price targets
    - Market sentiment tracking
    - Risk assessment
    - Valuation analysis
    """

    template_id = "financial"
    template_name = "Financial Analysis"
    description = "Stock and financial analysis for investment research"

    default_perspectives = [
        "valuation",
        "risk",
        "sentiment",
        "fundamental",
    ]

    default_max_searches = 8

    async def generate_search_queries(
        self,
        query: str,
        parameters: ResearchParameters,
    ) -> List[str]:
        """Generate financial analysis search queries."""
        max_searches = parameters.max_searches or self.default_max_searches
        granularity = parameters.granularity or "standard"

        prompt = f"""
You are a financial analyst planning research queries for investment analysis.

Research Topic: {query}

Depth Level: {granularity}

Generate search queries covering these financial analysis angles:
1. EARNINGS: Quarterly/annual results, EPS, revenue growth
2. SEC FILINGS: 10-K, 10-Q, 8-K filings, insider transactions
3. ANALYST COVERAGE: Price targets, ratings, estimates
4. VALUATION: P/E, P/S, EV/EBITDA, comparable analysis
5. GUIDANCE: Forward guidance, management commentary
6. RISKS: Risk factors, regulatory issues, competitive threats
7. NEWS & EVENTS: Recent developments, catalysts, announcements
8. INSTITUTIONAL: Institutional ownership, hedge fund positions
9. SECTOR TRENDS: Industry dynamics, macro factors
10. TECHNICAL: Price action, volume, momentum indicators

For a "{granularity}" depth level:
- "quick": Focus on 3-4 key metrics (earnings, guidance, analyst views)
- "standard": Cover 5-6 key angles with financial depth
- "deep": Comprehensive coverage of all angles with historical context

Return a JSON array of exactly {max_searches} search query strings, ordered by importance.
Example: ["company X Q3 2024 earnings results", "company X SEC 10-K filing 2024", ...]
"""

        result = await self._call_gemini_json(prompt)

        if isinstance(result, list):
            return result[:max_searches]
        return []

    async def extract_findings(
        self,
        query: str,
        sources: List[Source],
        synthesized_content: str,
        parameters: ResearchParameters,
    ) -> List[Finding]:
        """Extract financial analysis findings."""
        # Build source context
        source_context = "\n\n".join([
            f"Source: {s.title or 'Unknown'} ({s.url})\nCredibility: {s.credibility_score or 'Unknown'}\nDomain: {s.domain}"
            for s in sources[:20]
        ])

        prompt = f"""
You are a financial analyst extracting key findings for investment research.

Research Topic: {query}

Synthesized Research Content:
{synthesized_content[:15000]}

Sources Referenced:
{source_context}

Extract findings in these financial analysis categories:

1. FINANCIAL METRICS (finding_type: "fact")
   - Revenue, EPS, margins, growth rates
   - Include: metric name, value, period, YoY change
   - Note beat/miss vs expectations if available

2. COMPANY EVENTS (finding_type: "event")
   - Earnings releases, M&A, leadership changes
   - Include: date, event type, impact
   - Note market reaction if known

3. VALUATION DATA (finding_type: "evidence")
   - Multiples, price targets, fair value estimates
   - Include: source, methodology, comparison
   - Note valuation range and assumptions

4. RISK FACTORS (finding_type: "pattern")
   - Identified business, market, regulatory risks
   - Include: risk type, severity, likelihood
   - Note mitigation strategies if mentioned

5. ANALYST VIEWS (finding_type: "claim")
   - Ratings, price targets, thesis
   - Include: analyst/firm, rating, target, date
   - Note bull/bear case arguments

6. GUIDANCE (finding_type: "prediction")
   - Forward guidance, management outlook
   - Include: metric, guidance range, period
   - Note confidence and caveats

7. SENTIMENT INDICATORS (finding_type: "pattern")
   - Market sentiment, institutional positioning
   - Include: indicator type, reading, trend
   - Note changes from prior periods

8. COMPETITIVE POSITION (finding_type: "relationship")
   - Market share, competitive dynamics
   - Include: competitor comparisons
   - Note relative strengths/weaknesses

9. GAPS (finding_type: "gap")
   - Missing data, unanswered questions
   - Information needed for complete analysis
   - Suggested follow-up research

For each finding, return:
- finding_type: One of 'fact', 'event', 'evidence', 'pattern', 'claim', 'prediction', 'relationship', 'gap'
- content: Detailed finding with specific numbers, dates, and context
- summary: One sentence
- confidence_score: 0.0-1.0 (based on source quality and data recency)
- temporal_context: 'past', 'present', 'ongoing', or 'prediction'
- extracted_data: JSON object with structured financial data:
  - For metrics: {{"metric": "...", "value": ..., "period": "...", "yoy_change": ..., "vs_estimate": "beat/miss/inline"}}
  - For valuation: {{"multiple_type": "...", "value": ..., "peer_comparison": {{}}}}
  - For analyst views: {{"firm": "...", "rating": "...", "target": ..., "date": "..."}}

Return as JSON array.
"""

        result = await self._call_gemini_json(prompt)

        findings = []
        if isinstance(result, list):
            for f in result:
                if isinstance(f, dict):
                    findings.append(
                        Finding(
                            finding_type=f.get("finding_type", "fact"),
                            content=f.get("content", ""),
                            summary=f.get("summary"),
                            confidence_score=f.get("confidence_score", 0.5),
                            temporal_context=f.get("temporal_context", "present"),
                            extracted_data=f.get("extracted_data"),
                        )
                    )

        return findings
