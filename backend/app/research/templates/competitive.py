"""Competitive Intelligence research template."""

from typing import List

from .base import BaseResearchTemplate
from ..schemas import Source, Finding, ResearchParameters


class CompetitiveIntelligenceTemplate(BaseResearchTemplate):
    """
    Template for competitive intelligence research.

    Features:
    - Competitor identification and profiling
    - Market positioning analysis
    - Product/service comparison
    - Strategic moves tracking
    - SWOT analysis support
    - Pricing intelligence
    """

    template_id = "competitive"
    template_name = "Competitive Intelligence"
    description = "Market and competitor analysis for strategic business intelligence"

    default_perspectives = [
        "market_position",
        "competitive_advantage",
        "swot",
        "pricing_strategy",
    ]

    default_max_searches = 6

    async def generate_search_queries(
        self,
        query: str,
        parameters: ResearchParameters,
    ) -> List[str]:
        """Generate competitive intelligence search queries."""
        max_searches = parameters.max_searches or self.default_max_searches
        granularity = parameters.granularity or "standard"

        prompt = f"""
You are a competitive intelligence analyst planning research queries for market analysis.

Research Topic: {query}

Depth Level: {granularity}

Generate search queries covering these competitive intelligence angles:
1. COMPETITORS: Who are the main competitors in this space?
2. MARKET SHARE: What is the market distribution and sizing?
3. PRODUCT COMPARISON: Features, capabilities, differentiators
4. PRICING: Pricing models, tiers, competitive positioning
5. PARTNERSHIPS: Strategic alliances, integrations, ecosystems
6. ACQUISITIONS: M&A activity, investments, expansion
7. EXECUTIVE MOVES: Leadership changes, key hires, talent
8. CUSTOMER SENTIMENT: Reviews, NPS, market perception
9. NEWS & ANNOUNCEMENTS: Product launches, pivots, strategy shifts
10. FINANCIAL PERFORMANCE: Revenue, growth, funding (if public/disclosed)

For a "{granularity}" depth level:
- "quick": Focus on 2-3 most critical angles (competitors, positioning)
- "standard": Cover 4-5 key angles with balanced depth
- "deep": Comprehensive coverage of all angles with follow-up queries

Return a JSON array of exactly {max_searches} search query strings, ordered by importance.
Example: ["company X vs competitors market share 2024", "company X pricing comparison alternatives", ...]
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
        """Extract competitive intelligence findings."""
        # Build source context
        source_context = "\n\n".join([
            f"Source: {s.title or 'Unknown'} ({s.url})\nCredibility: {s.credibility_score or 'Unknown'}\nDomain: {s.domain}"
            for s in sources[:20]
        ])

        prompt = f"""
You are a competitive intelligence analyst extracting key findings for strategic analysis.

Research Topic: {query}

Synthesized Research Content:
{synthesized_content[:15000]}

Sources Referenced:
{source_context}

Extract findings in these competitive intelligence categories:

1. COMPETITORS (finding_type: "actor")
   - Companies, products, services competing in this space
   - Include: name, market position, key differentiators
   - Note market segment focus and target customers

2. MARKET DYNAMICS (finding_type: "fact")
   - Market size, growth rates, trends
   - Include: specific numbers with dates when available
   - Note geographic variations

3. COMPETITIVE MOVES (finding_type: "event")
   - Product launches, pivots, expansions
   - Include: date, company, action, impact
   - Note strategic implications

4. RELATIONSHIPS (finding_type: "relationship")
   - Partnerships, integrations, acquisitions
   - Types: strategic alliance, acquisition, investment, competition
   - Include deal terms if known

5. COMPETITIVE ADVANTAGES (finding_type: "pattern")
   - Recurring strengths, moats, differentiators
   - Include: description, evidence, sustainability
   - Note whether advantage is growing or eroding

6. PRICING INTELLIGENCE (finding_type: "evidence")
   - Pricing models, price points, discount patterns
   - Include: tier structure, feature gates, comparison
   - Note recent pricing changes

7. CUSTOMER INSIGHTS (finding_type: "claim")
   - Customer sentiment, reviews, pain points
   - Include: source of claim, sentiment direction
   - Note NPS or satisfaction metrics if available

8. GAPS (finding_type: "gap")
   - Market opportunities, unmet needs
   - Areas where data is limited or uncertain
   - Suggested follow-up research

For each finding, return:
- finding_type: One of 'actor', 'fact', 'event', 'relationship', 'pattern', 'evidence', 'claim', 'gap'
- content: Detailed finding with specific facts, numbers, and context
- summary: One sentence
- confidence_score: 0.0-1.0 (based on source quality and recency)
- temporal_context: 'past', 'present', 'ongoing', or 'prediction'
- extracted_data: JSON object with structured data specific to the finding type:
  - For competitors: {{"company": "...", "market_position": "leader|challenger|niche", "differentiators": [...]}}
  - For market data: {{"metric": "...", "value": "...", "date": "...", "trend": "growing|stable|declining"}}
  - For pricing: {{"model": "...", "tiers": [...], "comparison": {{}}}}

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
