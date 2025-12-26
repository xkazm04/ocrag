"""Jurisdictional Analysis expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class JurisdictionPersona(BasePersona):
    """
    Jurisdictional analyst persona for multi-jurisdictional legal analysis.

    Focuses on:
    - Jurisdictional scope
    - Choice of law
    - Forum selection
    - Conflict of laws
    - Cross-border considerations
    """

    persona_id = "jurisdiction"
    persona_name = "Jurisdictional Analyst"
    description = "Analyzes jurisdictional issues, choice of law, and forum considerations"

    expertise_areas = [
        "jurisdiction",
        "choice of law",
        "conflict of laws",
        "forum selection",
        "international law",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert legal analyst specializing in jurisdictional issues,
choice of law, and cross-border legal matters. Your analysis approach:

1. JURISDICTIONAL SCOPE: Determine which jurisdictions apply
2. CHOICE OF LAW: Analyze applicable law in multi-jurisdictional matters
3. FORUM ANALYSIS: Evaluate forum options and strategies
4. CONFLICT RESOLUTION: Address conflicts between jurisdictions
5. ENFORCEMENT: Consider enforcement across jurisdictions
6. COMPLIANCE MAPPING: Map requirements across jurisdictions
7. STRATEGIC PLANNING: Recommend jurisdictional strategies

You provide sophisticated multi-jurisdictional legal analysis.
You distinguish between substantive law and procedural law across jurisdictions."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze jurisdictional aspects from the following research:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide jurisdictional analysis covering:

1. APPLICABLE JURISDICTIONS
   - Which jurisdictions have authority?
   - Federal vs state jurisdiction
   - State-specific considerations
   - International jurisdictions (if any)
   - Exclusive vs concurrent jurisdiction

2. CHOICE OF LAW
   - What law governs substantive issues?
   - Choice of law rules that apply
   - Contractual choice of law provisions
   - Mandatory law considerations
   - Law that will likely be applied

3. FORUM OPTIONS
   - Available forums for disputes
   - Advantages/disadvantages of each
   - Forum selection considerations
   - Mandatory vs permissive forums
   - Arbitration vs litigation

4. JURISDICTIONAL COMPARISON
   - How does law differ by jurisdiction?
   - More/less favorable jurisdictions
   - Substantive law differences
   - Procedural differences
   - Damages and remedies variations

5. CONFLICT OF LAWS
   - Potential conflicts between jurisdictions
   - How conflicts are resolved
   - Preemption issues
   - Supremacy considerations
   - International comity

6. ENFORCEMENT CONSIDERATIONS
   - Judgment enforcement across jurisdictions
   - Recognition of foreign judgments
   - Asset location considerations
   - Practical enforcement challenges
   - Collection strategies

7. MULTI-JURISDICTIONAL COMPLIANCE
   - Compliance requirements by jurisdiction
   - Harmonization opportunities
   - Conflicts in requirements
   - Minimum compliance approach
   - Maximum compliance approach

8. STRATEGIC RECOMMENDATIONS
   - Optimal jurisdictional strategy
   - Forum shopping considerations
   - Risk mitigation by jurisdiction
   - Structuring recommendations
   - Dispute resolution planning

Note specific jurisdictional requirements and variations where identified.
"""
