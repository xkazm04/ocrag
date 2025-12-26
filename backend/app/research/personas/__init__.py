"""Expert personas for multi-perspective analysis."""

from .base import BasePersona
# Investigative personas
from .historian import HistorianPersona
from .economist import EconomistPersona
from .political import PoliticalPersona
from .psychologist import PsychologistPersona
from .military import MilitaryPersona
# Competitive intelligence personas
from .market_position import MarketPositionPersona
from .competitive_advantage import CompetitiveAdvantagePersona
from .swot import SWOTPersona
from .pricing_strategy import PricingStrategyPersona
# Financial analysis personas
from .valuation import ValuationPersona
from .risk_analyst import RiskAnalystPersona
from .sentiment import SentimentPersona
from .fundamental import FundamentalPersona
# Legal research personas
from .compliance import CompliancePersona
from .precedent import PrecedentPersona
from .regulatory_risk import RegulatoryRiskPersona
from .jurisdiction import JurisdictionPersona

# Persona registry
PERSONA_REGISTRY = {
    # Investigative perspectives
    "historical": HistorianPersona(),
    "economic": EconomistPersona(),
    "political": PoliticalPersona(),
    "psychological": PsychologistPersona(),
    "military": MilitaryPersona(),
    # Competitive intelligence perspectives
    "market_position": MarketPositionPersona(),
    "competitive_advantage": CompetitiveAdvantagePersona(),
    "swot": SWOTPersona(),
    "pricing_strategy": PricingStrategyPersona(),
    # Financial analysis perspectives
    "valuation": ValuationPersona(),
    "risk": RiskAnalystPersona(),
    "sentiment": SentimentPersona(),
    "fundamental": FundamentalPersona(),
    # Legal research perspectives
    "compliance": CompliancePersona(),
    "precedent": PrecedentPersona(),
    "regulatory_risk": RegulatoryRiskPersona(),
    "jurisdiction": JurisdictionPersona(),
}


def get_persona(perspective_type: str) -> BasePersona:
    """Get a persona by perspective type."""
    persona = PERSONA_REGISTRY.get(perspective_type)
    if not persona:
        raise ValueError(f"Unknown perspective type: {perspective_type}")
    return persona


__all__ = [
    "BasePersona",
    # Investigative
    "HistorianPersona",
    "EconomistPersona",
    "PoliticalPersona",
    "PsychologistPersona",
    "MilitaryPersona",
    # Competitive
    "MarketPositionPersona",
    "CompetitiveAdvantagePersona",
    "SWOTPersona",
    "PricingStrategyPersona",
    # Financial
    "ValuationPersona",
    "RiskAnalystPersona",
    "SentimentPersona",
    "FundamentalPersona",
    # Legal
    "CompliancePersona",
    "PrecedentPersona",
    "RegulatoryRiskPersona",
    "JurisdictionPersona",
    # Registry
    "PERSONA_REGISTRY",
    "get_persona",
]
