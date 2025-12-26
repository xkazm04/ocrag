"""Base composer for markdown report generation."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from ..schemas import ReportData, ReportVariant


class BaseComposer(ABC):
    """
    Abstract base class for markdown composers.

    Each composer transforms ReportData into structured markdown
    for a specific report variant.
    """

    @abstractmethod
    def compose(
        self,
        data: ReportData,
        variant: ReportVariant,
        title: Optional[str] = None,
        include_sections: Optional[List[str]] = None,
    ) -> str:
        """
        Compose markdown content from report data.

        Args:
            data: Aggregated research data
            variant: Specific report variant to generate
            title: Optional custom title
            include_sections: Optional filter for sections to include

        Returns:
            Formatted markdown string
        """
        pass

    def _header(self, title: str, data: ReportData) -> str:
        """Generate standard report header."""
        return f"""# {title}

**Research Query:** {data.session_query}

**Template:** {data.template_type.title()} Research

**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}

**Status:** {data.status.title()}

---

"""

    def _format_confidence(self, score: float) -> str:
        """Format confidence score as visual indicator."""
        if score >= 0.8:
            return f"High ({score:.0%})"
        elif score >= 0.6:
            return f"Medium ({score:.0%})"
        else:
            return f"Low ({score:.0%})"

    def _format_finding(self, finding: dict, include_details: bool = True) -> str:
        """Format a single finding as markdown."""
        ftype = finding.get("finding_type", "fact").upper()
        content = finding.get("content", "")
        summary = finding.get("summary", "")
        confidence = finding.get("confidence_score", 0.5)

        lines = [f"### [{ftype}] {summary or content[:80]}"]

        if include_details:
            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append(f"*Confidence: {self._format_confidence(confidence)}*")

            temporal = finding.get("temporal_context")
            if temporal:
                lines.append(f"*Temporal Context: {temporal.title()}*")

        return "\n".join(lines)

    def _format_source(self, source: dict, include_snippet: bool = True) -> str:
        """Format a single source as markdown."""
        title = source.get("title", source.get("url", "Unknown"))
        url = source.get("url", "#")
        domain = source.get("domain", "")
        credibility = source.get("credibility_score", 0)
        source_type = source.get("source_type", "unknown")

        lines = [f"- [{title}]({url})"]
        lines.append(f"  - Domain: {domain} | Type: {source_type.replace('_', ' ').title()}")
        lines.append(f"  - Credibility: {self._format_confidence(credibility)}")

        if include_snippet:
            snippet = source.get("snippet", "")
            if snippet:
                lines.append(f"  - *\"{snippet[:200]}...\"*")

        return "\n".join(lines)

    def _format_perspective(self, perspective: dict) -> str:
        """Format a perspective analysis as markdown."""
        ptype = perspective.get("perspective_type", "unknown").replace("_", " ").title()
        analysis = perspective.get("analysis_text", "")
        insights = perspective.get("key_insights", [])
        recommendations = perspective.get("recommendations", [])
        warnings = perspective.get("warnings", [])
        confidence = perspective.get("confidence", 0.5)

        lines = [f"### {ptype} Perspective"]
        lines.append("")
        lines.append(analysis)
        lines.append("")

        if insights:
            lines.append("**Key Insights:**")
            for insight in insights:
                lines.append(f"- {insight}")
            lines.append("")

        if recommendations:
            lines.append("**Recommendations:**")
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        if warnings:
            lines.append("**Warnings:**")
            for warning in warnings:
                lines.append(f"- {warning}")
            lines.append("")

        lines.append(f"*Confidence: {self._format_confidence(confidence)}*")

        return "\n".join(lines)

    def _table_of_contents(self, sections: List[str]) -> str:
        """Generate table of contents."""
        lines = ["## Table of Contents", ""]
        for i, section in enumerate(sections, 1):
            anchor = section.lower().replace(" ", "-")
            lines.append(f"{i}. [{section}](#{anchor})")
        lines.append("")
        return "\n".join(lines)

    def _section_divider(self) -> str:
        """Return a section divider."""
        return "\n---\n\n"
