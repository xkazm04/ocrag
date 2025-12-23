"""Relationship schemas for knowledge graph edges.

Defines relationships between findings and gap/contradiction detection.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class RelationshipType(Enum):
    """Types of relationships between findings."""
    CAUSES = "causes"           # A caused/led to B
    SUPPORTS = "supports"       # A provides evidence for B
    CONTRADICTS = "contradicts" # A conflicts with B
    EXPANDS = "expands"         # A adds detail to B
    PRECEDES = "precedes"       # A happened before B (temporal)
    INVOLVES = "involves"       # A involves same actors as B
    SUPERSEDES = "supersedes"   # A replaces B (newer information)
    PART_OF = "part_of"         # A is component of B


class GapType(Enum):
    """Types of gaps in research coverage."""
    TEMPORAL = "temporal"       # Missing time period
    ACTOR = "actor"             # Missing information about key actor
    TOPIC = "topic"             # Missing topic coverage
    EVIDENCE = "evidence"       # Missing supporting evidence
    GEOGRAPHIC = "geographic"   # Missing location coverage


@dataclass
class FindingRelationship:
    """Relationship between two findings.

    Represents an edge in the knowledge graph connecting
    two finding nodes.
    """
    source_finding_id: str
    target_finding_id: str
    relationship_type: RelationshipType
    description: str = ""
    strength: float = 1.0  # 0.0-1.0 relationship strength

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_finding_id": self.source_finding_id,
            "target_finding_id": self.target_finding_id,
            "relationship_type": self.relationship_type.value,
            "description": self.description,
            "strength": self.strength,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FindingRelationship":
        return cls(
            source_finding_id=data["source_finding_id"],
            target_finding_id=data["target_finding_id"],
            relationship_type=RelationshipType(data["relationship_type"]),
            description=data.get("description", ""),
            strength=data.get("strength", 1.0),
        )


@dataclass
class Contradiction:
    """A contradiction detected between findings or sources.

    Contradictions are valuable for investigative research as they
    often reveal truth or propaganda.
    """
    finding_id_1: str
    finding_id_2: str
    claim_1: str
    claim_2: str
    source_1: str
    source_2: str
    significance: str = ""  # Why this contradiction matters
    resolution_hint: Optional[str] = None  # Possible explanation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id_1": self.finding_id_1,
            "finding_id_2": self.finding_id_2,
            "claim_1": self.claim_1,
            "claim_2": self.claim_2,
            "source_1": self.source_1,
            "source_2": self.source_2,
            "significance": self.significance,
            "resolution_hint": self.resolution_hint,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Contradiction":
        return cls(
            finding_id_1=data["finding_id_1"],
            finding_id_2=data["finding_id_2"],
            claim_1=data["claim_1"],
            claim_2=data["claim_2"],
            source_1=data["source_1"],
            source_2=data["source_2"],
            significance=data.get("significance", ""),
            resolution_hint=data.get("resolution_hint"),
        )


@dataclass
class ResearchGap:
    """A gap identified in research coverage.

    Gaps indicate areas where additional research may be needed.
    """
    gap_type: GapType
    description: str
    suggested_queries: List[str] = field(default_factory=list)
    priority: str = "medium"  # high, medium, low
    related_finding_ids: List[str] = field(default_factory=list)

    # For temporal gaps
    gap_start: Optional[str] = None  # Date string
    gap_end: Optional[str] = None

    # For actor gaps
    missing_actor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_type": self.gap_type.value,
            "description": self.description,
            "suggested_queries": self.suggested_queries,
            "priority": self.priority,
            "related_finding_ids": self.related_finding_ids,
            "gap_start": self.gap_start,
            "gap_end": self.gap_end,
            "missing_actor": self.missing_actor,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchGap":
        return cls(
            gap_type=GapType(data["gap_type"]),
            description=data["description"],
            suggested_queries=data.get("suggested_queries", []),
            priority=data.get("priority", "medium"),
            related_finding_ids=data.get("related_finding_ids", []),
            gap_start=data.get("gap_start"),
            gap_end=data.get("gap_end"),
            missing_actor=data.get("missing_actor"),
        )


@dataclass
class CausalChain:
    """A chain of causal relationships between findings.

    Represents: A caused B caused C caused D
    """
    finding_ids: List[str] = field(default_factory=list)
    descriptions: List[str] = field(default_factory=list)  # Description of each link

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_ids": self.finding_ids,
            "descriptions": self.descriptions,
            "chain_length": len(self.finding_ids),
        }

    def add_link(self, finding_id: str, description: str = "") -> None:
        """Add a finding to the causal chain."""
        self.finding_ids.append(finding_id)
        if description:
            self.descriptions.append(description)


@dataclass
class RelationshipGraph:
    """Complete relationship graph for a research result.

    Contains all relationships, contradictions, gaps, and causal chains.
    """
    relationships: List[FindingRelationship] = field(default_factory=list)
    contradictions: List[Contradiction] = field(default_factory=list)
    gaps: List[ResearchGap] = field(default_factory=list)
    causal_chains: List[CausalChain] = field(default_factory=list)

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType,
        description: str = "",
    ) -> None:
        """Add a relationship to the graph."""
        self.relationships.append(FindingRelationship(
            source_finding_id=source_id,
            target_finding_id=target_id,
            relationship_type=rel_type,
            description=description,
        ))

    def add_contradiction(
        self,
        finding_id_1: str,
        finding_id_2: str,
        claim_1: str,
        claim_2: str,
        source_1: str,
        source_2: str,
        significance: str = "",
    ) -> None:
        """Add a contradiction to the graph."""
        self.contradictions.append(Contradiction(
            finding_id_1=finding_id_1,
            finding_id_2=finding_id_2,
            claim_1=claim_1,
            claim_2=claim_2,
            source_1=source_1,
            source_2=source_2,
            significance=significance,
        ))

    def add_gap(
        self,
        gap_type: GapType,
        description: str,
        suggested_queries: List[str] = None,
        priority: str = "medium",
    ) -> None:
        """Add a gap to the graph."""
        self.gaps.append(ResearchGap(
            gap_type=gap_type,
            description=description,
            suggested_queries=suggested_queries or [],
            priority=priority,
        ))

    def get_relationships_for(self, finding_id: str) -> List[FindingRelationship]:
        """Get all relationships involving a specific finding."""
        return [
            r for r in self.relationships
            if r.source_finding_id == finding_id or r.target_finding_id == finding_id
        ]

    def get_causes(self, finding_id: str) -> List[str]:
        """Get IDs of findings that caused this finding."""
        return [
            r.source_finding_id for r in self.relationships
            if r.target_finding_id == finding_id
            and r.relationship_type == RelationshipType.CAUSES
        ]

    def get_effects(self, finding_id: str) -> List[str]:
        """Get IDs of findings caused by this finding."""
        return [
            r.target_finding_id for r in self.relationships
            if r.source_finding_id == finding_id
            and r.relationship_type == RelationshipType.CAUSES
        ]

    def get_contradicting(self, finding_id: str) -> List[str]:
        """Get IDs of findings that contradict this finding."""
        result = []
        for c in self.contradictions:
            if c.finding_id_1 == finding_id:
                result.append(c.finding_id_2)
            elif c.finding_id_2 == finding_id:
                result.append(c.finding_id_1)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationships": [r.to_dict() for r in self.relationships],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "gaps": [g.to_dict() for g in self.gaps],
            "causal_chains": [c.to_dict() for c in self.causal_chains],
            "stats": {
                "total_relationships": len(self.relationships),
                "total_contradictions": len(self.contradictions),
                "total_gaps": len(self.gaps),
                "total_causal_chains": len(self.causal_chains),
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationshipGraph":
        return cls(
            relationships=[
                FindingRelationship.from_dict(r)
                for r in data.get("relationships", [])
            ],
            contradictions=[
                Contradiction.from_dict(c)
                for c in data.get("contradictions", [])
            ],
            gaps=[
                ResearchGap.from_dict(g)
                for g in data.get("gaps", [])
            ],
            causal_chains=[
                CausalChain(**c) for c in data.get("causal_chains", [])
            ],
        )
