"""Standalone test for report generation that avoids triggering external dependencies.

This test directly executes composer logic without going through the app module chain,
allowing testing without API keys configured.

Run with: python tests/research/test_report_standalone.py
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from enum import Enum

# Setup paths
_script_dir = Path(__file__).parent
_backend_dir = _script_dir.parent.parent
_results_dir = _script_dir / "results" / "reports"
sys.path.insert(0, str(_backend_dir))

# Ensure results directory exists
_results_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# INLINE SCHEMAS (avoiding app imports)
# =============================================================================

class ReportVariant(str, Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    FULL_REPORT = "full_report"
    FINDINGS_ONLY = "findings_only"
    SOURCE_BIBLIOGRAPHY = "source_bibliography"
    TIMELINE_REPORT = "timeline_report"
    ACTOR_DOSSIER = "actor_dossier"
    EVIDENCE_BRIEF = "evidence_brief"
    COMPETITIVE_MATRIX = "competitive_matrix"
    SWOT_ANALYSIS = "swot_analysis"
    BATTLECARD = "battlecard"
    INVESTMENT_THESIS = "investment_thesis"
    EARNINGS_SUMMARY = "earnings_summary"
    RISK_ASSESSMENT = "risk_assessment"
    LEGAL_BRIEF = "legal_brief"
    CASE_DIGEST = "case_digest"
    COMPLIANCE_CHECKLIST = "compliance_checklist"


class ReportData:
    """Minimal ReportData for testing."""
    def __init__(self, **kwargs):
        self.session_id = kwargs.get("session_id", uuid4())
        self.session_title = kwargs.get("session_title", "")
        self.session_query = kwargs.get("session_query", "")
        self.template_type = kwargs.get("template_type", "general")
        self.status = kwargs.get("status", "completed")
        self.parameters = kwargs.get("parameters", {})
        self.created_at = kwargs.get("created_at", datetime.now())
        self.completed_at = kwargs.get("completed_at", datetime.now())
        self.findings = kwargs.get("findings", [])
        self.perspectives = kwargs.get("perspectives", [])
        self.sources = kwargs.get("sources", [])
        self.claims = kwargs.get("claims", [])

    @property
    def high_confidence_findings(self) -> List[Dict]:
        return [f for f in self.findings if f.get("confidence_score", 0) >= 0.7]

    @property
    def findings_by_type(self) -> Dict[str, List[Dict]]:
        grouped = {}
        for f in self.findings:
            ftype = f.get("finding_type", "unknown")
            if ftype not in grouped:
                grouped[ftype] = []
            grouped[ftype].append(f)
        return grouped

    @property
    def sources_by_credibility(self) -> List[Dict]:
        return sorted(self.sources, key=lambda s: s.get("credibility_score", 0), reverse=True)


# =============================================================================
# INLINE BASE COMPOSER
# =============================================================================

class BaseComposer(ABC):
    @abstractmethod
    def compose(self, data: ReportData, variant: ReportVariant, title: Optional[str] = None, include_sections: Optional[List[str]] = None) -> str:
        pass

    def _header(self, title: str, data: ReportData) -> str:
        return f"""# {title}

**Research Query:** {data.session_query}

**Template:** {data.template_type.title()} Research

**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}

**Status:** {data.status.title()}

---

