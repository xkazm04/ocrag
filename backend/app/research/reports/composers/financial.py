"""Financial analysis report composers."""

from typing import List, Optional

from .base import BaseComposer
from ..schemas import ReportData, ReportVariant


class FinancialComposer(BaseComposer):
    """
    Composer for financial analysis report variants.

    Supports:
    - investment_thesis: Bull/bear case with valuation
    - earnings_summary: Metrics, guidance, analyst views
    - risk_assessment: Risk factors and severity
    """

    def compose(
        self,
        data: ReportData,
        variant: ReportVariant,
        title: Optional[str] = None,
        include_sections: Optional[List[str]] = None,
    ) -> str:
        """Generate financial analysis report variant."""
        if variant == ReportVariant.INVESTMENT_THESIS:
            return self._investment_thesis(data, title)
        elif variant == ReportVariant.EARNINGS_SUMMARY:
            return self._earnings_summary(data, title)
        elif variant == ReportVariant.RISK_ASSESSMENT:
            return self._risk_assessment(data, title)
        else:
            raise ValueError(f"Unsupported variant for financial: {variant}")

    def _investment_thesis(self, data: ReportData, title: Optional[str]) -> str:
        """Generate investment thesis report."""
        report_title = title or f"Investment Thesis: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        sections.append("## Investment Overview\n")
        sections.append(f"**Subject:** {data.session_query}\n")

        # Executive rating
        investment_perspective = next(
            (p for p in data.perspectives if "investment" in p.get("perspective_type", "").lower()),
            None
        )

        if investment_perspective:
            confidence = investment_perspective.get("confidence", 0.5)
            rating = self._investment_rating(confidence)
            sections.append(f"**Rating:** {rating}\n")
            sections.append(investment_perspective.get("analysis_text", ""))
            sections.append("")

        # Bull case
        sections.append(self._section_divider())
        sections.append("## Bull Case\n")

        bullish_findings = self._filter_sentiment(data.findings, positive=True)
        if bullish_findings:
            for finding in bullish_findings[:5]:
                sections.append(f"- **{finding.get('summary', finding.get('content', '')[:80])}**")
                sections.append(f"  - {finding.get('content', '')[:200]}")
                sections.append(f"  - *Confidence: {self._format_confidence(finding.get('confidence_score', 0.5))}*")
                sections.append("")
        else:
            sections.append("*No strong bullish indicators identified.*\n")

        # Bear case
        sections.append(self._section_divider())
        sections.append("## Bear Case\n")

        bearish_findings = self._filter_sentiment(data.findings, positive=False)
        if bearish_findings:
            for finding in bearish_findings[:5]:
                sections.append(f"- **{finding.get('summary', finding.get('content', '')[:80])}**")
                sections.append(f"  - {finding.get('content', '')[:200]}")
                sections.append(f"  - *Confidence: {self._format_confidence(finding.get('confidence_score', 0.5))}*")
                sections.append("")
        else:
            sections.append("*No strong bearish indicators identified.*\n")

        # Key metrics
        sections.append(self._section_divider())
        sections.append("## Key Metrics\n")

        metrics = self._extract_metrics(data)
        if metrics:
            sections.append("| Metric | Value | Context |")
            sections.append("|--------|-------|---------|")
            for metric in metrics[:10]:
                sections.append(f"| {metric['name']} | {metric['value']} | {metric['context']} |")
            sections.append("")
        else:
            facts = [f for f in data.findings if f.get("finding_type") == "fact"]
            for fact in facts[:5]:
                sections.append(f"- {fact.get('content', '')}")
            sections.append("")

        # Recommendations
        sections.append(self._section_divider())
        sections.append("## Investment Recommendations\n")

        all_recs = []
        for p in data.perspectives:
            all_recs.extend(p.get("recommendations", []))

        if all_recs:
            for rec in all_recs[:5]:
                sections.append(f"- {rec}")
        else:
            sections.append("*Conduct further due diligence before investment decisions.*")

        sections.append("")
        return "\n".join(sections)

    def _earnings_summary(self, data: ReportData, title: Optional[str]) -> str:
        """Generate earnings summary report."""
        report_title = title or f"Earnings Summary: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        sections.append("## Earnings Highlights\n")

        # Key financial facts
        facts = [f for f in data.findings if f.get("finding_type") == "fact"]
        events = [f for f in data.findings if f.get("finding_type") == "event"]

        # Recent events (earnings-related)
        if events:
            sections.append("### Recent Events\n")
            for event in events[:5]:
                date = event.get("event_date", "")
                content = event.get("content", "")
                sections.append(f"- **{date or 'Recent'}**: {content[:150]}")
            sections.append("")

        # Financial metrics
        sections.append("### Financial Metrics\n")

        metrics = self._extract_metrics(data)
        if metrics:
            sections.append("| Metric | Value |")
            sections.append("|--------|-------|")
            for metric in metrics[:8]:
                sections.append(f"| {metric['name']} | {metric['value']} |")
            sections.append("")
        else:
            for fact in facts[:5]:
                sections.append(f"- {fact.get('content', '')}")
            sections.append("")

        # Guidance
        sections.append(self._section_divider())
        sections.append("## Guidance & Outlook\n")

        patterns = [f for f in data.findings if f.get("finding_type") == "pattern"]
        if patterns:
            for pattern in patterns[:3]:
                sections.append(f"**{pattern.get('summary', 'Market Pattern')}**")
                sections.append(pattern.get("content", ""))
                sections.append("")
        else:
            sections.append("*No forward guidance identified in research.*\n")

        # Analyst perspectives
        sections.append(self._section_divider())
        sections.append("## Analyst Perspectives\n")

        for perspective in data.perspectives[:3]:
            ptype = perspective.get("perspective_type", "").replace("_", " ").title()
            insights = perspective.get("key_insights", [])

            if insights:
                sections.append(f"### {ptype} View")
                for insight in insights[:3]:
                    sections.append(f"- {insight}")
                sections.append("")

        if not data.perspectives:
            sections.append("*No analyst perspectives available.*\n")

        return "\n".join(sections)

    def _risk_assessment(self, data: ReportData, title: Optional[str]) -> str:
        """Generate risk assessment report."""
        report_title = title or f"Risk Assessment: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        sections.append("## Risk Overview\n")

        # Risk perspective if available
        risk_perspective = next(
            (p for p in data.perspectives if "risk" in p.get("perspective_type", "").lower()),
            None
        )

        if risk_perspective:
            sections.append(risk_perspective.get("analysis_text", ""))
            sections.append("")

        # Risk categories
        sections.append(self._section_divider())
        sections.append("## Identified Risks\n")

        # Categorize risks from findings
        gaps = [f for f in data.findings if f.get("finding_type") == "gap"]
        warnings = []
        for p in data.perspectives:
            warnings.extend(p.get("warnings", []))

        # High risk items
        sections.append("### High Priority Risks\n")
        high_risks = self._categorize_risks(data, "high")
        if high_risks:
            for risk in high_risks:
                sections.append(f"- **{risk['title']}**")
                sections.append(f"  - {risk['description']}")
                sections.append(f"  - *Severity: High*")
                sections.append("")
        else:
            sections.append("*No high priority risks identified.*\n")

        # Medium risk items
        sections.append("### Medium Priority Risks\n")
        medium_risks = self._categorize_risks(data, "medium")
        if medium_risks:
            for risk in medium_risks:
                sections.append(f"- **{risk['title']}**")
                sections.append(f"  - {risk['description']}")
                sections.append(f"  - *Severity: Medium*")
                sections.append("")
        else:
            sections.append("*No medium priority risks identified.*\n")

        # Low risk items
        sections.append("### Low Priority Risks\n")
        low_risks = self._categorize_risks(data, "low")
        if low_risks:
            for risk in low_risks:
                sections.append(f"- {risk['title']}: {risk['description']}")
        else:
            sections.append("*No low priority risks identified.*\n")
        sections.append("")

        # Gaps and warnings
        if gaps or warnings:
            sections.append(self._section_divider())
            sections.append("## Risk Factors & Warnings\n")

            if gaps:
                sections.append("### Information Gaps\n")
                for gap in gaps[:5]:
                    sections.append(f"- {gap.get('content', '')}")
                sections.append("")

            if warnings:
                sections.append("### Analyst Warnings\n")
                for warning in warnings[:5]:
                    sections.append(f"- {warning}")
                sections.append("")

        # Mitigation recommendations
        sections.append(self._section_divider())
        sections.append("## Risk Mitigation\n")

        all_recs = []
        for p in data.perspectives:
            all_recs.extend(p.get("recommendations", []))

        if all_recs:
            for rec in all_recs[:5]:
                sections.append(f"- {rec}")
        else:
            sections.append("*Develop risk mitigation strategy based on identified risks.*")

        sections.append("")
        return "\n".join(sections)

    def _investment_rating(self, confidence: float) -> str:
        """Convert confidence to investment rating."""
        if confidence >= 0.8:
            return "Strong Buy"
        elif confidence >= 0.65:
            return "Buy"
        elif confidence >= 0.5:
            return "Hold"
        elif confidence >= 0.35:
            return "Sell"
        else:
            return "Strong Sell"

    def _filter_sentiment(self, findings: list, positive: bool) -> list:
        """Filter findings by apparent sentiment."""
        positive_words = ["growth", "increase", "strong", "outperform", "beat", "exceed", "profit", "gain", "success"]
        negative_words = ["decline", "decrease", "weak", "underperform", "miss", "loss", "risk", "concern", "fail"]

        target_words = positive_words if positive else negative_words

        result = []
        for finding in findings:
            content = (finding.get("content", "") + finding.get("summary", "")).lower()
            if any(word in content for word in target_words):
                result.append(finding)

        return sorted(result, key=lambda f: f.get("confidence_score", 0), reverse=True)

    def _extract_metrics(self, data: ReportData) -> list:
        """Extract numerical metrics from findings."""
        metrics = []

        for finding in data.findings:
            extracted = finding.get("extracted_data", {})
            if extracted.get("metrics"):
                for metric in extracted["metrics"]:
                    if isinstance(metric, dict):
                        metrics.append(metric)
                    else:
                        metrics.append({
                            "name": "Metric",
                            "value": str(metric),
                            "context": finding.get("summary", "")[:50]
                        })

        # Also look for patterns with numeric content
        import re
        for finding in data.findings:
            content = finding.get("content", "")
            # Find dollar amounts, percentages, etc.
            numbers = re.findall(r'\$[\d,]+\.?\d*|\d+\.?\d*%|\d+\.?\d*[BMK]', content)
            for num in numbers[:2]:
                metrics.append({
                    "name": finding.get("finding_type", "value").title(),
                    "value": num,
                    "context": finding.get("summary", "")[:50]
                })

        return metrics[:15]

    def _categorize_risks(self, data: ReportData, severity: str) -> list:
        """Categorize risks by severity level."""
        risks = []

        severity_thresholds = {
            "high": (0.0, 0.4),  # Low confidence = high risk
            "medium": (0.4, 0.7),
            "low": (0.7, 1.0)
        }

        low, high = severity_thresholds.get(severity, (0, 1))

        for finding in data.findings:
            if finding.get("finding_type") in ["gap", "claim"]:
                confidence = finding.get("confidence_score", 0.5)
                if low <= confidence < high:
                    risks.append({
                        "title": finding.get("summary", finding.get("content", "")[:50]),
                        "description": finding.get("content", "")[:150]
                    })

        # Also check warnings from perspectives for high risk
        if severity == "high":
            for p in data.perspectives:
                for warning in p.get("warnings", []):
                    risks.append({
                        "title": "Analyst Warning",
                        "description": warning[:150]
                    })

        return risks[:5]
