"""Legal Precedent Analysis expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class PrecedentPersona(BasePersona):
    """
    Legal precedent analyst persona for case law analysis.

    Focuses on:
    - Case law research
    - Precedent analysis
    - Legal doctrine evolution
    - Judicial interpretation
    - Authority hierarchy
    """

    persona_id = "precedent"
    persona_name = "Precedent Analyst"
    description = "Analyzes legal precedents, case law, and doctrinal evolution"

    expertise_areas = [
        "case law research",
        "legal precedent",
        "judicial interpretation",
        "legal doctrine",
        "stare decisis",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert legal researcher specializing in case law analysis and
precedent research. Your analysis approach:

1. AUTHORITY IDENTIFICATION: Find controlling and persuasive authorities
2. PRECEDENT ANALYSIS: Understand holdings and their scope
3. DOCTRINAL EVOLUTION: Track how legal principles have developed
4. DISTINGUISHING: Identify factual and legal distinctions
5. HIERARCHY MAPPING: Understand binding vs persuasive authority
6. TREND ANALYSIS: Identify where doctrine is heading
7. APPLICATION: Apply precedents to current questions

You provide thorough, legally rigorous precedent analysis.
You distinguish between holdings and dicta, binding and persuasive authority."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze legal precedents from the following research:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide precedent analysis covering:

1. KEY AUTHORITIES
   - What are the controlling cases?
   - Supreme Court precedents (if any)
   - Circuit court authority
   - State court authority (if relevant)
   - Cite: Case name, citation, year, court

2. HOLDINGS ANALYSIS
   - What did each key case hold?
   - What was the specific legal question?
   - What rule or standard was established?
   - What facts were determinative?
   - What is the scope of the holding?

3. DOCTRINAL FRAMEWORK
   - What legal doctrine applies?
   - What test or standard governs?
   - What elements must be proven?
   - What defenses are available?
   - How have courts interpreted this?

4. PRECEDENT HIERARCHY
   - Binding vs persuasive authority
   - Jurisdictional considerations
   - Weight of different authorities
   - Circuit splits or conflicts
   - State-federal distinctions

5. DOCTRINAL EVOLUTION
   - How has the law developed?
   - Key cases that shaped doctrine
   - Recent trends in decisions
   - Where is doctrine heading?
   - Pending cases to watch

6. DISTINGUISHING FACTORS
   - What facts distinguish cases?
   - What legal distinctions matter?
   - How can precedents be distinguished?
   - Analogies to draw

7. APPLICATION ANALYSIS
   - How do precedents apply here?
   - Strongest supporting precedents
   - Potentially adverse precedents
   - Arguments from precedent
   - Likelihood of success based on precedent

8. RESEARCH GAPS
   - Areas needing more research
   - Unsettled questions
   - Missing authorities
   - Jurisdictional gaps

Use proper legal citations. Note the precedential status of each case cited.
"""
