"""Perspective Agents Module.

Provides specialized analysis perspectives for research findings:
- Historical: Places events in historical context
- Financial: Analyzes economic motivations and impacts
- Journalist: Identifies contradictions and propaganda
- Conspirator: Proposes probable hidden motivations
- Network: Maps actor relationships and power dynamics
"""

from .base import BasePerspectiveAgent, PerspectiveContext
from .agents import (
    HistoricalAgent,
    FinancialAgent,
    JournalistAgent,
    ConspiratorAgent,
    NetworkAgent,
)
from .runner import PerspectiveRunner, run_perspectives

__all__ = [
    "BasePerspectiveAgent",
    "PerspectiveContext",
    "HistoricalAgent",
    "FinancialAgent",
    "JournalistAgent",
    "ConspiratorAgent",
    "NetworkAgent",
    "PerspectiveRunner",
    "run_perspectives",
]
