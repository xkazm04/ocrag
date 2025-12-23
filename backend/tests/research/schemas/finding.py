"""Enhanced finding schema for knowledge graph.

Each finding is a core unit of knowledge with:
- Linked actors and sources
- Multiple perspective analyses
- Relationships to other findings
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional, List, Dict, Any
import uuid


class FindingType(Enum):
    """Types of findings extracted from research."""
    EVENT = "event"           # Something that happened
    ACTOR = "actor"           # Person, organization, entity
    RELATIONSHIP = "relationship"  # Connection between actors
    EVIDENCE = "evidence"     # Document, statement, data point
    PATTERN = "pattern"       # Recurring behavior or structure
    GAP = "gap"               # Missing information


class ActorType(Enum):
    """Types of actors that can be referenced."""
    PERSON = "person"
    ORGANIZATION = "organization"
    COUNTRY = "country"
    ENTITY = "entity"  # Generic entity


class DatePrecision(Enum):
    """Precision level of extracted dates."""
    EXACT = "exact"           # Full date: 2022-02-24
    MONTH = "month"           # Month precision: 2022-02
    YEAR = "year"             # Year only: 2022
    RANGE = "range"           # Date range: 2014-2022
    APPROXIMATE = "approximate"  # Approximate date
    UNKNOWN = "unknown"       # No date information


@dataclass
class ExtractedDate:
    """Extracted and normalized date information."""
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    precision: DatePrecision = DatePrecision.UNKNOWN
    original_text: str = ""

    @property
    def display_text(self) -> str:
        """Human-readable date string."""
        if self.original_text:
            return self.original_text
        if self.date_start:
            if self.precision == DatePrecision.EXACT:
                return self.date_start.strftime("%B %d, %Y")
            elif self.precision == DatePrecision.MONTH:
                return self.date_start.strftime("%B %Y")
            elif self.precision == DatePrecision.YEAR:
                return str(self.date_start.year)
            elif self.precision == DatePrecision.RANGE and self.date_end:
                return f"{self.date_start.year}-{self.date_end.year}"
        return "Unknown date"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date_start": self.date_start.isoformat() if self.date_start else None,
            "date_end": self.date_end.isoformat() if self.date_end else None,
            "precision": self.precision.value,
            "display_text": self.display_text,
        }


@dataclass
class ActorRef:
    """Reference to an actor mentioned in a finding."""
    name: str
    actor_type: ActorType = ActorType.ENTITY
    role: str = "mentioned"  # subject, object, mentioned, participant
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "actor_type": self.actor_type.value,
            "role": self.role,
            "aliases": self.aliases,
        }


@dataclass
class SourceRef:
    """Reference to a source supporting a finding."""
    source_id: str
    url: str
    title: str
    domain: str
    excerpt: str = ""  # Specific text supporting this finding
    source_type: str = "web"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "domain": self.domain,
            "excerpt": self.excerpt[:200] if self.excerpt else "",
            "source_type": self.source_type,
        }


@dataclass
class Finding:
    """Core finding unit with linked perspectives and relationships.

    This is the central node in the knowledge graph. Each finding can have:
    - Multiple source references (evidence)
    - Multiple actor references (who's involved)
    - Multiple perspective analyses (different viewpoints)
    - Relationships to other findings (causality, contradiction, etc.)
    """

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Core content
    finding_type: FindingType = FindingType.EVENT
    content: str = ""
    summary: str = ""

    # Temporal information
    extracted_date: ExtractedDate = field(default_factory=ExtractedDate)

    # Linked entities
    actors: List[ActorRef] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)

    # Source attribution
    source_refs: List[SourceRef] = field(default_factory=list)

    # Perspectives (populated by perspective agents)
    # Key is perspective type: "historical", "financial", "journalist", etc.
    perspectives: Dict[str, Any] = field(default_factory=dict)

    # Relationships to other findings (populated by relationship builder)
    # Stored as list of FindingRelationship objects
    relationships: List[Any] = field(default_factory=list)

    # Metadata
    batch_id: Optional[str] = None  # Which research batch produced this
    extracted_data: Optional[Dict] = None  # Additional structured data

    @property
    def event_date(self) -> Optional[date]:
        """Convenience accessor for the primary date."""
        return self.extracted_date.date_start

    @property
    def date_text(self) -> str:
        """Convenience accessor for date display text."""
        return self.extracted_date.display_text

    def add_actor(
        self,
        name: str,
        actor_type: ActorType = ActorType.ENTITY,
        role: str = "mentioned",
    ) -> None:
        """Add an actor reference to this finding."""
        self.actors.append(ActorRef(
            name=name,
            actor_type=actor_type,
            role=role,
        ))

    def add_source(
        self,
        url: str,
        title: str,
        domain: str,
        excerpt: str = "",
    ) -> None:
        """Add a source reference to this finding."""
        source_id = str(uuid.uuid4())[:8]
        self.source_refs.append(SourceRef(
            source_id=source_id,
            url=url,
            title=title,
            domain=domain,
            excerpt=excerpt,
        ))

    def add_perspective(self, perspective_type: str, analysis: Any) -> None:
        """Add a perspective analysis to this finding."""
        self.perspectives[perspective_type] = analysis

    def get_perspective(self, perspective_type: str) -> Optional[Any]:
        """Get a specific perspective analysis."""
        return self.perspectives.get(perspective_type)

    def has_perspective(self, perspective_type: str) -> bool:
        """Check if a perspective has been added."""
        return perspective_type in self.perspectives

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "finding_type": self.finding_type.value,
            "content": self.content,
            "summary": self.summary,
            "date": self.extracted_date.to_dict(),
            "actors": [a.to_dict() for a in self.actors],
            "locations": self.locations,
            "sources": [s.to_dict() for s in self.source_refs],
            "perspectives": {
                k: v.to_dict() if hasattr(v, 'to_dict') else v
                for k, v in self.perspectives.items()
            },
            "relationships": [
                r.to_dict() if hasattr(r, 'to_dict') else r
                for r in self.relationships
            ],
            "batch_id": self.batch_id,
            "extracted_data": self.extracted_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finding":
        """Create Finding from dictionary."""
        # Parse date
        date_data = data.get("date", {})
        extracted_date = ExtractedDate(
            date_start=date.fromisoformat(date_data["date_start"]) if date_data.get("date_start") else None,
            date_end=date.fromisoformat(date_data["date_end"]) if date_data.get("date_end") else None,
            precision=DatePrecision(date_data.get("precision", "unknown")),
            original_text=date_data.get("display_text", ""),
        )

        # Parse actors
        actors = [
            ActorRef(
                name=a["name"],
                actor_type=ActorType(a.get("actor_type", "entity")),
                role=a.get("role", "mentioned"),
            )
            for a in data.get("actors", [])
        ]

        # Parse sources
        sources = [
            SourceRef(
                source_id=s.get("source_id", ""),
                url=s.get("url", ""),
                title=s.get("title", ""),
                domain=s.get("domain", ""),
                excerpt=s.get("excerpt", ""),
            )
            for s in data.get("sources", [])
        ]

        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            finding_type=FindingType(data.get("finding_type", "event")),
            content=data.get("content", ""),
            summary=data.get("summary", ""),
            extracted_date=extracted_date,
            actors=actors,
            locations=data.get("locations", []),
            source_refs=sources,
            perspectives=data.get("perspectives", {}),
            batch_id=data.get("batch_id"),
            extracted_data=data.get("extracted_data"),
        )
