"""Markdown composers for report generation."""

from .base import BaseComposer
from .executive import ExecutiveSummaryComposer
from .full_report import FullReportComposer
from .investigative import InvestigativeComposer
from .competitive import CompetitiveComposer
from .financial import FinancialComposer
from .legal import LegalComposer

# Composer registry maps variant -> composer class
COMPOSER_REGISTRY = {
    # Universal variants
    "executive_summary": ExecutiveSummaryComposer,
    "full_report": FullReportComposer,
    "findings_only": FullReportComposer,  # Uses full report with sections filter
    "source_bibliography": FullReportComposer,

    # Investigative variants
    "timeline_report": InvestigativeComposer,
    "actor_dossier": InvestigativeComposer,
    "evidence_brief": InvestigativeComposer,

    # Competitive variants
    "competitive_matrix": CompetitiveComposer,
    "swot_analysis": CompetitiveComposer,
    "battlecard": CompetitiveComposer,

    # Financial variants
    "investment_thesis": FinancialComposer,
    "earnings_summary": FinancialComposer,
    "risk_assessment": FinancialComposer,

    # Legal variants
    "legal_brief": LegalComposer,
    "case_digest": LegalComposer,
    "compliance_checklist": LegalComposer,
}


def get_composer(variant: str) -> BaseComposer:
    """Get the appropriate composer for a report variant."""
    composer_class = COMPOSER_REGISTRY.get(variant)
    if not composer_class:
        raise ValueError(f"Unknown report variant: {variant}")
    return composer_class()


__all__ = [
    "BaseComposer",
    "ExecutiveSummaryComposer",
    "FullReportComposer",
    "InvestigativeComposer",
    "CompetitiveComposer",
    "FinancialComposer",
    "LegalComposer",
    "COMPOSER_REGISTRY",
    "get_composer",
]
