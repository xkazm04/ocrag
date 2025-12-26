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
    # Core templates
    INVESTIGATIVE = "investigative"
    MARKET = "market"
    HISTORICAL = "historical"
    DETECTIVE = "detective"
    # Domain-specific templates
    COMPETITIVE = "competitive"      # Competitive intelligence
    FINANCIAL = "financial"          # Financial/stock analysis
    LEGAL = "legal"                  # Legal/regulatory research


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
    # General sources
    NEWS = "news"
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    CORPORATE = "corporate"
    BLOG = "blog"
    SOCIAL = "social"
    WIKI = "wiki"
    UNKNOWN = "unknown"
    # Financial sources
    SEC_FILING = "sec_filing"
    EARNINGS_REPORT = "earnings_report"
    ANALYST_REPORT = "analyst_report"
    FINANCIAL_NEWS = "financial_news"
    PRESS_RELEASE = "press_release"
    # Legal sources
    COURT_RULING = "court_ruling"
    STATUTE = "statute"
    REGULATION = "regulation"
    LEGAL_COMMENTARY = "legal_commentary"


class PerspectiveType(str, Enum):
    """Expert perspective types."""
    # Investigative perspectives
    HISTORICAL = "historical"
    POLITICAL = "political"
    ECONOMIC = "economic"
    PSYCHOLOGICAL = "psychological"
    MILITARY = "military"
    SOCIAL = "social"
    TECHNOLOGICAL = "technological"
    # Competitive intelligence perspectives
    MARKET_POSITION = "market_position"
    COMPETITIVE_ADVANTAGE = "competitive_advantage"
    SWOT = "swot"
    PRICING_STRATEGY = "pricing_strategy"
    # Financial analysis perspectives
    VALUATION = "valuation"
    RISK = "risk"
    SENTIMENT = "sentiment"
    FUNDAMENTAL = "fundamental"
    # Legal research perspectives
    COMPLIANCE = "compliance"
    PRECEDENT = "precedent"
    REGULATORY_RISK = "regulatory_risk"
    JURISDICTION = "jurisdiction"


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
    # General entities
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    PRODUCT = "product"
    CONCEPT = "concept"
    # Competitive entities
    COMPETITOR = "competitor"
    MARKET_SEGMENT = "market_segment"
    PRODUCT_LINE = "product_line"
    # Financial entities
    PUBLICLY_TRADED_COMPANY = "publicly_traded_company"
    SECURITY = "security"
    FUND = "fund"
    # Legal entities
    COURT = "court"
    JUDGE = "judge"
    LEGAL_CASE = "legal_case"
    REGULATORY_BODY = "regulatory_body"


class ClaimType(str, Enum):
    """Types of knowledge claims."""
    FACT = "fact"
    EVENT = "event"
    RELATIONSHIP = "relationship"
    PATTERN = "pattern"
    PREDICTION = "prediction"
    FINANCIAL = "financial"  # Money transfers, payments, transactions
    EVIDENCE = "evidence"    # Documentary evidence


class RelationshipType(str, Enum):
    """Types of claim relationships."""
    # General relationships
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
    # Competitive relationships
    COMPETES_WITH = "competes_with"
    PARTNERS_WITH = "partners_with"
    # Legal relationships
    OVERRULES = "overrules"
    DISTINGUISHES = "distinguishes"
    EXTENDS_PRECEDENT = "extends_precedent"
    CITES = "cites"


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
