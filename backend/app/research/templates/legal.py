"""Legal Research template."""

from typing import List

from .base import BaseResearchTemplate
from ..schemas import Source, Finding, ResearchParameters


class LegalResearchTemplate(BaseResearchTemplate):
    """
    Template for legal and regulatory research.

    Features:
    - Case law analysis
    - Statutory interpretation
    - Regulatory compliance
    - Legal precedent tracking
    - Jurisdictional analysis
    """

    template_id = "legal"
    template_name = "Legal Research"
    description = "Legal and regulatory research for compliance and case analysis"

    default_perspectives = [
        "compliance",
        "precedent",
        "regulatory_risk",
        "jurisdiction",
    ]

    default_max_searches = 10

    async def generate_search_queries(
        self,
        query: str,
        parameters: ResearchParameters,
    ) -> List[str]:
        """Generate legal research search queries."""
        max_searches = parameters.max_searches or self.default_max_searches
        granularity = parameters.granularity or "standard"

        prompt = f"""
You are a legal researcher planning research queries for legal analysis.

Research Topic: {query}

Depth Level: {granularity}

Generate search queries covering these legal research angles:
1. CASE LAW: Relevant court decisions, precedents, rulings
2. STATUTES: Applicable laws, acts, codes
3. REGULATIONS: Agency rules, regulatory guidance
4. ENFORCEMENT: Enforcement actions, penalties, settlements
5. COURT FILINGS: Complaints, motions, briefs, orders
6. LEGAL COMMENTARY: Law review articles, expert analysis
7. AGENCY GUIDANCE: Regulatory interpretations, advisory opinions
8. LEGISLATIVE HISTORY: Intent, debates, amendments
9. JURISDICTIONAL: State vs federal, international
10. RECENT DEVELOPMENTS: New cases, regulatory changes, pending legislation

For a "{granularity}" depth level:
- "quick": Focus on 3-4 key authorities (leading cases, main statutes)
- "standard": Cover 5-6 key angles with legal depth
- "deep": Comprehensive coverage including secondary sources and commentary

Return a JSON array of exactly {max_searches} search query strings, ordered by importance.
Example: ["Supreme Court ruling on X", "Title VII employment discrimination cases 2024", ...]
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
        """Extract legal research findings."""
        # Build source context
        source_context = "\n\n".join([
            f"Source: {s.title or 'Unknown'} ({s.url})\nCredibility: {s.credibility_score or 'Unknown'}\nDomain: {s.domain}"
            for s in sources[:20]
        ])

        prompt = f"""
You are a legal analyst extracting key findings for legal research.

Research Topic: {query}

Synthesized Research Content:
{synthesized_content[:15000]}

Sources Referenced:
{source_context}

Extract findings in these legal research categories:

1. CASE LAW (finding_type: "evidence")
   - Court decisions, rulings, precedents
   - Include: case citation, court, date, holding
   - Note binding vs persuasive authority
   - Indicate if overruled/distinguished

2. STATUTORY PROVISIONS (finding_type: "fact")
   - Applicable laws and statutory text
   - Include: statute citation, key provisions
   - Note effective dates and amendments
   - Indicate jurisdictional scope

3. REGULATORY REQUIREMENTS (finding_type: "fact")
   - Agency rules and regulations
   - Include: CFR citation, requirements
   - Note enforcement guidance
   - Indicate compliance deadlines

4. LEGAL HOLDINGS (finding_type: "claim")
   - Key legal principles established
   - Include: source, scope, limitations
   - Note circuit splits or conflicts
   - Indicate precedential value

5. ENFORCEMENT PATTERNS (finding_type: "pattern")
   - Agency enforcement trends
   - Include: types of violations, penalties
   - Note focus areas and priorities
   - Indicate risk levels

6. LEGAL RELATIONSHIPS (finding_type: "relationship")
   - How authorities relate to each other
   - Types: overrules, distinguishes, extends, cites
   - Include hierarchy and weight
   - Note evolution of doctrine

7. RISK FACTORS (finding_type: "pattern")
   - Legal and regulatory risks identified
   - Include: risk type, likelihood, severity
   - Note mitigation approaches
   - Indicate compliance gaps

8. GAPS (finding_type: "gap")
   - Unsettled legal questions
   - Jurisdictional uncertainties
   - Missing authorities
   - Areas needing further research

For each finding, return:
- finding_type: One of 'evidence', 'fact', 'claim', 'pattern', 'relationship', 'gap'
- content: Detailed finding with legal citations and context
- summary: One sentence
- confidence_score: 0.0-1.0 (based on source authority and recency)
- temporal_context: 'past', 'present', 'ongoing', or 'prediction'
- extracted_data: JSON object with structured legal data:
  - For cases: {{"citation": "...", "court": "...", "year": ..., "holding": "...", "status": "good_law/overruled/distinguished"}}
  - For statutes: {{"citation": "...", "jurisdiction": "...", "key_provisions": [...], "effective_date": "..."}}
  - For regulations: {{"cfr_citation": "...", "agency": "...", "requirements": [...], "enforcement_status": "..."}}

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
