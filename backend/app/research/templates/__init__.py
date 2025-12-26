"""Research templates module."""

from .base import BaseResearchTemplate
from .investigative import InvestigativeTemplate
from .competitive import CompetitiveIntelligenceTemplate
from .financial import FinancialAnalysisTemplate
from .legal import LegalResearchTemplate

# Template registry
TEMPLATE_REGISTRY = {
    "investigative": InvestigativeTemplate(),
    "competitive": CompetitiveIntelligenceTemplate(),
    "financial": FinancialAnalysisTemplate(),
    "legal": LegalResearchTemplate(),
}


def get_template(template_type: str) -> BaseResearchTemplate:
    """Get a research template by type."""
    template = TEMPLATE_REGISTRY.get(template_type)
    if not template:
        raise ValueError(f"Unknown template type: {template_type}")
    return template


__all__ = [
    "BaseResearchTemplate",
    "InvestigativeTemplate",
    "CompetitiveIntelligenceTemplate",
    "FinancialAnalysisTemplate",
    "LegalResearchTemplate",
    "TEMPLATE_REGISTRY",
    "get_template",
]
