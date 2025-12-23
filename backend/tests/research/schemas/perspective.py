"""Perspective analysis schemas.

Each perspective agent produces a specific analysis type
attached to individual findings.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class PerspectiveType(Enum):
    """Types of perspective analyses available."""
    HISTORICAL = "historical"
    FINANCIAL = "financial"
    JOURNALIST = "journalist"
    CONSPIRATOR = "conspirator"
    NETWORK = "network"


class TheoryProbability(Enum):
    """Probability rating for conspirator theories."""
    POSSIBLE = "possible"      # >20% probability
    PROBABLE = "probable"      # >50% probability
    LIKELY = "likely"          # >70% probability


@dataclass
class PerspectiveAnalysis:
    """Base class for perspective analysis attached to a finding."""
    perspective_type: PerspectiveType
    analysis: str
    implications: List[str] = field(default_factory=list)
    related_finding_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "perspective_type": self.perspective_type.value,
            "analysis": self.analysis,
            "implications": self.implications,
            "related_finding_ids": self.related_finding_ids,
        }


@dataclass
class HistoricalAnalysis(PerspectiveAnalysis):
    """Historical perspective analysis.

    Focus: Precedents, patterns, cycles, historical context
    """
    perspective_type: PerspectiveType = field(default=PerspectiveType.HISTORICAL, init=False)
    historical_parallels: List[str] = field(default_factory=list)
    historical_patterns: List[str] = field(default_factory=list)
    likely_consequences: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "historical_parallels": self.historical_parallels,
            "historical_patterns": self.historical_patterns,
            "likely_consequences": self.likely_consequences,
        })
        return base


@dataclass
class FinancialAnalysis(PerspectiveAnalysis):
    """Financial perspective analysis.

    Focus: Money trails, cui bono, sanctions, economic leverage
    """
    perspective_type: PerspectiveType = field(default=PerspectiveType.FINANCIAL, init=False)
    cui_bono: List[str] = field(default_factory=list)  # Who benefits
    financial_mechanisms: List[str] = field(default_factory=list)
    money_flows: List[Dict[str, str]] = field(default_factory=list)  # from, to, mechanism
    sanctions_relevance: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "cui_bono": self.cui_bono,
            "financial_mechanisms": self.financial_mechanisms,
            "money_flows": self.money_flows,
            "sanctions_relevance": self.sanctions_relevance,
        })
        return base


@dataclass
class ContradictionDetail:
    """Detail of a contradiction found between sources."""
    claim1: str
    claim2: str
    source1: str
    source2: str
    significance: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim1": self.claim1,
            "claim2": self.claim2,
            "source1": self.source1,
            "source2": self.source2,
            "significance": self.significance,
        }


@dataclass
class JournalistAnalysis(PerspectiveAnalysis):
    """Investigative journalist perspective analysis.

    Focus: Contradictions, propaganda detection, fact-checking, source verification
    """
    perspective_type: PerspectiveType = field(default=PerspectiveType.JOURNALIST, init=False)
    contradictions_found: List[ContradictionDetail] = field(default_factory=list)
    propaganda_indicators: List[str] = field(default_factory=list)
    unanswered_questions: List[str] = field(default_factory=list)
    verification_status: str = "unverified"  # verified, disputed, unverified
    source_bias_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "contradictions_found": [c.to_dict() for c in self.contradictions_found],
            "propaganda_indicators": self.propaganda_indicators,
            "unanswered_questions": self.unanswered_questions,
            "verification_status": self.verification_status,
            "source_bias_notes": self.source_bias_notes,
        })
        return base


@dataclass
class SupportingEvidence:
    """Evidence supporting a theory."""
    finding_id: str
    how_it_supports: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "how_it_supports": self.how_it_supports,
        }


@dataclass
class CounterEvidence:
    """Evidence contradicting a theory."""
    finding_id: str
    how_it_contradicts: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "how_it_contradicts": self.how_it_contradicts,
        }


@dataclass
class ConspiratorAnalysis(PerspectiveAnalysis):
    """Conspirator/theorist perspective analysis.

    Focus: Probable theories explaining events based on deep domain knowledge.
    NOT a conspiracy theorist - a rigorous analyst who:
    - Forms theories based on evidence
    - Acknowledges counter-evidence
    - Rates probability honestly
    """
    perspective_type: PerspectiveType = field(default=PerspectiveType.CONSPIRATOR, init=False)
    theory: str = ""
    theory_probability: TheoryProbability = TheoryProbability.POSSIBLE
    supporting_evidence: List[SupportingEvidence] = field(default_factory=list)
    counter_evidence: List[CounterEvidence] = field(default_factory=list)
    hidden_motivations: List[str] = field(default_factory=list)
    implications_if_true: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "theory": self.theory,
            "theory_probability": self.theory_probability.value,
            "supporting_evidence": [e.to_dict() for e in self.supporting_evidence],
            "counter_evidence": [e.to_dict() for e in self.counter_evidence],
            "hidden_motivations": self.hidden_motivations,
            "implications_if_true": self.implications_if_true,
        })
        return base


@dataclass
class RevealedRelationship:
    """A relationship revealed by network analysis."""
    actor1: str
    actor2: str
    relationship_type: str
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actor1": self.actor1,
            "actor2": self.actor2,
            "relationship_type": self.relationship_type,
            "evidence": self.evidence,
        }


@dataclass
class NetworkAnalysis(PerspectiveAnalysis):
    """Network analyst perspective analysis.

    Focus: Relationship mapping, hidden connections, influence networks
    """
    perspective_type: PerspectiveType = field(default=PerspectiveType.NETWORK, init=False)
    relationships_revealed: List[RevealedRelationship] = field(default_factory=list)
    intermediaries: List[str] = field(default_factory=list)
    network_patterns: List[str] = field(default_factory=list)
    hidden_connections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "relationships_revealed": [r.to_dict() for r in self.relationships_revealed],
            "intermediaries": self.intermediaries,
            "network_patterns": self.network_patterns,
            "hidden_connections": self.hidden_connections,
        })
        return base


# Factory function to create perspective from dict
def perspective_from_dict(
    perspective_type: str,
    data: Dict[str, Any]
) -> PerspectiveAnalysis:
    """Create appropriate perspective analysis from dictionary."""

    ptype = PerspectiveType(perspective_type)

    if ptype == PerspectiveType.HISTORICAL:
        return HistoricalAnalysis(
            analysis=data.get("analysis", ""),
            implications=data.get("implications", []),
            related_finding_ids=data.get("related_finding_ids", []),
            historical_parallels=data.get("historical_parallels", []),
            historical_patterns=data.get("historical_patterns", []),
            likely_consequences=data.get("likely_consequences", []),
        )

    elif ptype == PerspectiveType.FINANCIAL:
        return FinancialAnalysis(
            analysis=data.get("analysis", ""),
            implications=data.get("implications", []),
            related_finding_ids=data.get("related_finding_ids", []),
            cui_bono=data.get("cui_bono", []),
            financial_mechanisms=data.get("financial_mechanisms", []),
            money_flows=data.get("money_flows", []),
            sanctions_relevance=data.get("sanctions_relevance"),
        )

    elif ptype == PerspectiveType.JOURNALIST:
        contradictions = [
            ContradictionDetail(**c) for c in data.get("contradictions_found", [])
        ]
        return JournalistAnalysis(
            analysis=data.get("analysis", ""),
            implications=data.get("implications", []),
            related_finding_ids=data.get("related_finding_ids", []),
            contradictions_found=contradictions,
            propaganda_indicators=data.get("propaganda_indicators", []),
            unanswered_questions=data.get("unanswered_questions", []),
            verification_status=data.get("verification_status", "unverified"),
            source_bias_notes=data.get("source_bias_notes", []),
        )

    elif ptype == PerspectiveType.CONSPIRATOR:
        supporting = [
            SupportingEvidence(**e) for e in data.get("supporting_evidence", [])
        ]
        counter = [
            CounterEvidence(**e) for e in data.get("counter_evidence", [])
        ]
        return ConspiratorAnalysis(
            analysis=data.get("analysis", ""),
            implications=data.get("implications", []),
            related_finding_ids=data.get("related_finding_ids", []),
            theory=data.get("theory", ""),
            theory_probability=TheoryProbability(data.get("theory_probability", "possible")),
            supporting_evidence=supporting,
            counter_evidence=counter,
            hidden_motivations=data.get("hidden_motivations", []),
            implications_if_true=data.get("implications_if_true", []),
        )

    elif ptype == PerspectiveType.NETWORK:
        relationships = [
            RevealedRelationship(**r) for r in data.get("relationships_revealed", [])
        ]
        return NetworkAnalysis(
            analysis=data.get("analysis", ""),
            implications=data.get("implications", []),
            related_finding_ids=data.get("related_finding_ids", []),
            relationships_revealed=relationships,
            intermediaries=data.get("intermediaries", []),
            network_patterns=data.get("network_patterns", []),
            hidden_connections=data.get("hidden_connections", []),
        )

    else:
        return PerspectiveAnalysis(
            perspective_type=ptype,
            analysis=data.get("analysis", ""),
            implications=data.get("implications", []),
            related_finding_ids=data.get("related_finding_ids", []),
        )


# ============================================
# FINDING-LEVEL PERSPECTIVE ANALYSES
# Lighter-weight analyses attached to individual findings
# ============================================

@dataclass
class FindingPerspectiveBase:
    """Base class for finding-level perspective analysis."""
    finding_id: str
    perspective_type: PerspectiveType
    key_insight: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "perspective_type": self.perspective_type.value,
            "key_insight": self.key_insight,
        }


@dataclass
class FindingHistoricalAnalysis(FindingPerspectiveBase):
    """Historical context for a single finding."""
    perspective_type: PerspectiveType = field(default=PerspectiveType.HISTORICAL, init=False)
    historical_context: str = ""
    precedents: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "historical_context": self.historical_context,
            "precedents": self.precedents,
            "patterns": self.patterns,
        })
        return base


@dataclass
class FindingFinancialAnalysis(FindingPerspectiveBase):
    """Financial context for a single finding."""
    perspective_type: PerspectiveType = field(default=PerspectiveType.FINANCIAL, init=False)
    economic_context: str = ""
    beneficiaries: List[str] = field(default_factory=list)
    follow_the_money: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "economic_context": self.economic_context,
            "beneficiaries": self.beneficiaries,
            "follow_the_money": self.follow_the_money,
        })
        return base


@dataclass
class FindingJournalistAnalysis(FindingPerspectiveBase):
    """Journalist assessment for a single finding."""
    perspective_type: PerspectiveType = field(default=PerspectiveType.JOURNALIST, init=False)
    source_assessment: str = ""
    red_flags: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "source_assessment": self.source_assessment,
            "red_flags": self.red_flags,
            "questions": self.questions,
        })
        return base


@dataclass
class FindingConspiratorAnalysis(FindingPerspectiveBase):
    """Alternative theory perspective for a single finding."""
    perspective_type: PerspectiveType = field(default=PerspectiveType.CONSPIRATOR, init=False)
    alternative_explanation: str = ""
    probability: str = "possible"  # possible, probable, likely
    supporting_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "alternative_explanation": self.alternative_explanation,
            "probability": self.probability,
            "supporting_evidence": self.supporting_evidence,
        })
        return base


@dataclass
class FindingNetworkAnalysis(FindingPerspectiveBase):
    """Network analysis for a single finding."""
    perspective_type: PerspectiveType = field(default=PerspectiveType.NETWORK, init=False)
    actor_role: str = ""
    connections: List[str] = field(default_factory=list)
    power_dynamics: str = ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "actor_role": self.actor_role,
            "connections": self.connections,
            "power_dynamics": self.power_dynamics,
        })
        return base


@dataclass
class FindingPerspectives:
    """Container for all perspective analyses on a single finding."""
    finding_id: str
    finding_content: str
    finding_summary: Optional[str] = None

    historical: Optional[FindingHistoricalAnalysis] = None
    financial: Optional[FindingFinancialAnalysis] = None
    journalist: Optional[FindingJournalistAnalysis] = None
    conspirator: Optional[FindingConspiratorAnalysis] = None
    network: Optional[FindingNetworkAnalysis] = None

    def get_all_analyses(self) -> List[FindingPerspectiveBase]:
        """Get all non-None perspective analyses."""
        analyses = []
        if self.historical:
            analyses.append(self.historical)
        if self.financial:
            analyses.append(self.financial)
        if self.journalist:
            analyses.append(self.journalist)
        if self.conspirator:
            analyses.append(self.conspirator)
        if self.network:
            analyses.append(self.network)
        return analyses

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "finding_content": self.finding_content,
            "finding_summary": self.finding_summary,
            "perspectives": {
                "historical": self.historical.to_dict() if self.historical else None,
                "financial": self.financial.to_dict() if self.financial else None,
                "journalist": self.journalist.to_dict() if self.journalist else None,
                "conspirator": self.conspirator.to_dict() if self.conspirator else None,
                "network": self.network.to_dict() if self.network else None,
            }
        }


def finding_perspective_from_dict(
    perspective_type: str,
    data: Dict[str, Any],
    finding_id: str,
) -> FindingPerspectiveBase:
    """Create appropriate finding-level perspective analysis from dictionary."""

    ptype = PerspectiveType(perspective_type)

    if ptype == PerspectiveType.HISTORICAL:
        return FindingHistoricalAnalysis(
            finding_id=finding_id,
            key_insight=data.get("key_insight", ""),
            historical_context=data.get("historical_context", ""),
            precedents=data.get("precedents", []),
            patterns=data.get("patterns", []),
        )

    elif ptype == PerspectiveType.FINANCIAL:
        return FindingFinancialAnalysis(
            finding_id=finding_id,
            key_insight=data.get("key_insight", ""),
            economic_context=data.get("economic_context", ""),
            beneficiaries=data.get("beneficiaries", []),
            follow_the_money=data.get("follow_the_money", ""),
        )

    elif ptype == PerspectiveType.JOURNALIST:
        return FindingJournalistAnalysis(
            finding_id=finding_id,
            key_insight=data.get("key_insight", ""),
            source_assessment=data.get("source_assessment", ""),
            red_flags=data.get("red_flags", []),
            questions=data.get("questions", []),
        )

    elif ptype == PerspectiveType.CONSPIRATOR:
        return FindingConspiratorAnalysis(
            finding_id=finding_id,
            key_insight=data.get("key_insight", ""),
            alternative_explanation=data.get("alternative_explanation", ""),
            probability=data.get("probability", "possible"),
            supporting_evidence=data.get("supporting_evidence", []),
        )

    elif ptype == PerspectiveType.NETWORK:
        return FindingNetworkAnalysis(
            finding_id=finding_id,
            key_insight=data.get("key_insight", ""),
            actor_role=data.get("actor_role", ""),
            connections=data.get("connections", []),
            power_dynamics=data.get("power_dynamics", ""),
        )

    else:
        return FindingPerspectiveBase(
            finding_id=finding_id,
            perspective_type=ptype,
            key_insight=data.get("key_insight", ""),
        )
