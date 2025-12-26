"""Competitive intelligence report composers."""

from typing import List, Optional, Dict, Any

from .base import BaseComposer
from ..schemas import ReportData, ReportVariant


class CompetitiveComposer(BaseComposer):
    """
    Composer for competitive intelligence report variants.

    Supports:
    - competitive_matrix: Side-by-side competitor comparison
    - swot_analysis: Structured SWOT format
    - battlecard: Sales enablement format
    """

    def compose(
        self,
        data: ReportData,
        variant: ReportVariant,
        title: Optional[str] = None,
        include_sections: Optional[List[str]] = None,
    ) -> str:
        """Generate competitive intelligence report variant."""
        if variant == ReportVariant.COMPETITIVE_MATRIX:
            return self._competitive_matrix(data, title)
        elif variant == ReportVariant.SWOT_ANALYSIS:
            return self._swot_analysis(data, title)
        elif variant == ReportVariant.BATTLECARD:
            return self._battlecard(data, title)
        else:
            raise ValueError(f"Unsupported variant for competitive: {variant}")

    def _competitive_matrix(self, data: ReportData, title: Optional[str]) -> str:
        """Generate competitive comparison matrix."""
        report_title = title or f"Competitive Matrix: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        # Extract competitors (actors in competitive context)
        competitors = [f for f in data.findings if f.get("finding_type") == "actor"]
        facts = [f for f in data.findings if f.get("finding_type") == "fact"]

        sections.append("## Competitive Landscape\n")

        if not competitors:
            sections.append("*No specific competitors identified. Showing key market findings.*\n")
            sections.append("")

            # Fall back to showing top facts
            for fact in facts[:10]:
                sections.append(f"- {fact.get('content', '')}")
            sections.append("")
        else:
            # Build competitor table
            sections.append("| Competitor | Position | Key Differentiator | Confidence |")
            sections.append("|------------|----------|-------------------|------------|")

            for comp in competitors[:10]:
                name = comp.get("summary", "Unknown")[:30]
                content = comp.get("content", "")
                extracted = comp.get("extracted_data", {})

                position = extracted.get("market_position", "Unknown")
                diff = extracted.get("differentiators", [content[:50]])
                if isinstance(diff, list):
                    diff = diff[0] if diff else content[:50]

                confidence = comp.get("confidence_score", 0.5)

                sections.append(f"| {name} | {position} | {diff[:40]} | {confidence:.0%} |")

            sections.append("")

        # Market insights
        sections.append("## Market Insights\n")

        # Look for market-related patterns
        patterns = [f for f in data.findings if f.get("finding_type") == "pattern"]
        if patterns:
            for pattern in patterns[:5]:
                sections.append(f"### {pattern.get('summary', 'Market Pattern')}")
                sections.append(pattern.get("content", ""))
                sections.append("")
        else:
            for fact in facts[:5]:
                sections.append(f"- {fact.get('content', '')}")
            sections.append("")

        # Pricing intelligence (if available from perspectives)
        pricing_perspective = next(
            (p for p in data.perspectives if "pricing" in p.get("perspective_type", "")),
            None
        )

        if pricing_perspective:
            sections.append(self._section_divider())
            sections.append("## Pricing Intelligence\n")
            sections.append(pricing_perspective.get("analysis_text", ""))
            sections.append("")

            insights = pricing_perspective.get("key_insights", [])
            if insights:
                sections.append("**Key Pricing Insights:**")
                for insight in insights:
                    sections.append(f"- {insight}")
            sections.append("")

        return "\n".join(sections)

    def _swot_analysis(self, data: ReportData, title: Optional[str]) -> str:
        """Generate SWOT analysis report."""
        report_title = title or f"SWOT Analysis: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        # Find SWOT perspective
        swot_perspective = next(
            (p for p in data.perspectives if p.get("perspective_type") == "swot"),
            None
        )

        sections.append("## SWOT Analysis\n")

        if swot_perspective:
            sections.append(swot_perspective.get("analysis_text", ""))
            sections.append("")

            insights = swot_perspective.get("key_insights", [])
            if insights:
                # Try to categorize insights into SWOT
                sections.append(self._categorize_swot(insights))
        else:
            # Generate SWOT from findings
            sections.append(self._generate_swot_from_findings(data))

        # Recommendations
        sections.append(self._section_divider())
        sections.append("## Strategic Recommendations\n")

        all_recs = []
        for p in data.perspectives:
            all_recs.extend(p.get("recommendations", []))

        if all_recs:
            for rec in all_recs[:8]:
                sections.append(f"- {rec}")
        else:
            sections.append("*No specific recommendations generated.*")

        sections.append("")
        return "\n".join(sections)

    def _categorize_swot(self, insights: List[str]) -> str:
        """Attempt to categorize insights into SWOT quadrants."""
        lines = []

        # Simple keyword matching for categorization
        strengths = []
        weaknesses = []
        opportunities = []
        threats = []

        strength_words = ["strong", "advantage", "leader", "best", "superior", "excellent"]
        weakness_words = ["weak", "lacking", "behind", "limited", "poor", "gap"]
        opportunity_words = ["opportunity", "potential", "could", "growth", "expand", "market"]
        threat_words = ["threat", "risk", "competitor", "challenge", "decline", "disruption"]

        for insight in insights:
            lower = insight.lower()
            if any(w in lower for w in strength_words):
                strengths.append(insight)
            elif any(w in lower for w in weakness_words):
                weaknesses.append(insight)
            elif any(w in lower for w in opportunity_words):
                opportunities.append(insight)
            elif any(w in lower for w in threat_words):
                threats.append(insight)
            else:
                # Default to opportunities
                opportunities.append(insight)

        lines.append("### Strengths")
        for s in strengths or ["*Analysis pending*"]:
            lines.append(f"- {s}")
        lines.append("")

        lines.append("### Weaknesses")
        for w in weaknesses or ["*Analysis pending*"]:
            lines.append(f"- {w}")
        lines.append("")

        lines.append("### Opportunities")
        for o in opportunities or ["*Analysis pending*"]:
            lines.append(f"- {o}")
        lines.append("")

        lines.append("### Threats")
        for t in threats or ["*Analysis pending*"]:
            lines.append(f"- {t}")
        lines.append("")

        return "\n".join(lines)

    def _generate_swot_from_findings(self, data: ReportData) -> str:
        """Generate SWOT structure from findings when no SWOT perspective exists."""
        lines = []

        # Map finding types to SWOT
        patterns = [f.get("content", "") for f in data.findings if f.get("finding_type") == "pattern"]
        facts = [f.get("content", "") for f in data.findings if f.get("finding_type") == "fact"]

        lines.append("### Strengths")
        lines.append("*Derived from research findings:*")
        for p in patterns[:2]:
            lines.append(f"- {p[:150]}")
        lines.append("")

        lines.append("### Weaknesses")
        gaps = [f.get("content", "") for f in data.findings if f.get("finding_type") == "gap"]
        for g in gaps[:2]:
            lines.append(f"- {g[:150]}")
        if not gaps:
            lines.append("- *No specific weaknesses identified*")
        lines.append("")

        lines.append("### Opportunities")
        for f in facts[:2]:
            lines.append(f"- {f[:150]}")
        lines.append("")

        lines.append("### Threats")
        lines.append("- *Competitive analysis required for threat assessment*")
        lines.append("")

        return "\n".join(lines)

    def _battlecard(self, data: ReportData, title: Optional[str]) -> str:
        """Generate sales battlecard format."""
        report_title = title or f"Battlecard: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        sections.append("## Quick Reference Battlecard\n")

        # Target company/product (from query)
        sections.append(f"**Subject:** {data.session_query}\n")

        # Key differentiators
        sections.append("### Key Differentiators\n")

        competitive_adv = next(
            (p for p in data.perspectives if "competitive_advantage" in p.get("perspective_type", "")),
            None
        )

        if competitive_adv:
            insights = competitive_adv.get("key_insights", [])
            for insight in insights[:4]:
                sections.append(f"- {insight}")
        else:
            patterns = [f for f in data.findings if f.get("finding_type") == "pattern"]
            for p in patterns[:4]:
                sections.append(f"- {p.get('summary', p.get('content', '')[:80])}")

        sections.append("")

        # Competitive weaknesses to exploit
        sections.append("### Competitive Weaknesses\n")
        gaps = [f for f in data.findings if f.get("finding_type") == "gap"]
        if gaps:
            for gap in gaps[:3]:
                sections.append(f"- {gap.get('content', '')[:100]}")
        else:
            sections.append("- *Further competitive analysis needed*")
        sections.append("")

        # Talk track
        sections.append("### Suggested Talk Track\n")
        sections.append("When engaging prospects:")
        sections.append("")

        # Use recommendations as talk track
        all_recs = []
        for p in data.perspectives:
            all_recs.extend(p.get("recommendations", []))

        if all_recs:
            for i, rec in enumerate(all_recs[:3], 1):
                sections.append(f"{i}. {rec}")
        else:
            sections.append("1. *Customize based on prospect needs*")

        sections.append("")

        # Objection handling
        sections.append("### Common Objections\n")
        warnings = []
        for p in data.perspectives:
            warnings.extend(p.get("warnings", []))

        if warnings:
            for warning in warnings[:3]:
                sections.append(f"- **Objection:** {warning[:80]}")
                sections.append(f"  - **Response:** *Prepare tailored response*")
        else:
            sections.append("*No common objections identified*")

        sections.append("")
        return "\n".join(sections)
