"""Executive summary composer."""

from typing import List, Optional

from .base import BaseComposer
from ..schemas import ReportData, ReportVariant


class ExecutiveSummaryComposer(BaseComposer):
    """
    Composer for executive summary reports.

    Generates a concise 1-2 page overview focusing on:
    - Key findings (high confidence only)
    - Main conclusions
    - Critical recommendations
    - Top sources
    """

    def compose(
        self,
        data: ReportData,
        variant: ReportVariant,
        title: Optional[str] = None,
        include_sections: Optional[List[str]] = None,
    ) -> str:
        """Generate executive summary markdown."""
        report_title = title or f"Executive Summary: {data.session_query[:60]}"

        sections = []

        # Header
        sections.append(self._header(report_title, data))

        # Quick stats
        sections.append(self._quick_stats(data))

        # Key findings (top 5 by confidence)
        sections.append(self._key_findings(data))

        # Main insights from perspectives
        sections.append(self._main_insights(data))

        # Recommendations
        sections.append(self._recommendations(data))

        # Top sources
        sections.append(self._top_sources(data))

        return "\n".join(sections)

    def _quick_stats(self, data: ReportData) -> str:
        """Generate quick statistics section."""
        high_conf = len(data.high_confidence_findings)
        verified = len([c for c in data.claims if c.get("verification_status") == "verified"])

        return f"""## At a Glance

| Metric | Value |
|--------|-------|
| Total Findings | {len(data.findings)} |
| High Confidence | {high_conf} |
| Perspectives Analyzed | {len(data.perspectives)} |
| Sources Reviewed | {len(data.sources)} |
| Verified Claims | {verified} |

---

"""

    def _key_findings(self, data: ReportData) -> str:
        """Generate key findings section."""
        lines = ["## Key Findings", ""]

        # Top 5 findings by confidence
        top_findings = sorted(
            data.findings,
            key=lambda f: f.get("confidence_score", 0),
            reverse=True
        )[:5]

        if not top_findings:
            lines.append("*No findings extracted.*")
        else:
            for i, finding in enumerate(top_findings, 1):
                ftype = finding.get("finding_type", "fact")
                summary = finding.get("summary") or finding.get("content", "")[:100]
                confidence = finding.get("confidence_score", 0)

                lines.append(f"{i}. **[{ftype.upper()}]** {summary}")
                lines.append(f"   - Confidence: {self._format_confidence(confidence)}")
                lines.append("")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def _main_insights(self, data: ReportData) -> str:
        """Extract main insights from all perspectives."""
        lines = ["## Main Insights", ""]

        all_insights = []
        for perspective in data.perspectives:
            ptype = perspective.get("perspective_type", "").replace("_", " ").title()
            insights = perspective.get("key_insights", [])
            for insight in insights[:2]:  # Top 2 from each perspective
                all_insights.append((ptype, insight))

        if not all_insights:
            lines.append("*No perspective analyses available.*")
        else:
            for ptype, insight in all_insights[:8]:  # Limit to 8 total
                lines.append(f"- **{ptype}:** {insight}")

        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def _recommendations(self, data: ReportData) -> str:
        """Aggregate recommendations from perspectives."""
        lines = ["## Recommendations", ""]

        all_recs = []
        for perspective in data.perspectives:
            recs = perspective.get("recommendations", [])
            all_recs.extend(recs)

        # Deduplicate and limit
        seen = set()
        unique_recs = []
        for rec in all_recs:
            if rec.lower() not in seen:
                seen.add(rec.lower())
                unique_recs.append(rec)

        if not unique_recs:
            lines.append("*No specific recommendations generated.*")
        else:
            for rec in unique_recs[:5]:
                lines.append(f"- {rec}")

        # Add warnings if any
        all_warnings = []
        for perspective in data.perspectives:
            warnings = perspective.get("warnings", [])
            all_warnings.extend(warnings)

        if all_warnings:
            lines.append("")
            lines.append("### Cautions")
            for warning in all_warnings[:3]:
                lines.append(f"- {warning}")

        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def _top_sources(self, data: ReportData) -> str:
        """List top sources by credibility."""
        lines = ["## Top Sources", ""]

        top_sources = data.sources_by_credibility[:5]

        if not top_sources:
            lines.append("*No sources available.*")
        else:
            for source in top_sources:
                title = source.get("title", source.get("url", "Unknown"))
                url = source.get("url", "#")
                credibility = source.get("credibility_score", 0)
                lines.append(f"- [{title}]({url}) - {self._format_confidence(credibility)}")

        lines.append("")
        return "\n".join(lines)
