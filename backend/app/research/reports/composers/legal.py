"""Legal research report composers."""

from typing import List, Optional

from .base import BaseComposer
from ..schemas import ReportData, ReportVariant


class LegalComposer(BaseComposer):
    """
    Composer for legal research report variants.

    Supports:
    - legal_brief: IRAC format memorandum
    - case_digest: Holdings and precedents
    - compliance_checklist: Requirements × Status matrix
    """

    def compose(
        self,
        data: ReportData,
        variant: ReportVariant,
        title: Optional[str] = None,
        include_sections: Optional[List[str]] = None,
    ) -> str:
        """Generate legal research report variant."""
        if variant == ReportVariant.LEGAL_BRIEF:
            return self._legal_brief(data, title)
        elif variant == ReportVariant.CASE_DIGEST:
            return self._case_digest(data, title)
        elif variant == ReportVariant.COMPLIANCE_CHECKLIST:
            return self._compliance_checklist(data, title)
        else:
            raise ValueError(f"Unsupported variant for legal: {variant}")

    def _legal_brief(self, data: ReportData, title: Optional[str]) -> str:
        """Generate IRAC-format legal brief."""
        report_title = title or f"Legal Brief: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        # IRAC Format: Issue, Rule, Application, Conclusion

        # Issue
        sections.append("## I. Issue\n")
        sections.append(f"**Question Presented:** {data.session_query}\n")

        # Identify the core legal issues from findings
        legal_issues = self._extract_legal_issues(data)
        if legal_issues:
            sections.append("**Sub-Issues:**")
            for issue in legal_issues[:5]:
                sections.append(f"- {issue}")
            sections.append("")

        # Rule
        sections.append(self._section_divider())
        sections.append("## II. Rule\n")

        # Extract legal rules and precedents
        rules = self._extract_rules(data)
        if rules:
            for rule in rules:
                sections.append(f"### {rule['title']}\n")
                sections.append(rule['content'])
                sections.append("")
                if rule.get('citation'):
                    sections.append(f"*{rule['citation']}*")
                sections.append("")
        else:
            sections.append("*Applicable legal rules require further research.*\n")

        # Application
        sections.append(self._section_divider())
        sections.append("## III. Application\n")

        # Use perspectives for analysis
        for perspective in data.perspectives:
            ptype = perspective.get("perspective_type", "").replace("_", " ").title()
            analysis = perspective.get("analysis_text", "")

            if analysis:
                sections.append(f"### {ptype} Analysis\n")
                sections.append(analysis)
                sections.append("")

                insights = perspective.get("key_insights", [])
                if insights:
                    sections.append("**Key Points:**")
                    for insight in insights[:4]:
                        sections.append(f"- {insight}")
                    sections.append("")

        if not data.perspectives:
            # Fall back to findings
            patterns = [f for f in data.findings if f.get("finding_type") == "pattern"]
            facts = [f for f in data.findings if f.get("finding_type") == "fact"]

            if patterns:
                sections.append("### Legal Patterns Identified\n")
                for pattern in patterns[:3]:
                    sections.append(f"**{pattern.get('summary', 'Pattern')}**")
                    sections.append(pattern.get("content", ""))
                    sections.append("")

            if facts:
                sections.append("### Relevant Facts\n")
                for fact in facts[:5]:
                    sections.append(f"- {fact.get('content', '')}")
                sections.append("")

        # Conclusion
        sections.append(self._section_divider())
        sections.append("## IV. Conclusion\n")

        # Aggregate recommendations as conclusions
        all_recs = []
        for p in data.perspectives:
            all_recs.extend(p.get("recommendations", []))

        if all_recs:
            sections.append("Based on the analysis above:\n")
            for rec in all_recs[:5]:
                sections.append(f"- {rec}")
            sections.append("")
        else:
            sections.append("*Further legal analysis required to reach conclusions.*\n")

        # Caveats
        warnings = []
        for p in data.perspectives:
            warnings.extend(p.get("warnings", []))

        if warnings:
            sections.append("### Caveats\n")
            for warning in warnings[:3]:
                sections.append(f"- {warning}")
            sections.append("")

        # Sources
        sections.append(self._section_divider())
        sections.append("## Authorities Cited\n")

        legal_sources = [s for s in data.sources if s.get("source_type") in ["legal", "government", "official"]]
        other_sources = [s for s in data.sources if s not in legal_sources]

        if legal_sources:
            sections.append("### Primary Sources\n")
            for source in legal_sources[:10]:
                title_str = source.get("title", source.get("url", ""))
                url = source.get("url", "#")
                sections.append(f"- [{title_str}]({url})")
            sections.append("")

        if other_sources:
            sections.append("### Secondary Sources\n")
            for source in other_sources[:5]:
                title_str = source.get("title", source.get("url", ""))
                url = source.get("url", "#")
                sections.append(f"- [{title_str}]({url})")
            sections.append("")

        return "\n".join(sections)

    def _case_digest(self, data: ReportData, title: Optional[str]) -> str:
        """Generate case digest with holdings and precedents."""
        report_title = title or f"Case Digest: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        sections.append("## Case Overview\n")
        sections.append(f"**Research Focus:** {data.session_query}\n")

        # Cases identified (from actors in legal context)
        actors = [f for f in data.findings if f.get("finding_type") == "actor"]

        sections.append("## Cases Analyzed\n")

        if not actors:
            # Fall back to using facts as case references
            facts = [f for f in data.findings if f.get("finding_type") == "fact"]
            if facts:
                for i, fact in enumerate(facts[:10], 1):
                    sections.append(f"### Case Reference {i}")
                    sections.append("")
                    sections.append(fact.get("content", ""))
                    sections.append("")
                    sections.append(f"*Confidence: {self._format_confidence(fact.get('confidence_score', 0.5))}*")
                    sections.append("")
            else:
                sections.append("*No specific cases identified in research.*\n")
        else:
            for i, actor in enumerate(actors, 1):
                case_name = actor.get("summary", f"Case {i}")
                content = actor.get("content", "")
                extracted = actor.get("extracted_data", {})
                confidence = actor.get("confidence_score", 0.5)

                sections.append(f"### {case_name}")
                sections.append("")

                # Case details
                if extracted.get("court"):
                    sections.append(f"**Court:** {extracted['court']}")
                if extracted.get("date"):
                    sections.append(f"**Date:** {extracted['date']}")
                if extracted.get("citation"):
                    sections.append(f"**Citation:** {extracted['citation']}")
                sections.append("")

                # Holding
                sections.append("**Holding:**")
                sections.append(content)
                sections.append("")

                # Significance
                if extracted.get("significance"):
                    sections.append(f"**Significance:** {extracted['significance']}")
                    sections.append("")

                sections.append(f"*Confidence: {self._format_confidence(confidence)}*")
                sections.append("")

        # Key precedents
        sections.append(self._section_divider())
        sections.append("## Key Precedents\n")

        patterns = [f for f in data.findings if f.get("finding_type") == "pattern"]
        if patterns:
            for pattern in patterns[:5]:
                sections.append(f"- **{pattern.get('summary', 'Precedent')}**: {pattern.get('content', '')[:200]}")
            sections.append("")
        else:
            sections.append("*No precedent patterns identified.*\n")

        # Legal principles
        sections.append(self._section_divider())
        sections.append("## Legal Principles\n")

        for perspective in data.perspectives[:2]:
            insights = perspective.get("key_insights", [])
            for insight in insights[:4]:
                sections.append(f"- {insight}")

        if not data.perspectives:
            sections.append("*Further analysis needed to extract legal principles.*")

        sections.append("")
        return "\n".join(sections)

    def _compliance_checklist(self, data: ReportData, title: Optional[str]) -> str:
        """Generate compliance requirements checklist."""
        report_title = title or f"Compliance Checklist: {data.session_query[:50]}"

        sections = []
        sections.append(self._header(report_title, data))

        sections.append("## Compliance Overview\n")
        sections.append(f"**Scope:** {data.session_query}\n")

        # Compliance perspective if available
        compliance_perspective = next(
            (p for p in data.perspectives if "compliance" in p.get("perspective_type", "").lower()),
            None
        )

        if compliance_perspective:
            sections.append(compliance_perspective.get("analysis_text", ""))
            sections.append("")

        # Requirements matrix
        sections.append(self._section_divider())
        sections.append("## Requirements Checklist\n")

        # Build requirements from findings
        requirements = self._extract_requirements(data)

        if requirements:
            sections.append("| # | Requirement | Category | Status | Priority |")
            sections.append("|---|-------------|----------|--------|----------|")

            for i, req in enumerate(requirements, 1):
                status = req.get("status", "Pending")
                status_icon = "✅" if status == "Met" else "❌" if status == "Not Met" else "⏳"
                sections.append(
                    f"| {i} | {req['requirement'][:60]} | {req['category']} | {status_icon} {status} | {req['priority']} |"
                )
            sections.append("")
        else:
            sections.append("*No specific compliance requirements extracted.*\n")

            # Fall back to listing findings as requirements
            facts = [f for f in data.findings if f.get("finding_type") == "fact"]
            if facts:
                sections.append("### Identified Compliance Points\n")
                for fact in facts[:10]:
                    confidence = fact.get("confidence_score", 0.5)
                    priority = "High" if confidence >= 0.7 else "Medium" if confidence >= 0.5 else "Low"
                    sections.append(f"- [ ] {fact.get('content', '')[:100]} *(Priority: {priority})*")
                sections.append("")

        # Gaps and risks
        gaps = [f for f in data.findings if f.get("finding_type") == "gap"]
        if gaps:
            sections.append(self._section_divider())
            sections.append("## Compliance Gaps\n")

            for gap in gaps:
                sections.append(f"- **Gap:** {gap.get('content', '')}")
                sections.append(f"  - *Confidence: {self._format_confidence(gap.get('confidence_score', 0.5))}*")
            sections.append("")

        # Regulatory warnings
        warnings = []
        for p in data.perspectives:
            warnings.extend(p.get("warnings", []))

        if warnings:
            sections.append(self._section_divider())
            sections.append("## Regulatory Warnings\n")

            for warning in warnings:
                sections.append(f"- {warning}")
            sections.append("")

        # Action items
        sections.append(self._section_divider())
        sections.append("## Recommended Actions\n")

        all_recs = []
        for p in data.perspectives:
            all_recs.extend(p.get("recommendations", []))

        if all_recs:
            for i, rec in enumerate(all_recs[:8], 1):
                sections.append(f"{i}. {rec}")
        else:
            sections.append("1. Review all compliance requirements with legal counsel")
            sections.append("2. Develop compliance implementation plan")
            sections.append("3. Establish monitoring and reporting procedures")

        sections.append("")
        return "\n".join(sections)

    def _extract_legal_issues(self, data: ReportData) -> list:
        """Extract legal issues from findings."""
        issues = []

        # Look for question-type findings
        for finding in data.findings:
            content = finding.get("content", "")
            summary = finding.get("summary", "")

            # Check for legal issue indicators
            if any(word in content.lower() for word in ["whether", "issue", "question", "liability", "right", "duty"]):
                issues.append(summary or content[:100])

        # Also extract from perspectives
        for perspective in data.perspectives:
            insights = perspective.get("key_insights", [])
            for insight in insights:
                if "?" in insight or any(word in insight.lower() for word in ["whether", "issue"]):
                    issues.append(insight)

        return list(set(issues))[:5]

    def _extract_rules(self, data: ReportData) -> list:
        """Extract legal rules from findings."""
        rules = []

        # Look for rule-type content
        for finding in data.findings:
            if finding.get("finding_type") in ["fact", "pattern"]:
                content = finding.get("content", "")
                summary = finding.get("summary", "")
                extracted = finding.get("extracted_data", {})

                # Check for legal rule indicators
                legal_indicators = ["shall", "must", "required", "prohibited", "court held", "statute", "regulation"]
                if any(word in content.lower() for word in legal_indicators):
                    rules.append({
                        "title": summary or "Legal Rule",
                        "content": content,
                        "citation": extracted.get("citation", "")
                    })

        return rules[:10]

    def _extract_requirements(self, data: ReportData) -> list:
        """Extract compliance requirements from findings."""
        requirements = []

        compliance_words = {
            "mandatory": "High",
            "required": "High",
            "must": "High",
            "shall": "High",
            "should": "Medium",
            "recommended": "Medium",
            "may": "Low",
            "optional": "Low"
        }

        for finding in data.findings:
            content = finding.get("content", "")
            summary = finding.get("summary", "")
            extracted = finding.get("extracted_data", {})

            # Determine priority from content
            priority = "Medium"
            for word, pri in compliance_words.items():
                if word in content.lower():
                    priority = pri
                    break

            # Determine category
            category = "General"
            if extracted.get("category"):
                category = extracted["category"]
            elif "data" in content.lower() or "privacy" in content.lower():
                category = "Data Privacy"
            elif "security" in content.lower():
                category = "Security"
            elif "report" in content.lower() or "disclosure" in content.lower():
                category = "Reporting"
            elif "audit" in content.lower():
                category = "Audit"

            if any(word in content.lower() for word in compliance_words.keys()):
                requirements.append({
                    "requirement": summary or content[:80],
                    "category": category,
                    "priority": priority,
                    "status": "Pending"
                })

        return requirements[:15]
