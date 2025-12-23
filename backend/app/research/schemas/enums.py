"""Enums for the research module."""

from enum import Enum


class ResearchStatus(str, Enum):
    """Research session status."""
    ACTIVE = "active"
    SEARCHING = "searching"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


class TemplateType(str, Enum):
    """Available research templates."""
    INVESTIGATIVE = "investigative"
    MARKET = "market"
    HISTORICAL = "historical"
    DETECTIVE = "detective"


class FindingType(str, Enum):
    """Types of research findings."""
    FACT = "fact"
    CLAIM = "claim"
    EVENT = "event"
    ACTOR = "actor"
    RELATIONSHIP = "relationship"
    PATTERN = "pattern"
    GAP = "gap"
    EVIDENCE = "evidence"


class SourceType(str, Enum):
    """Types of web sources."""
    NEWS = "news"
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    CORPORATE = "corporate"
    BLOG = "blog"
    SOCIAL = "social"
    WIKI = "wiki"
    UNKNOWN = "unknown"


class PerspectiveType(str, Enum):
    """Expert perspective types."""
    HISTORICAL = "historical"
    POLITICAL = "political"
    ECONOMIC = "economic"
    PSYCHOLOGICAL = "psychological"
    MILITARY = "military"
    SOCIAL = "social"
    TECHNOLOGICAL = "technological"


class TemporalContext(str, Enum):
    """Temporal context for findings."""
    PAST = "past"
    PRESENT = "present"
    ONGOING = "ongoing"
    PREDICTION = "prediction"


class TopicType(str, Enum):
    """Types of knowledge topics."""
    DOMAIN = "domain"
    EVENT = "event"
    ENTITY = "entity"
    CONCEPT = "concept"


class EntityType(str, Enum):
    """Types of knowledge entities."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    PRODUCT = "product"
    CONCEPT = "concept"


class ClaimType(str, Enum):
    """Types of knowledge claims."""
    FACT = "fact"
    EVENT = "event"
    RELATIONSHIP = "relationship"
    PATTERN = "pattern"
    PREDICTION = "prediction"


class RelationshipType(str, Enum):
    """Types of claim relationships."""
    CAUSES = "causes"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    EXPANDS = "expands"
    SUPERSEDES = "supersedes"
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    PRECEDES = "precedes"
    DERIVED_FROM = "derived_from"
    CORROBORATES = "corroborates"
    REFUTES = "refutes"


class VerificationStatus(str, Enum):
    """Verification status for claims."""
    UNVERIFIED = "unverified"
    CORROBORATED = "corroborated"
    DISPUTED = "disputed"
    VERIFIED = "verified"


class Visibility(str, Enum):
    """Visibility levels for knowledge items."""
    PUBLIC = "public"
    WORKSPACE = "workspace"
    PRIVATE = "private"


class ClaimSourceType(str, Enum):
    """Types of sources for claims."""
    WEB = "web"
    DOCUMENT = "document"
    CLAIM = "claim"
    USER_INPUT = "user_input"


class SimilarityStatus(str, Enum):
    """Status for similarity candidates."""
    PENDING = "pending"
    MERGED = "merged"
    DISTINCT = "distinct"
    IGNORED = "ignored"