"""

    def _format_confidence(self, score: float) -> str:
        if score >= 0.8:
            return f"High ({score:.0%})"
        elif score >= 0.6:
            return f"Medium ({score:.0%})"
        else:
            return f"Low ({score:.0%})"

    def _format_finding(self, finding: dict, include_details: bool = True) -> str:
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
        return "\n".join(lines)

    def _format_source(self, source: dict, include_snippet: bool = True) -> str:
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
        ptype = perspective.get("perspective_type", "unknown").replace("_", " ").title()
        analysis = perspective.get("analysis_text", "")
        insights = perspective.get("key_insights", [])
        recommendations = perspective.get("recommendations", [])
        warnings = perspective.get("warnings", [])
        confidence = perspective.get("confidence", 0.5)

        lines = [f"### {ptype} Perspective", "", analysis, ""]
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
        lines = ["## Table of Contents", ""]
        for i, section in enumerate(sections, 1):
            anchor = section.lower().replace(" ", "-")
            lines.append(f"{i}. [{section}](#{anchor})")
        lines.append("")
        return "\n".join(lines)

    def _section_divider(self) -> str:
        return "\n---\n\n"


# =============================================================================
# COMPOSER IMPLEMENTATIONS (Copied from source files)
# =============================================================================

class ExecutiveSummaryComposer(BaseComposer):
    def compose(self, data: ReportData, variant: ReportVariant, title: Optional[str] = None, include_sections: Optional[List[str]] = None) -> str:
        report_title = title or f"Executive Summary: {data.session_query[:60]}"
        sections = []
        sections.append(self._header(report_title, data))
        sections.append(self._quick_stats(data))
        sections.append(self._key_findings(data))
        sections.append(self._main_insights(data))
        sections.append(self._recommendations(data))
        sections.append(self._top_sources(data))
        return "\n".join(sections)

    def _quick_stats(self, data: ReportData) -> str:
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
        lines = ["## Key Findings", ""]
        top_findings = sorted(data.findings, key=lambda f: f.get("confidence_score", 0), reverse=True)[:5]
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
        lines = ["## Main Insights", ""]
        all_insights = []
        for perspective in data.perspectives:
            ptype = perspective.get("perspective_type", "").replace("_", " ").title()
            for insight in perspective.get("key_insights", [])[:2]:
                all_insights.append((ptype, insight))
        if not all_insights:
            lines.append("*No perspective analyses available.*")
        else:
            for ptype, insight in all_insights[:8]:
                lines.append(f"- **{ptype}:** {insight}")
        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def _recommendations(self, data: ReportData) -> str:
        lines = ["## Recommendations", ""]
        all_recs = []
        for perspective in data.perspectives:
            all_recs.extend(perspective.get("recommendations", []))
        seen = set()
        unique_recs = [r for r in all_recs if not (r.lower() in seen or seen.add(r.lower()))]
        if not unique_recs:
            lines.append("*No specific recommendations generated.*")
        else:
            for rec in unique_recs[:5]:
                lines.append(f"- {rec}")
        all_warnings = [w for p in data.perspectives for w in p.get("warnings", [])]
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


class CompetitiveComposer(BaseComposer):
    def compose(self, data: ReportData, variant: ReportVariant, title: Optional[str] = None, include_sections: Optional[List[str]] = None) -> str:
        if variant == ReportVariant.COMPETITIVE_MATRIX:
            return self._competitive_matrix(data, title)
        elif variant == ReportVariant.SWOT_ANALYSIS:
            return self._swot_analysis(data, title)
        elif variant == ReportVariant.BATTLECARD:
            return self._battlecard(data, title)
        else:
            raise ValueError(f"Unsupported variant: {variant}")

    def _competitive_matrix(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Competitive Matrix: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        competitors = [f for f in data.findings if f.get("finding_type") == "actor"]
        facts = [f for f in data.findings if f.get("finding_type") == "fact"]
        sections.append("## Competitive Landscape\n")
        if not competitors:
            sections.append("*No specific competitors identified. Showing key market findings.*\n")
            for fact in facts[:10]:
                sections.append(f"- {fact.get('content', '')}")
            sections.append("")
        else:
            sections.append("| Competitor | Position | Key Differentiator | Confidence |")
            sections.append("|------------|----------|-------------------|------------|")
            for comp in competitors[:10]:
                name = comp.get("summary", "Unknown")[:30]
                extracted = comp.get("extracted_data", {})
                position = extracted.get("market_position", "Unknown")
                diff = extracted.get("differentiators", [comp.get("content", "")[:50]])
                if isinstance(diff, list):
                    diff = diff[0] if diff else ""
                confidence = comp.get("confidence_score", 0.5)
                sections.append(f"| {name} | {position} | {str(diff)[:40]} | {confidence:.0%} |")
            sections.append("")
        sections.append("## Market Insights\n")
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
        return "\n".join(sections)

    def _swot_analysis(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"SWOT Analysis: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        sections.append("## SWOT Analysis\n")
        all_insights = [i for p in data.perspectives for i in p.get("key_insights", [])]
        sections.append(self._categorize_swot(all_insights))
        sections.append(self._section_divider())
        sections.append("## Strategic Recommendations\n")
        all_recs = [r for p in data.perspectives for r in p.get("recommendations", [])]
        for rec in all_recs[:8]:
            sections.append(f"- {rec}")
        if not all_recs:
            sections.append("*No specific recommendations generated.*")
        sections.append("")
        return "\n".join(sections)

    def _categorize_swot(self, insights: List[str]) -> str:
        lines = []
        strengths, weaknesses, opportunities, threats = [], [], [], []
        strength_words = ["strong", "advantage", "leader", "best", "superior"]
        weakness_words = ["weak", "lacking", "behind", "limited", "poor"]
        opportunity_words = ["opportunity", "potential", "growth", "expand", "market"]
        threat_words = ["threat", "risk", "competitor", "challenge", "decline"]
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
                opportunities.append(insight)
        for title, items in [("Strengths", strengths), ("Weaknesses", weaknesses), ("Opportunities", opportunities), ("Threats", threats)]:
            lines.append(f"### {title}")
            for item in items or ["*Analysis pending*"]:
                lines.append(f"- {item}")
            lines.append("")
        return "\n".join(lines)

    def _battlecard(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Battlecard: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        sections.append("## Quick Reference Battlecard\n")
        sections.append(f"**Subject:** {data.session_query}\n")
        sections.append("### Key Differentiators\n")
        patterns = [f for f in data.findings if f.get("finding_type") == "pattern"]
        for p in patterns[:4]:
            sections.append(f"- {p.get('summary', p.get('content', '')[:80])}")
        sections.append("")
        sections.append("### Competitive Weaknesses\n")
        gaps = [f for f in data.findings if f.get("finding_type") == "gap"]
        for gap in gaps[:3]:
            sections.append(f"- {gap.get('content', '')[:100]}")
        if not gaps:
            sections.append("- *Further competitive analysis needed*")
        sections.append("")
        sections.append("### Suggested Talk Track\n")
        all_recs = [r for p in data.perspectives for r in p.get("recommendations", [])]
        for i, rec in enumerate(all_recs[:3], 1):
            sections.append(f"{i}. {rec}")
        if not all_recs:
            sections.append("1. *Customize based on prospect needs*")
        sections.append("")
        return "\n".join(sections)


class InvestigativeComposer(BaseComposer):
    def compose(self, data: ReportData, variant: ReportVariant, title: Optional[str] = None, include_sections: Optional[List[str]] = None) -> str:
        if variant == ReportVariant.TIMELINE_REPORT:
            return self._timeline_report(data, title)
        elif variant == ReportVariant.ACTOR_DOSSIER:
            return self._actor_dossier(data, title)
        elif variant == ReportVariant.EVIDENCE_BRIEF:
            return self._evidence_brief(data, title)
        else:
            raise ValueError(f"Unsupported variant: {variant}")

    def _timeline_report(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Timeline: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        events = [f for f in data.findings if f.get("finding_type") == "event"]
        sections.append("## Chronological Timeline\n")
        if not events:
            sections.append("*No specific events were identified.*\n")
        else:
            sorted_events = sorted(events, key=lambda e: e.get("event_date") or e.get("created_at", ""))
            current_year = None
            for event in sorted_events:
                event_date = event.get("event_date", "")
                if event_date:
                    year = str(event_date)[:4]
                    if year != current_year:
                        current_year = year
                        sections.append(f"\n### {year}\n")
                date_str = event_date or "Date Unknown"
                sections.append(f"**{date_str}** - {event.get('summary', event.get('content', '')[:100])}")
                sections.append(f"> {event.get('content', '')}")
                sections.append(f"*Confidence: {self._format_confidence(event.get('confidence_score', 0.5))}*")
                sections.append("")
        sections.append(self._section_divider())
        sections.append("## Key Actors Involved\n")
        actors = [f for f in data.findings if f.get("finding_type") == "actor"]
        for actor in actors[:10]:
            sections.append(f"- **{actor.get('summary', actor.get('content', '')[:50])}**")
        if not actors:
            sections.append("*No specific actors identified.*")
        sections.append("")
        return "\n".join(sections)

    def _actor_dossier(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Actor Dossier: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        actors = [f for f in data.findings if f.get("finding_type") == "actor"]
        sections.append("## Identified Actors\n")
        if not actors:
            sections.append("*No specific actors were identified.*\n")
        else:
            for i, actor in enumerate(actors, 1):
                summary = actor.get("summary", "Unknown")
                content = actor.get("content", "")
                extracted = actor.get("extracted_data", {})
                sections.append(f"### Actor {i}: {summary}")
                sections.append("")
                sections.append(content)
                sections.append("")
                if extracted.get("role"):
                    sections.append(f"**Role:** {extracted['role']}")
                if extracted.get("affiliations"):
                    sections.append(f"**Affiliations:** {', '.join(extracted['affiliations'])}")
                if extracted.get("aliases"):
                    sections.append(f"**Also known as:** {', '.join(extracted['aliases'])}")
                sections.append(f"*Confidence: {self._format_confidence(actor.get('confidence_score', 0.5))}*")
                sections.append("")
        sections.append(self._section_divider())
        sections.append("## Relationships\n")
        relationships = [f for f in data.findings if f.get("finding_type") == "relationship"]
        for rel in relationships[:15]:
            sections.append(f"- {rel.get('content', '')}")
        if not relationships:
            sections.append("*No specific relationships identified.*")
        sections.append("")
        return "\n".join(sections)

    def _evidence_brief(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Evidence Brief: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        evidence = [f for f in data.findings if f.get("finding_type") == "evidence"]
        facts = [f for f in data.findings if f.get("finding_type") == "fact"]
        sections.append("## Evidence Summary\n")
        sections.append(f"This brief compiles **{len(evidence)} evidence items** and **{len(facts)} facts** from **{len(data.sources)} sources**.\n")
        sections.append("### Direct Evidence\n")
        if not evidence:
            sections.append("*No direct evidence items were catalogued.*\n")
        else:
            for i, ev in enumerate(sorted(evidence, key=lambda e: e.get("confidence_score", 0), reverse=True), 1):
                sections.append(f"**E{i}.** {ev.get('content', '')}")
                sections.append(f"- Confidence: {self._format_confidence(ev.get('confidence_score', 0.5))}")
                sections.append("")
        sections.append("### Corroborating Facts\n")
        for fact in sorted(facts, key=lambda f: f.get("confidence_score", 0), reverse=True)[:10]:
            sections.append(f"- {fact.get('content', '')}")
        if not facts:
            sections.append("*No corroborating facts identified.*")
        sections.append("")
        sections.append(self._section_divider())
        sections.append("## Evidence Gaps\n")
        gaps = [f for f in data.findings if f.get("finding_type") == "gap"]
        for gap in gaps:
            sections.append(f"- {gap.get('content', '')}")
        if not gaps:
            sections.append("*No significant evidence gaps identified.*")
        sections.append("")
        return "\n".join(sections)


class FinancialComposer(BaseComposer):
    def compose(self, data: ReportData, variant: ReportVariant, title: Optional[str] = None, include_sections: Optional[List[str]] = None) -> str:
        if variant == ReportVariant.INVESTMENT_THESIS:
            return self._investment_thesis(data, title)
        elif variant == ReportVariant.EARNINGS_SUMMARY:
            return self._earnings_summary(data, title)
        elif variant == ReportVariant.RISK_ASSESSMENT:
            return self._risk_assessment(data, title)
        else:
            raise ValueError(f"Unsupported variant: {variant}")

    def _investment_thesis(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Investment Thesis: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        sections.append("## Investment Overview\n")
        sections.append(f"**Subject:** {data.session_query}\n")
        inv_perspective = next((p for p in data.perspectives if "investment" in p.get("perspective_type", "").lower() or "valuation" in p.get("perspective_type", "").lower()), None)
        if inv_perspective:
            sections.append(inv_perspective.get("analysis_text", ""))
            sections.append("")
        sections.append(self._section_divider())
        sections.append("## Bull Case\n")
        bullish = self._filter_sentiment(data.findings, positive=True)
        for f in bullish[:5]:
            sections.append(f"- **{f.get('summary', f.get('content', '')[:80])}**")
            sections.append(f"  - *Confidence: {self._format_confidence(f.get('confidence_score', 0.5))}*")
        if not bullish:
            sections.append("*No strong bullish indicators identified.*")
        sections.append("")
        sections.append(self._section_divider())
        sections.append("## Bear Case\n")
        bearish = self._filter_sentiment(data.findings, positive=False)
        for f in bearish[:5]:
            sections.append(f"- **{f.get('summary', f.get('content', '')[:80])}**")
        if not bearish:
            sections.append("*No strong bearish indicators identified.*")
        sections.append("")
        sections.append(self._section_divider())
        sections.append("## Key Metrics\n")
        metrics = self._extract_metrics(data)
        if metrics:
            sections.append("| Metric | Value | Context |")
            sections.append("|--------|-------|---------|")
            for m in metrics[:10]:
                sections.append(f"| {m['name']} | {m['value']} | {m['context']} |")
        sections.append("")
        return "\n".join(sections)

    def _earnings_summary(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Earnings Summary: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        sections.append("## Earnings Highlights\n")
        events = [f for f in data.findings if f.get("finding_type") == "event"]
        if events:
            sections.append("### Recent Events\n")
            for event in events[:5]:
                sections.append(f"- **{event.get('event_date', 'Recent')}**: {event.get('content', '')[:150]}")
            sections.append("")
        sections.append("### Financial Metrics\n")
        metrics = self._extract_metrics(data)
        if metrics:
            sections.append("| Metric | Value |")
            sections.append("|--------|-------|")
            for m in metrics[:8]:
                sections.append(f"| {m['name']} | {m['value']} |")
        sections.append("")
        sections.append(self._section_divider())
        sections.append("## Guidance & Outlook\n")
        patterns = [f for f in data.findings if f.get("finding_type") == "pattern"]
        for p in patterns[:3]:
            sections.append(f"**{p.get('summary', 'Pattern')}**: {p.get('content', '')}")
            sections.append("")
        if not patterns:
            sections.append("*No forward guidance identified.*")
        sections.append("")
        return "\n".join(sections)

    def _risk_assessment(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Risk Assessment: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        sections.append("## Risk Overview\n")
        risk_perspective = next((p for p in data.perspectives if "risk" in p.get("perspective_type", "").lower()), None)
        if risk_perspective:
            sections.append(risk_perspective.get("analysis_text", ""))
            sections.append("")
        sections.append(self._section_divider())
        sections.append("## Identified Risks\n")
        sections.append("### High Priority\n")
        warnings = [w for p in data.perspectives for w in p.get("warnings", [])]
        for w in warnings[:5]:
            sections.append(f"- **{w}**")
        if not warnings:
            sections.append("*No high priority risks identified.*")
        sections.append("")
        sections.append("### Information Gaps\n")
        gaps = [f for f in data.findings if f.get("finding_type") == "gap"]
        for g in gaps[:5]:
            sections.append(f"- {g.get('content', '')}")
        if not gaps:
            sections.append("*No significant gaps identified.*")
        sections.append("")
        sections.append(self._section_divider())
        sections.append("## Risk Mitigation\n")
        all_recs = [r for p in data.perspectives for r in p.get("recommendations", [])]
        for rec in all_recs[:5]:
            sections.append(f"- {rec}")
        if not all_recs:
            sections.append("*Develop risk mitigation strategy.*")
        sections.append("")
        return "\n".join(sections)

    def _filter_sentiment(self, findings: list, positive: bool) -> list:
        positive_words = ["growth", "increase", "strong", "outperform", "beat", "profit", "gain"]
        negative_words = ["decline", "decrease", "weak", "underperform", "miss", "loss", "risk"]
        target = positive_words if positive else negative_words
        result = []
        for f in findings:
            content = (f.get("content", "") + f.get("summary", "")).lower()
            if any(w in content for w in target):
                result.append(f)
        return sorted(result, key=lambda x: x.get("confidence_score", 0), reverse=True)

    def _extract_metrics(self, data: ReportData) -> list:
        metrics = []
        for f in data.findings:
            extracted = f.get("extracted_data", {})
            if extracted.get("metrics"):
                for m in extracted["metrics"]:
                    if isinstance(m, dict):
                        metrics.append(m)
                    else:
                        metrics.append({"name": "Metric", "value": str(m), "context": f.get("summary", "")[:50]})
            content = f.get("content", "")
            numbers = re.findall(r'\$[\d,]+\.?\d*|\d+\.?\d*%|\d+\.?\d*[BMK]', content)
            for num in numbers[:2]:
                metrics.append({"name": f.get("finding_type", "value").title(), "value": num, "context": f.get("summary", "")[:50]})
        return metrics[:15]


class LegalComposer(BaseComposer):
    def compose(self, data: ReportData, variant: ReportVariant, title: Optional[str] = None, include_sections: Optional[List[str]] = None) -> str:
        if variant == ReportVariant.LEGAL_BRIEF:
            return self._legal_brief(data, title)
        elif variant == ReportVariant.CASE_DIGEST:
            return self._case_digest(data, title)
        elif variant == ReportVariant.COMPLIANCE_CHECKLIST:
            return self._compliance_checklist(data, title)
        else:
            raise ValueError(f"Unsupported variant: {variant}")

    def _legal_brief(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Legal Brief: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        sections.append("## I. Issue\n")
        sections.append(f"**Question Presented:** {data.session_query}\n")
        sections.append(self._section_divider())
        sections.append("## II. Rule\n")
        facts = [f for f in data.findings if f.get("finding_type") == "fact"]
        for f in facts[:5]:
            citation = f.get("extracted_data", {}).get("citation", "")
            sections.append(f"- {f.get('content', '')}")
            if citation:
                sections.append(f"  *{citation}*")
        sections.append("")
        sections.append(self._section_divider())
        sections.append("## III. Application\n")
        for p in data.perspectives:
            ptype = p.get("perspective_type", "").replace("_", " ").title()
            sections.append(f"### {ptype} Analysis\n")
            sections.append(p.get("analysis_text", ""))
            sections.append("")
            for insight in p.get("key_insights", [])[:4]:
                sections.append(f"- {insight}")
            sections.append("")
        sections.append(self._section_divider())
        sections.append("## IV. Conclusion\n")
        all_recs = [r for p in data.perspectives for r in p.get("recommendations", [])]
        for rec in all_recs[:5]:
            sections.append(f"- {rec}")
        if not all_recs:
            sections.append("*Further legal analysis required.*")
        sections.append("")
        sections.append(self._section_divider())
        sections.append("## Authorities Cited\n")
        for s in data.sources[:10]:
            sections.append(f"- [{s.get('title', s.get('url', ''))}]({s.get('url', '#')})")
        sections.append("")
        return "\n".join(sections)

    def _case_digest(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Case Digest: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        sections.append("## Case Overview\n")
        sections.append(f"**Research Focus:** {data.session_query}\n")
        sections.append("## Cases Analyzed\n")
        actors = [f for f in data.findings if f.get("finding_type") == "actor"]
        facts = [f for f in data.findings if f.get("finding_type") == "fact"]
        items = actors if actors else facts[:10]
        for i, item in enumerate(items, 1):
            sections.append(f"### Case Reference {i}: {item.get('summary', 'Case')[:50]}")
            sections.append("")
            sections.append(item.get("content", ""))
            sections.append(f"*Confidence: {self._format_confidence(item.get('confidence_score', 0.5))}*")
            sections.append("")
        if not items:
            sections.append("*No specific cases identified.*")
        sections.append(self._section_divider())
        sections.append("## Key Precedents\n")
        patterns = [f for f in data.findings if f.get("finding_type") == "pattern"]
        for p in patterns[:5]:
            sections.append(f"- **{p.get('summary', 'Precedent')}**: {p.get('content', '')[:200]}")
        if not patterns:
            sections.append("*No precedent patterns identified.*")
        sections.append("")
        return "\n".join(sections)

    def _compliance_checklist(self, data: ReportData, title: Optional[str]) -> str:
        report_title = title or f"Compliance Checklist: {data.session_query[:50]}"
        sections = [self._header(report_title, data)]
        sections.append("## Compliance Overview\n")
        sections.append(f"**Scope:** {data.session_query}\n")
        compliance_perspective = next((p for p in data.perspectives if "compliance" in p.get("perspective_type", "").lower()), None)
        if compliance_perspective:
            sections.append(compliance_perspective.get("analysis_text", ""))
            sections.append("")
        sections.append(self._section_divider())
        sections.append("## Requirements Checklist\n")
        facts = [f for f in data.findings if f.get("finding_type") == "fact"]
        if facts:
            sections.append("| # | Requirement | Priority | Status |")
            sections.append("|---|-------------|----------|--------|")
            for i, f in enumerate(facts[:15], 1):
                content = f.get("summary", f.get("content", ""))[:60]
                priority = "High" if f.get("confidence_score", 0) >= 0.8 else "Medium"
                sections.append(f"| {i} | {content} | {priority} | ⏳ Pending |")
            sections.append("")
        else:
            sections.append("*No specific requirements extracted.*")
        sections.append(self._section_divider())
        sections.append("## Compliance Gaps\n")
        gaps = [f for f in data.findings if f.get("finding_type") == "gap"]
        for g in gaps:
            sections.append(f"- {g.get('content', '')}")
        if not gaps:
            sections.append("*No significant gaps identified.*")
        sections.append("")
        sections.append(self._section_divider())
        sections.append("## Recommended Actions\n")
        all_recs = [r for p in data.perspectives for r in p.get("recommendations", [])]
        for i, rec in enumerate(all_recs[:8], 1):
            sections.append(f"{i}. {rec}")
        if not all_recs:
            sections.append("1. Review all requirements with legal counsel")
        sections.append("")
        return "\n".join(sections)


class FullReportComposer(BaseComposer):
    def compose(self, data: ReportData, variant: ReportVariant, title: Optional[str] = None, include_sections: Optional[List[str]] = None) -> str:
        report_title = title or f"Research Report: {data.session_query[:60]}"
        if variant == ReportVariant.FINDINGS_ONLY:
            return self._findings_only(data, report_title)
        elif variant == ReportVariant.SOURCE_BIBLIOGRAPHY:
            return self._source_bibliography(data, report_title)
        sections = [self._header(report_title, data)]
        sections.append(self._table_of_contents(["Executive Summary", "Findings", "Perspectives", "Sources"]))
        sections.append("## Executive Summary\n")
        sections.append(f"This research analyzed **{data.session_query}** using {data.template_type.title()} methodology. ")
        sections.append(f"The investigation yielded **{len(data.findings)} findings** from **{len(data.sources)} sources**, analyzed through **{len(data.perspectives)} perspectives**.\n")
        sections.append(f"- **High confidence findings:** {len(data.high_confidence_findings)}")
        sections.append("")
        if data.findings:
            top = max(data.findings, key=lambda f: f.get("confidence_score", 0))
            sections.append(f"**Top Finding:** {top.get('summary') or top.get('content', '')[:150]}")
        sections.append("")
        sections.append(self._section_divider())
        sections.append("## Findings\n")
        type_order = ["fact", "event", "actor", "relationship", "pattern", "evidence", "gap"]
        for ftype in type_order:
            type_findings = [f for f in data.findings if f.get("finding_type") == ftype]
            if type_findings:
                sections.append(f"### {ftype.title()}s ({len(type_findings)})\n")
                for f in sorted(type_findings, key=lambda x: x.get("confidence_score", 0), reverse=True):
                    sections.append(self._format_finding(f))
                    sections.append("")
        sections.append(self._section_divider())
        sections.append("## Perspective Analyses\n")
        for p in data.perspectives:
            sections.append(self._format_perspective(p))
            sections.append("")
        sections.append(self._section_divider())
        sections.append("## Sources\n")
        for s in data.sources_by_credibility:
            sections.append(self._format_source(s))
            sections.append("")
        return "\n".join(sections)

    def _findings_only(self, data: ReportData, title: str) -> str:
        sections = [self._header(f"Findings: {title}", data)]
        sections.append("## All Findings\n")
        for f in sorted(data.findings, key=lambda x: x.get("confidence_score", 0), reverse=True):
            sections.append(self._format_finding(f))
            sections.append("")
        return "\n".join(sections)

    def _source_bibliography(self, data: ReportData, title: str) -> str:
        sections = [self._header(f"Bibliography: {title}", data)]
        sections.append("## Sources\n")
        for s in data.sources_by_credibility:
            sections.append(self._format_source(s))
            sections.append("")
        return "\n".join(sections)


# =============================================================================
# COMPOSER REGISTRY
# =============================================================================

COMPOSER_REGISTRY = {
    "executive_summary": ExecutiveSummaryComposer,
    "full_report": FullReportComposer,
    "findings_only": FullReportComposer,
    "source_bibliography": FullReportComposer,
    "timeline_report": InvestigativeComposer,
    "actor_dossier": InvestigativeComposer,
    "evidence_brief": InvestigativeComposer,
    "competitive_matrix": CompetitiveComposer,
    "swot_analysis": CompetitiveComposer,
    "battlecard": CompetitiveComposer,
    "investment_thesis": FinancialComposer,
    "earnings_summary": FinancialComposer,
    "risk_assessment": FinancialComposer,
    "legal_brief": LegalComposer,
    "case_digest": LegalComposer,
    "compliance_checklist": LegalComposer,
}


# =============================================================================
# MOCK DATA (from previous file)
# =============================================================================

def create_investigative_mock_data():
    return {
        "session_title": "FTX Collapse Investigation",
        "session_query": "What led to the collapse of FTX and who were the key players involved?",
        "template_type": "investigative",
        "status": "completed",
        "parameters": {"max_searches": 15},
        "created_at": datetime.now() - timedelta(hours=2),
        "completed_at": datetime.now(),
        "findings": [
            {"finding_type": "event", "content": "On November 2, 2022, CoinDesk published an article revealing Alameda Research held significant FTT tokens.", "summary": "CoinDesk article exposes Alameda-FTX connection", "confidence_score": 0.95, "event_date": "2022-11-02"},
            {"finding_type": "event", "content": "Binance CEO CZ announced on November 6 that Binance would sell FTT holdings, triggering sell-off.", "summary": "Binance announces FTT sale", "confidence_score": 0.98, "event_date": "2022-11-06"},
            {"finding_type": "actor", "content": "Sam Bankman-Fried (SBF) was founder and CEO of FTX, known for effective altruism advocacy.", "summary": "Sam Bankman-Fried (SBF)", "confidence_score": 0.99, "extracted_data": {"role": "Founder & CEO of FTX", "affiliations": ["FTX", "Alameda Research"], "aliases": ["SBF"]}},
            {"finding_type": "actor", "content": "Caroline Ellison served as CEO of Alameda Research.", "summary": "Caroline Ellison", "confidence_score": 0.92, "extracted_data": {"role": "CEO of Alameda Research", "affiliations": ["Alameda Research"]}},
            {"finding_type": "relationship", "content": "FTX secretly transferred customer funds to Alameda Research to cover trading losses.", "summary": "FTX-Alameda fund transfer", "confidence_score": 0.88},
            {"finding_type": "fact", "content": "FTX customer deposits totaled approximately $16 billion, with $8-10 billion missing.", "summary": "Missing customer funds", "confidence_score": 0.85},
            {"finding_type": "evidence", "content": "Internal documents revealed FTX had a secret backdoor for transfers.", "summary": "Secret backdoor", "confidence_score": 0.82, "extracted_data": {"source": "Court filings", "type": "documentary"}},
            {"finding_type": "pattern", "content": "A pattern of regulatory arbitrage emerged, operating from Bahamas to avoid US regulations.", "summary": "Regulatory arbitrage pattern", "confidence_score": 0.78},
            {"finding_type": "gap", "content": "The exact timeline of when customer funds were first misappropriated remains unclear.", "confidence_score": 0.65}
        ],
        "perspectives": [
            {"perspective_type": "historical", "analysis_text": "The FTX collapse represents one of the largest financial frauds in history.", "key_insights": ["Concentration of power enabled fraud", "Regulatory gaps allowed growth"], "recommendations": ["Implement mandatory fund segregation", "Require third-party audits"], "warnings": ["Similar structures exist elsewhere"], "confidence": 0.85},
            {"perspective_type": "economic", "analysis_text": "The economic impact extended beyond FTX to the entire crypto market.", "key_insights": ["Market cap loss exceeded $200B", "Contagion spread to BlockFi, Genesis"], "recommendations": ["Diversify holdings", "Use regulated custodians"], "warnings": [], "confidence": 0.80}
        ],
        "sources": [
            {"url": "https://coindesk.com/ftx-alameda", "title": "CoinDesk FTX Alameda Report", "domain": "coindesk.com", "snippet": "A review of Alameda's balance sheet...", "credibility_score": 0.92, "source_type": "news"},
            {"url": "https://sec.gov/ftx-complaint", "title": "SEC Charges Bankman-Fried", "domain": "sec.gov", "snippet": "The SEC today charged...", "credibility_score": 0.98, "source_type": "government"}
        ],
        "claims": []
    }


def create_competitive_mock_data():
    return {
        "session_title": "AI Code Assistant Market Analysis",
        "session_query": "Compare GitHub Copilot, Cursor, and Claude Code in the AI coding assistant market",
        "template_type": "competitive",
        "status": "completed",
        "parameters": {"max_searches": 12},
        "created_at": datetime.now() - timedelta(hours=1),
        "completed_at": datetime.now(),
        "findings": [
            {"finding_type": "actor", "content": "GitHub Copilot is market leader with 1.3M+ paid subscribers.", "summary": "GitHub Copilot", "confidence_score": 0.95, "extracted_data": {"market_position": "Market Leader", "differentiators": ["GitHub integration", "Large training data"]}},
            {"finding_type": "actor", "content": "Cursor positions as AI-first IDE with full editor replacement.", "summary": "Cursor", "confidence_score": 0.88, "extracted_data": {"market_position": "Challenger", "differentiators": ["Full IDE", "Multi-model"]}},
            {"finding_type": "actor", "content": "Claude Code offers terminal-based AI with agentic features.", "summary": "Claude Code", "confidence_score": 0.90, "extracted_data": {"market_position": "Emerging", "differentiators": ["Agentic capabilities", "Safety focus"]}},
            {"finding_type": "fact", "content": "AI code assistant market projected to reach $5.2B by 2028 at 25% CAGR.", "summary": "Market size projection", "confidence_score": 0.82},
            {"finding_type": "pattern", "content": "All players moving toward agentic capabilities for multi-step tasks.", "summary": "Agentic trend", "confidence_score": 0.85},
            {"finding_type": "gap", "content": "Enterprise adoption metrics not publicly available for comparison.", "confidence_score": 0.60}
        ],
        "perspectives": [
            {"perspective_type": "competitive_advantage", "analysis_text": "Each player has distinct competitive advantages.", "key_insights": ["Copilot benefits from network effects", "Cursor offers deeper integration", "Claude Code suits power users"], "recommendations": ["Consider multi-tool strategy", "Evaluate based on workflow"], "warnings": ["Rapid innovation may shift dynamics"], "confidence": 0.85},
            {"perspective_type": "pricing_strategy", "analysis_text": "Pricing varies with different value propositions.", "key_insights": ["Copilot: $10-19/month", "Cursor: $20/month usage-based", "Claude Code: bundled with Pro"], "recommendations": ["Calculate TCO with productivity gains"], "warnings": [], "confidence": 0.78}
        ],
        "sources": [
            {"url": "https://github.blog/copilot", "title": "GitHub Copilot Updates", "domain": "github.blog", "credibility_score": 0.90, "source_type": "corporate"},
            {"url": "https://cursor.com", "title": "About Cursor", "domain": "cursor.com", "credibility_score": 0.85, "source_type": "corporate"}
        ],
        "claims": []
    }


def create_financial_mock_data():
    return {
        "session_title": "NVIDIA Investment Analysis",
        "session_query": "Should I invest in NVIDIA (NVDA) at current valuations given AI demand?",
        "template_type": "financial",
        "status": "completed",
        "parameters": {},
        "created_at": datetime.now() - timedelta(hours=1),
        "completed_at": datetime.now(),
        "findings": [
            {"finding_type": "fact", "content": "NVIDIA Q3 FY2025 revenue of $35.1B, up 94% YoY.", "summary": "Q3 revenue growth", "confidence_score": 0.98, "extracted_data": {"metrics": [{"name": "Revenue", "value": "$35.1B", "context": "Q3 FY2025"}]}},
            {"finding_type": "fact", "content": "Data center generated $30.8B, 88% of total revenue.", "summary": "Data center dominance", "confidence_score": 0.97, "extracted_data": {"metrics": [{"name": "DC Revenue", "value": "$30.8B", "context": "88% of total"}]}},
            {"finding_type": "event", "content": "Blackwell GPUs shipping Q4, demand exceeds supply.", "summary": "Blackwell launch", "confidence_score": 0.92, "event_date": "2024-11-20"},
            {"finding_type": "pattern", "content": "Gross margins expanded from 64% to 75% as AI demand outpaces supply.", "summary": "Margin expansion", "confidence_score": 0.88, "extracted_data": {"metrics": [{"name": "Gross Margin", "value": "75%", "context": "expanded from 64%"}]}},
            {"finding_type": "fact", "content": "Current P/E of 65x elevated vs historical 40x average.", "summary": "Valuation metrics", "confidence_score": 0.90, "extracted_data": {"metrics": [{"name": "P/E Ratio", "value": "65x", "context": "vs 40x historical"}]}},
            {"finding_type": "gap", "content": "Long-term AI infra spending sustainability uncertain.", "summary": "Demand sustainability", "confidence_score": 0.70}
        ],
        "perspectives": [
            {"perspective_type": "valuation", "analysis_text": "NVIDIA trades at premium justified by growth, but leaves little room for disappointment.", "key_insights": ["PEG 1.2x reasonable", "Forward P/E 35x on 2025 estimates", "DCF near fair value"], "recommendations": ["Dollar-cost average", "Limit position size"], "warnings": ["Guidance miss could trigger correction"], "confidence": 0.82},
            {"perspective_type": "risk", "analysis_text": "Key risks: concentration, competition, geopolitical.", "key_insights": ["Top 5 customers = 50%+ DC revenue", "AMD/Intel increasing AI investments", "China restrictions limit TAM"], "recommendations": ["Monitor hyperscaler capex"], "warnings": ["Export restrictions could tighten"], "confidence": 0.78}
        ],
        "sources": [
            {"url": "https://investor.nvidia.com/q3", "title": "NVIDIA Q3 Results", "domain": "investor.nvidia.com", "credibility_score": 0.99, "source_type": "sec_filing"}
        ],
        "claims": []
    }


def create_legal_mock_data():
    return {
        "session_title": "GDPR Compliance for AI",
        "session_query": "What are GDPR compliance requirements for AI companies in the EU?",
        "template_type": "legal",
        "status": "completed",
        "parameters": {},
        "created_at": datetime.now() - timedelta(hours=1),
        "completed_at": datetime.now(),
        "findings": [
            {"finding_type": "fact", "content": "Article 22 provides right not to be subject to automated decisions with legal effects.", "summary": "Article 22 - Automated Decisions", "confidence_score": 0.98, "extracted_data": {"citation": "GDPR Article 22"}},
            {"finding_type": "fact", "content": "Privacy by design and default required under Article 25.", "summary": "Privacy by Design", "confidence_score": 0.97, "extracted_data": {"citation": "GDPR Article 25"}},
            {"finding_type": "fact", "content": "DPIA mandatory under Article 35 for high-risk processing including AI.", "summary": "DPIA requirement", "confidence_score": 0.95, "extracted_data": {"citation": "GDPR Article 35"}},
            {"finding_type": "pattern", "content": "Courts require genuine human review, not rubber-stamping AI decisions.", "summary": "Human oversight interpretation", "confidence_score": 0.85},
            {"finding_type": "fact", "content": "Maximum fines: €20M or 4% global turnover.", "summary": "Maximum penalties", "confidence_score": 0.99, "extracted_data": {"citation": "GDPR Article 83"}},
            {"finding_type": "gap", "content": "GDPR and EU AI Act intersection creates compliance uncertainties.", "confidence_score": 0.72}
        ],
        "perspectives": [
            {"perspective_type": "compliance", "analysis_text": "GDPR compliance for AI requires comprehensive approach.", "key_insights": ["Establish lawful basis before collecting training data", "Right to explanation applies to AI decisions", "Data minimization limits training scope"], "recommendations": ["Conduct DPIA before deployment", "Implement human review processes", "Document lawful basis", "Handle data subject requests"], "warnings": ["Training on personal data without consent is high-risk", "Cross-border transfers need safeguards"], "confidence": 0.88},
            {"perspective_type": "regulatory_risk", "analysis_text": "Enforcement against AI companies increasing.", "key_insights": ["Irish DPC investigated major AI companies", "French CNIL issued AI training guidance", "Italian Garante banned ChatGPT temporarily"], "recommendations": ["Engage with DPAs proactively", "Monitor enforcement trends"], "warnings": [], "confidence": 0.82}
        ],
        "sources": [
            {"url": "https://eur-lex.europa.eu/gdpr", "title": "GDPR Regulation", "domain": "eur-lex.europa.eu", "credibility_score": 1.0, "source_type": "regulation"},
            {"url": "https://edpb.europa.eu/ai-guidelines", "title": "EDPB AI Guidelines", "domain": "edpb.europa.eu", "credibility_score": 0.98, "source_type": "government"}
        ],
        "claims": []
    }


MOCK_DATA_GENERATORS = {
    "investigative": create_investigative_mock_data,
    "competitive": create_competitive_mock_data,
    "financial": create_financial_mock_data,
    "legal": create_legal_mock_data
}

VARIANT_TEMPLATES = {
    "executive_summary": "investigative",
    "full_report": "investigative",
    "findings_only": "investigative",
    "source_bibliography": "investigative",
    "timeline_report": "investigative",
    "actor_dossier": "investigative",
    "evidence_brief": "investigative",
    "competitive_matrix": "competitive",
    "swot_analysis": "competitive",
    "battlecard": "competitive",
    "investment_thesis": "financial",
    "earnings_summary": "financial",
    "risk_assessment": "financial",
    "legal_brief": "legal",
    "case_digest": "legal",
    "compliance_checklist": "legal"
}


# =============================================================================
# TEST RUNNER
# =============================================================================

def generate_all_reports():
    """Generate all report variants and save to results folder."""
    print("\n" + "="*70)
    print(" STANDALONE REPORT GENERATION TEST")
    print("="*70)
    print(f" Started: {datetime.now().isoformat()}")
    print(f" Output: {_results_dir}")
    print("="*70)

    results = []

    for variant_name in VARIANT_TEMPLATES.keys():
        template_type = VARIANT_TEMPLATES[variant_name]
        mock_data = MOCK_DATA_GENERATORS[template_type]()
        data = ReportData(**mock_data)

        print(f"\n[{len(results)+1}/16] Generating: {variant_name}")

        try:
            composer_class = COMPOSER_REGISTRY[variant_name]
            composer = composer_class()
            variant = ReportVariant(variant_name)
            markdown = composer.compose(data, variant)

            word_count = len(markdown.split())
            char_count = len(markdown)

            # Save markdown
            md_path = _results_dir / f"{variant_name}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            print(f"    [OK] {word_count} words, {char_count} chars")
            print(f"    Saved: {md_path.name}")

            results.append({
                "variant": variant_name,
                "template": template_type,
                "words": word_count,
                "chars": char_count,
                "success": True
            })

        except Exception as e:
            print(f"    [FAIL] {e}")
            results.append({
                "variant": variant_name,
                "template": template_type,
                "success": False,
                "error": str(e)
            })

    # Summary
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)

    success = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\n  Total: {len(results)}")
    print(f"  Successful: {len(success)}")
    print(f"  Failed: {len(failed)}")

    if success:
        total_words = sum(r["words"] for r in success)
        print(f"\n  Total words: {total_words:,}")
        print(f"  Average: {total_words // len(success)} words/report")

        print("\n  By template:")
        for template in ["investigative", "competitive", "financial", "legal"]:
            t_results = [r for r in success if r["template"] == template]
            if t_results:
                words = sum(r["words"] for r in t_results)
                print(f"    {template}: {len(t_results)} reports, {words} words")

    if failed:
        print("\n  Failed:")
        for r in failed:
            print(f"    - {r['variant']}: {r['error'][:50]}")

    print("\n" + "="*70)
    return results


if __name__ == "__main__":
    generate_all_reports()
