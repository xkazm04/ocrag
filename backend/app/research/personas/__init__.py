"""Expert personas for multi-perspective analysis."""

from .base import BasePersona
from .historian import HistorianPersona
from .economist import EconomistPersona
from .political import PoliticalPersona
from .psychologist import PsychologistPersona
from .military import MilitaryPersona

# Persona registry
PERSONA_REGISTRY = {
    "historical": HistorianPersona(),
    "economic": EconomistPersona(),
    "political": PoliticalPersona(),
    "psychological": PsychologistPersona(),
    "military": MilitaryPersona(),
}


def get_persona(perspective_type: str) -> BasePersona:
    """Get a persona by perspective type."""
    persona = PERSONA_REGISTRY.get(perspective_type)
    if not persona:
        raise ValueError(f"Unknown perspective type: {perspective_type}")
    return persona


__all__ = [
    "BasePersona",
    "HistorianPersona",
    "EconomistPersona",
    "PoliticalPersona",
    "PsychologistPersona",
    "MilitaryPersona",
    "PERSONA_REGISTRY",
    "get_persona",
]
