"""Investigative journalism research template."""

from typing import List

from .base import BaseResearchTemplate
from ..schemas import Source, Finding, ResearchParameters


class InvestigativeTemplate(BaseResearchTemplate):
    """
    Template for investigative journalism research.

    Features:
    - Actor identification and profiling
    - Event timeline construction
    - Relationship mapping
    - Evidence chain building
    - Source verification emphasis
    """

    template_id = "investigative"
    template_name = "Investigative Research"
    description = "Deep investigative journalism style research with actor and relationship analysis"

    default_perspectives = [
        "political",
        "economic",
        "psychological",
        "historical",
    ]

    default_max_searches = 8

    async def generate_search_queries(
        self,
        query: str,
        parameters: ResearchParameters,
    ) -> List[str]:
        """Generate investigative search queries."""
        max_searches = parameters.max_searches or self.default_max_searches
        granularity = parameters.granularity or "standard"

        prompt = f"""
You are an investigative journalist planning research queries for a deep investigation.

Investigation Topic: {query}

Depth Level: {granularity}

Generate search queries covering these investigative angles:
1. KEY ACTORS: Who are the main people/organizations involved?
2. TIMELINE: What events happened and when?
3. LOCATIONS: Where did key events occur? What jurisdictions are involved?
4. MOTIVATIONS: What are the underlying interests and relationships?
5. METHODS: How were things done? What mechanisms were used?
6. MONEY TRAIL: Financial connections and transactions
7. OFFICIAL RECORDS: Government filings, court documents, regulatory actions
8. MEDIA COVERAGE: News reports, interviews, public statements

For a "{granularity}" depth level:
- "quick": Focus on 1-3 most critical angles
- "standard": Cover 4-5 key angles with balanced depth
- "deep": Comprehensive coverage of all angles with follow-up queries

Return a JSON array of exactly {max_searches} search query strings, ordered by importance.
Example: ["query about main actor", "query about key event", ...]
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
        """Extract investigative findings."""
        # Build source context
        source_context = "\n\n".join([
            f"Source: {s.title or 'Unknown'} ({s.url})\nCredibility: {s.credibility_score or 'Unknown'}\nDomain: {s.domain}"
            for s in sources[:20]
        ])

        prompt = f"""
You are an investigative analyst extracting key findings for a deep investigation.

Investigation Topic: {query}

Synthesized Research Content:
{synthesized_content[:15000]}

Sources Referenced:
{source_context}

Extract findings in these investigative categories:

1. ACTORS (finding_type: "actor")
   - People, organizations, entities involved
   - Include: name, role, affiliations, significance
   - Note any aliases or connections

2. EVENTS (finding_type: "event")
   - Key incidents, actions, decisions
   - Include: date (if known), location, participants, outcome
   - Note sequence and causation

3. RELATIONSHIPS (finding_type: "relationship")
   - Connections between actors
   - Types: financial, personal, professional, political, criminal
   - Include strength of evidence

4. EVIDENCE (finding_type: "evidence")
   - Documents, statements, data points
   - Include: type, source, significance
   - Note verification status

5. PATTERNS (finding_type: "pattern")
   - Recurring behaviors, methods, structures
   - Include: description, frequency, participants

6. GAPS (finding_type: "gap")
   - Missing information, unanswered questions
   - What we don't know and why it matters
   - Suggested follow-up

For each finding, return:
- finding_type: One of 'actor', 'event', 'relationship', 'evidence', 'pattern', 'gap'
- content: Detailed finding with specific facts
- summary: One sentence
- confidence_score: 0.0-1.0 (based on source quality and corroboration)
- temporal_context: 'past', 'present', 'ongoing', or 'prediction'
- extracted_data: Optional JSON object with structured data specific to the finding type

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
