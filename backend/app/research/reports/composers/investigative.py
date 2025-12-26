"""Investigative report composers."""

from typing import List, Optional
from datetime import datetime

from .base import BaseComposer
from ..schemas import ReportData, ReportVariant


class InvestigativeComposer(BaseComposer):
    """
    Composer for investigative research report variants.

    Supports:
    - timeline_report: Chronological event narrative
    - actor_dossier: Entity profiles and relationships
    - evidence_brief: Evidence chain summary
    """

    def compose(
        self,
        data: ReportData,
        variant: ReportVariant,
        title: Optional[str] = None,
        include_sections: Optional[List[str]] = None,
    ) -> str:
        """Generate investigative report variant."""
        if variant == ReportVariant.TIMELINE_REPORT:
            return self._timeline_report(data, title)
        elif variant == ReportVariant.ACTOR_DOSSIER:
            return self._actor_dossier(data, title)
        elif variant == ReportVariant.EVIDENCE_BRIEF:
            return self._evidence_brief(data, title)
        else:
            raise ValueError(f"Unsupported variant for investigative: {variant}")

    def _timeline_report(self, data: ReportData, title: Optional[str]) -> str:
        """Generate timeline-focused report."""
        report_title = title or f"Timeline: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        # Extract events
        events = [f for f in data.findings if f.get("finding_type") == "event"]

        sections.append("## Chronological Timeline\n")

        if not events:
            sections.append("*No specific events were identified in the research.*\n")
        else:
            # Sort by event_date if available, otherwise by creation
            sorted_events = sorted(
                events,
                key=lambda e: e.get("event_date") or e.get("created_at", ""),
            )

            current_year = None
            for event in sorted_events:
                event_date = event.get("event_date", "")
                content = event.get("content", "")
                summary = event.get("summary", "")
                confidence = event.get("confidence_score", 0.5)

                # Year header
                if event_date:
                    try:
                        year = str(event_date)[:4]
                        if year != current_year:
                            current_year = year
                            sections.append(f"\n### {year}\n")
                    except Exception:
                        pass

                date_str = event_date or "Date Unknown"
                sections.append(f"**{date_str}** - {summary or content[:100]}")
                sections.append(f"> {content}")
                sections.append(f"*Confidence: {self._format_confidence(confidence)}*")
                sections.append("")

        # Related actors
        sections.append(self._section_divider())
        sections.append("## Key Actors Involved\n")

        actors = [f for f in data.findings if f.get("finding_type") == "actor"]
        if actors:
            for actor in actors[:10]:
                sections.append(f"- **{actor.get('summary', actor.get('content', '')[:50])}**")
        else:
            sections.append("*No specific actors identified.*")

        sections.append("")
        return "\n".join(sections)

    def _actor_dossier(self, data: ReportData, title: Optional[str]) -> str:
        """Generate actor-focused dossier report."""
        report_title = title or f"Actor Dossier: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        # Extract actors
        actors = [f for f in data.findings if f.get("finding_type") == "actor"]

        sections.append("## Identified Actors\n")

        if not actors:
            sections.append("*No specific actors were identified in the research.*\n")
        else:
            for i, actor in enumerate(actors, 1):
                content = actor.get("content", "")
                summary = actor.get("summary", "")
                confidence = actor.get("confidence_score", 0.5)
                extracted = actor.get("extracted_data", {})

                sections.append(f"### Actor {i}: {summary or 'Unknown'}")
                sections.append("")
                sections.append(content)
                sections.append("")

                # If extracted data has structured info
                if extracted:
                    if extracted.get("role"):
                        sections.append(f"**Role:** {extracted['role']}")
                    if extracted.get("affiliations"):
                        sections.append(f"**Affiliations:** {', '.join(extracted['affiliations'])}")
                    if extracted.get("aliases"):
                        sections.append(f"**Also known as:** {', '.join(extracted['aliases'])}")

                sections.append(f"*Confidence: {self._format_confidence(confidence)}*")
                sections.append("")

        # Relationships
        sections.append(self._section_divider())
        sections.append("## Relationships\n")

        relationships = [f for f in data.findings if f.get("finding_type") == "relationship"]
        if relationships:
            for rel in relationships[:15]:
                sections.append(f"- {rel.get('content', '')}")
                sections.append(f"  *Confidence: {self._format_confidence(rel.get('confidence_score', 0.5))}*")
                sections.append("")
        else:
            sections.append("*No specific relationships identified.*")

        sections.append("")
        return "\n".join(sections)

    def _evidence_brief(self, data: ReportData, title: Optional[str]) -> str:
        """Generate evidence-focused brief."""
        report_title = title or f"Evidence Brief: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        # Extract evidence
        evidence = [f for f in data.findings if f.get("finding_type") == "evidence"]
        facts = [f for f in data.findings if f.get("finding_type") == "fact"]

        sections.append("## Evidence Summary\n")
        sections.append(f"This brief compiles **{len(evidence)} evidence items** and "
                       f"**{len(facts)} facts** from **{len(data.sources)} sources**.\n")

        # Evidence items
        sections.append("### Direct Evidence\n")

        if not evidence:
            sections.append("*No direct evidence items were catalogued.*\n")
        else:
            for i, ev in enumerate(sorted(evidence, key=lambda e: e.get("confidence_score", 0), reverse=True), 1):
                sections.append(f"**E{i}.** {ev.get('content', '')}")
                sections.append(f"- Confidence: {self._format_confidence(ev.get('confidence_score', 0.5))}")

                extracted = ev.get("extracted_data", {})
                if extracted.get("source"):
                    sections.append(f"- Source: {extracted['source']}")
                if extracted.get("type"):
                    sections.append(f"- Type: {extracted['type']}")
                sections.append("")

        # Supporting facts
        sections.append("### Corroborating Facts\n")

        if facts:
            for fact in sorted(facts, key=lambda f: f.get("confidence_score", 0), reverse=True)[:10]:
                sections.append(f"- {fact.get('content', '')}")
                sections.append(f"  *({self._format_confidence(fact.get('confidence_score', 0.5))})*")
                sections.append("")
        else:
            sections.append("*No corroborating facts identified.*")

        # Gaps
        sections.append(self._section_divider())
        sections.append("## Evidence Gaps\n")

        gaps = [f for f in data.findings if f.get("finding_type") == "gap"]
        if gaps:
            for gap in gaps:
                sections.append(f"- {gap.get('content', '')}")
        else:
            sections.append("*No significant evidence gaps identified.*")

        sections.append("")
        return "\n".join(sections)
