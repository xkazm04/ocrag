"""Full report composer."""

from typing import List, Optional

from .base import BaseComposer
from ..schemas import ReportData, ReportVariant


class FullReportComposer(BaseComposer):
    """
    Composer for comprehensive full reports.

    Generates a complete research document with all sections:
    - Executive summary
    - All findings by category
    - All perspective analyses
    - Complete source bibliography
    - Methodology notes
    """

    def compose(
        self,
        data: ReportData,
        variant: ReportVariant,
        title: Optional[str] = None,
        include_sections: Optional[List[str]] = None,
    ) -> str:
        """Generate full report markdown."""
        report_title = title or f"Research Report: {data.session_query[:60]}"

        # Handle special variants
        if variant == ReportVariant.FINDINGS_ONLY:
            return self._findings_only(data, report_title)
        elif variant == ReportVariant.SOURCE_BIBLIOGRAPHY:
            return self._source_bibliography(data, report_title)

        # Full report sections
        all_sections = [
            "Executive Summary",
            "Findings",
            "Perspective Analyses",
            "Sources",
            "Methodology",
        ]

        # Filter sections if requested
        if include_sections:
            all_sections = [s for s in all_sections if s.lower() in [x.lower() for x in include_sections]]

        sections = []

        # Header
        sections.append(self._header(report_title, data))

        # Table of contents
        sections.append(self._table_of_contents(all_sections))

        # Generate each section
        for section_name in all_sections:
            if section_name == "Executive Summary":
                sections.append(self._executive_summary(data))
            elif section_name == "Findings":
                sections.append(self._findings_section(data))
            elif section_name == "Perspective Analyses":
                sections.append(self._perspectives_section(data))
            elif section_name == "Sources":
                sections.append(self._sources_section(data))
            elif section_name == "Methodology":
                sections.append(self._methodology_section(data))

        return "\n".join(sections)

    def _executive_summary(self, data: ReportData) -> str:
        """Generate executive summary section."""
        lines = ["## Executive Summary", ""]

        # Overview paragraph
        lines.append(f"This research analyzed **{data.session_query}** using the "
                    f"{data.template_type.replace('_', ' ').title()} research methodology. "
                    f"The investigation yielded **{len(data.findings)} findings** from "
                    f"**{len(data.sources)} sources**, analyzed through "
                    f"**{len(data.perspectives)} expert perspectives**.")
        lines.append("")

        # Key stats
        high_conf = len(data.high_confidence_findings)
        lines.append(f"- **High confidence findings:** {high_conf}")
        lines.append(f"- **Source credibility average:** {self._avg_credibility(data):.0%}")

        # Top finding
        if data.findings:
            top = max(data.findings, key=lambda f: f.get("confidence_score", 0))
            lines.append("")
            lines.append(f"**Top Finding:** {top.get('summary') or top.get('content', '')[:150]}")

        lines.append("")
        lines.append(self._section_divider())
        return "\n".join(lines)

    def _findings_section(self, data: ReportData) -> str:
        """Generate findings section grouped by type."""
        lines = ["## Findings", ""]

        findings_by_type = data.findings_by_type

        if not findings_by_type:
            lines.append("*No findings were extracted from the research.*")
            lines.append("")
            return "\n".join(lines)

        # Order by finding type importance
        type_order = ["fact", "event", "actor", "relationship", "pattern", "evidence", "claim", "gap"]

        for ftype in type_order:
            if ftype not in findings_by_type:
                continue

            type_findings = findings_by_type[ftype]
            lines.append(f"### {ftype.title()}s ({len(type_findings)})")
            lines.append("")

            # Sort by confidence
            sorted_findings = sorted(
                type_findings,
                key=lambda f: f.get("confidence_score", 0),
                reverse=True
            )

            for finding in sorted_findings:
                lines.append(self._format_finding_full(finding))
                lines.append("")

        lines.append(self._section_divider())
        return "\n".join(lines)

    def _format_finding_full(self, finding: dict) -> str:
        """Format a finding with full details."""
        content = finding.get("content", "")
        summary = finding.get("summary", "")
        confidence = finding.get("confidence_score", 0.5)
        temporal = finding.get("temporal_context", "")
        event_date = finding.get("event_date", "")

        lines = []

        if summary:
            lines.append(f"**{summary}**")
            lines.append("")

        lines.append(content)
        lines.append("")

        meta = [f"Confidence: {self._format_confidence(confidence)}"]
        if temporal:
            meta.append(f"Temporal: {temporal.title()}")
        if event_date:
            meta.append(f"Date: {event_date}")

        lines.append(f"*{' | '.join(meta)}*")

        return "\n".join(lines)

    def _perspectives_section(self, data: ReportData) -> str:
        """Generate perspectives section."""
        lines = ["## Perspective Analyses", ""]

        if not data.perspectives:
            lines.append("*No perspective analyses were conducted.*")
            lines.append("")
            return "\n".join(lines)

        for perspective in data.perspectives:
            lines.append(self._format_perspective(perspective))
            lines.append("")

        lines.append(self._section_divider())
        return "\n".join(lines)

    def _sources_section(self, data: ReportData) -> str:
        """Generate sources section."""
        lines = ["## Sources", ""]

        if not data.sources:
            lines.append("*No sources were collected.*")
            lines.append("")
            return "\n".join(lines)

        # Group by source type
        by_type = {}
        for source in data.sources:
            stype = source.get("source_type", "unknown")
            if stype not in by_type:
                by_type[stype] = []
            by_type[stype].append(source)

        for stype, sources in sorted(by_type.items()):
            lines.append(f"### {stype.replace('_', ' ').title()} ({len(sources)})")
            lines.append("")

            for source in sorted(sources, key=lambda s: s.get("credibility_score", 0), reverse=True):
                lines.append(self._format_source(source))
                lines.append("")

        lines.append(self._section_divider())
        return "\n".join(lines)

    def _methodology_section(self, data: ReportData) -> str:
        """Generate methodology section."""
        params = data.parameters
        perspectives_used = [p.get("perspective_type", "") for p in data.perspectives]

        lines = ["## Methodology", ""]

        lines.append(f"**Template:** {data.template_type.replace('_', ' ').title()} Research")
        lines.append("")
        lines.append(f"**Granularity:** {params.get('granularity', 'standard').title()}")
        lines.append("")
        lines.append(f"**Max Searches:** {params.get('max_searches', 'default')}")
        lines.append("")

        if perspectives_used:
            lines.append("**Perspectives Applied:**")
            for p in perspectives_used:
                lines.append(f"- {p.replace('_', ' ').title()}")
            lines.append("")

        lines.append(f"**Research Started:** {data.created_at.strftime('%Y-%m-%d %H:%M')}")
        if data.completed_at:
            lines.append(f"**Research Completed:** {data.completed_at.strftime('%Y-%m-%d %H:%M')}")

        lines.append("")
        return "\n".join(lines)

    def _findings_only(self, data: ReportData, title: str) -> str:
        """Generate findings-only report."""
        sections = []
        sections.append(self._header(f"Findings: {title}", data))
        sections.append(self._findings_section(data))
        return "\n".join(sections)

    def _source_bibliography(self, data: ReportData, title: str) -> str:
        """Generate source bibliography report."""
        sections = []
        sections.append(self._header(f"Bibliography: {title}", data))
        sections.append(self._sources_section(data))
        return "\n".join(sections)

    def _avg_credibility(self, data: ReportData) -> float:
        """Calculate average source credibility."""
        if not data.sources:
            return 0.0
        scores = [s.get("credibility_score", 0) for s in data.sources]
        return sum(scores) / len(scores)
