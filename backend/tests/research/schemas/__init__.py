"""Research system schemas.

Enhanced schemas for finding-centric knowledge graph with:
- Linked perspectives per finding
- Actor and source references
- Relationship mapping between findings
"""

from .finding import (
    Finding,
    FindingType,
    ActorRef,
    ActorType,
    SourceRef,
    ExtractedDate,
    DatePrecision,
)
from .perspective import (
    PerspectiveType,
    PerspectiveAnalysis,
    HistoricalAnalysis,
    FinancialAnalysis,
    JournalistAnalysis,
    ConspiratorAnalysis,
    NetworkAnalysis,
)
from .relationship import (
    RelationshipType,
    FindingRelationship,
    Contradiction,
    ResearchGap,
    GapType,
)

__all__ = [
    # Finding
    "Finding",
    "FindingType",
    "ActorRef",
    "ActorType",
    "SourceRef",
    "ExtractedDate",
    "DatePrecision",
    # Perspective
    "PerspectiveType",
    "PerspectiveAnalysis",
    "HistoricalAnalysis",
    "FinancialAnalysis",
    "JournalistAnalysis",
    "ConspiratorAnalysis",
    "NetworkAnalysis",
    # Relationship
    "RelationshipType",
    "FindingRelationship",
    "Contradiction",
    "ResearchGap",
    "GapType",
]
