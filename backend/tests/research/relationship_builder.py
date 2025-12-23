"""Relationship Builder Module.

Builds relationships between findings to create a knowledge graph:
- Identifies causal chains (A caused B)
- Finds supporting evidence (A supports B)
- Detects contradictions (A contradicts B)
- Identifies expansions (A expands on B)
- Maps temporal precedence (A precedes B)
- Detects research gaps
"""

import asyncio
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple

# Handle both relative and direct imports
try:
    from .inference_client import InferenceClient
    from .schemas.relationship import (
        RelationshipType,
        FindingRelationship,
        Contradiction,
        ResearchGap,
        GapType,
        CausalChain,
        RelationshipGraph,
    )
except ImportError:
    from inference_client import InferenceClient
    from schemas.relationship import (
        RelationshipType,
        FindingRelationship,
        Contradiction,
        ResearchGap,
        GapType,
        CausalChain,
        RelationshipGraph,
    )


@dataclass
class FindingInfo:
    """Simplified finding representation for relationship analysis."""

    id: str
    content: str
    finding_type: str
    summary: Optional[str] = None
    date_text: Optional[str] = None
    actors: List[str] = field(default_factory=list)


class RelationshipBuilder:
    """Builds a relationship graph from research findings."""

    def __init__(self, client: Optional[InferenceClient] = None):
        self.client = client or InferenceClient()

    async def build_graph(
        self,
        findings: List[FindingInfo],
        topic: str,
    ) -> RelationshipGraph:
        """Build a complete relationship graph from findings.

        Args:
            findings: List of findings to analyze
            topic: The research topic for context

        Returns:
            RelationshipGraph with all relationships and analysis
        """
        # Run relationship extraction and analysis in parallel
        relationships, contradictions, gaps, chains = await asyncio.gather(
            self._extract_relationships(findings, topic),
            self._detect_contradictions(findings, topic),
            self._identify_gaps(findings, topic),
            self._build_causal_chains(findings, topic),
        )

        return RelationshipGraph(
            relationships=relationships,
            contradictions=contradictions,
            gaps=gaps,
            causal_chains=chains,
        )

    async def _extract_relationships(
        self,
        findings: List[FindingInfo],
        topic: str,
    ) -> List[FindingRelationship]:
        """Extract relationships between findings."""

        if len(findings) < 2:
            return []

        # Format findings for prompt
        findings_text = "\n".join(
            f"[{f.id}] ({f.finding_type}) {f.content[:200]}"
            for f in findings[:20]  # Limit to prevent token overflow
        )

        prompt = f"""Analyze relationships between these research findings.

TOPIC: {topic}

FINDINGS:
{findings_text}

Identify relationships between findings. Types:
- CAUSES: Finding A led to/caused Finding B
- SUPPORTS: Finding A provides evidence for Finding B
- CONTRADICTS: Finding A conflicts with Finding B
- EXPANDS: Finding A adds detail to Finding B
- PRECEDES: Finding A happened before Finding B (temporal)
- INVOLVES: Findings share common actors/entities

Return JSON with relationships between finding IDs:
{{
    "relationships": [
        {{
            "source_id": "finding_id_1",
            "target_id": "finding_id_2",
            "relationship_type": "causes/supports/contradicts/expands/precedes/involves",
            "description": "Brief explanation of the relationship",
            "strength": 0.0-1.0
        }}
    ]
}}

Focus on the most significant relationships (max 15)."""

        result, _ = await self.client.generate_json(
            prompt,
            system_prompt="You are a research analyst building a knowledge graph.",
            temperature=0.3,
        )

        relationships = []
        for r in result.get("relationships", []):
            try:
                rel_type = RelationshipType(r.get("relationship_type", "involves").lower())
                relationships.append(FindingRelationship(
                    source_finding_id=r.get("source_id", ""),
                    target_finding_id=r.get("target_id", ""),
                    relationship_type=rel_type,
                    description=r.get("description", ""),
                    strength=float(r.get("strength", 0.5)),
                ))
            except (ValueError, KeyError):
                continue

        return relationships

    async def _detect_contradictions(
        self,
        findings: List[FindingInfo],
        topic: str,
    ) -> List[Contradiction]:
        """Detect contradictions between findings."""

        if len(findings) < 2:
            return []

        findings_text = "\n".join(
            f"[{f.id}] {f.content[:200]}"
            for f in findings[:20]
        )

        prompt = f"""Analyze these research findings for CONTRADICTIONS.

TOPIC: {topic}

FINDINGS:
{findings_text}

Identify any contradictions where:
- Two findings make conflicting claims
- Information from different sources disagrees
- There are logical inconsistencies
- Facts from one finding undermine another

Return JSON:
{{
    "contradictions": [
        {{
            "finding_id_1": "first finding ID",
            "finding_id_2": "second finding ID",
            "claim_1": "What the first finding claims",
            "claim_2": "What the second finding claims",
            "analysis": "Why these contradict and what it means",
            "resolution_needed": true/false,
            "possible_explanation": "Possible reason for contradiction"
        }}
    ]
}}

Only include genuine contradictions (not just different aspects of the same topic)."""

        result, _ = await self.client.generate_json(
            prompt,
            system_prompt="You are a fact-checker analyzing research for contradictions.",
            temperature=0.2,
        )

        contradictions = []
        for c in result.get("contradictions", []):
            contradictions.append(Contradiction(
                finding_id_1=c.get("finding_id_1", ""),
                finding_id_2=c.get("finding_id_2", ""),
                claim_1=c.get("claim_1", ""),
                claim_2=c.get("claim_2", ""),
                source_1=c.get("finding_id_1", ""),  # Use finding ID as source ref
                source_2=c.get("finding_id_2", ""),
                significance=c.get("analysis", ""),
                resolution_hint=c.get("possible_explanation", ""),
            ))

        return contradictions

    async def _identify_gaps(
        self,
        findings: List[FindingInfo],
        topic: str,
    ) -> List[ResearchGap]:
        """Identify gaps in the research."""

        findings_text = "\n".join(
            f"[{f.id}] ({f.finding_type}) {f.summary or f.content[:100]}"
            for f in findings[:20]
        )

        # Extract date range if present
        dates = [f.date_text for f in findings if f.date_text]
        date_context = f"Date range covered: {min(dates) if dates else 'N/A'} to {max(dates) if dates else 'N/A'}"

        prompt = f"""Analyze these research findings for GAPS - areas that should be explored but aren't.

TOPIC: {topic}
{date_context}

FINDINGS COLLECTED:
{findings_text}

Identify research gaps:
1. TEMPORAL GAPS: Time periods not covered (large date ranges with no findings)
2. ACTOR GAPS: Key actors mentioned but not explored
3. THEMATIC GAPS: Important aspects of the topic not addressed
4. CAUSAL GAPS: Missing links in cause-effect chains
5. PERSPECTIVE GAPS: Viewpoints not represented

Return JSON:
{{
    "gaps": [
        {{
            "gap_type": "temporal/actor/thematic/causal/perspective",
            "description": "What is missing",
            "importance": "high/medium/low",
            "suggested_query": "Search query to fill this gap",
            "related_finding_ids": ["IDs of findings that suggest this gap"]
        }}
    ]
}}

Focus on the most important gaps (max 8)."""

        result, _ = await self.client.generate_json(
            prompt,
            system_prompt="You are a research analyst identifying gaps in coverage.",
            temperature=0.3,
        )

        gaps = []
        for g in result.get("gaps", []):
            # Map string gap_type to GapType enum
            gap_type_str = g.get("gap_type", "topic").lower()
            gap_type_map = {
                "temporal": GapType.TEMPORAL,
                "actor": GapType.ACTOR,
                "thematic": GapType.TOPIC,
                "topic": GapType.TOPIC,
                "causal": GapType.EVIDENCE,
                "evidence": GapType.EVIDENCE,
                "perspective": GapType.TOPIC,
                "geographic": GapType.GEOGRAPHIC,
            }
            gap_type = gap_type_map.get(gap_type_str, GapType.TOPIC)

            gaps.append(ResearchGap(
                gap_type=gap_type,
                description=g.get("description", ""),
                priority=g.get("importance", "medium"),
                suggested_queries=[g.get("suggested_query", "")] if g.get("suggested_query") else [],
                related_finding_ids=g.get("related_finding_ids", []),
            ))

        return gaps

    async def _build_causal_chains(
        self,
        findings: List[FindingInfo],
        topic: str,
    ) -> List[CausalChain]:
        """Build causal chains from findings."""

        if len(findings) < 3:
            return []

        findings_text = "\n".join(
            f"[{f.id}] ({f.date_text or 'undated'}) {f.content[:150]}"
            for f in findings[:20]
        )

        prompt = f"""Analyze these research findings to build CAUSAL CHAINS.

TOPIC: {topic}

FINDINGS:
{findings_text}

A causal chain shows how events/actions led to other events/actions in sequence.
Example: Event A → caused → Event B → led to → Event C

Build causal chains that explain:
- How the situation developed over time
- What caused what
- The sequence of cause and effect

Return JSON:
{{
    "causal_chains": [
        {{
            "chain_name": "Name/title for this causal chain",
            "description": "What this chain explains",
            "links": [
                {{"finding_id": "id1", "role": "What role this finding plays"}},
                {{"finding_id": "id2", "role": "What role this finding plays"}},
                {{"finding_id": "id3", "role": "What role this finding plays"}}
            ],
            "overall_explanation": "Summary of the causal chain"
        }}
    ]
}}

Build 2-4 meaningful causal chains that help explain the topic."""

        result, _ = await self.client.generate_json(
            prompt,
            system_prompt="You are a research analyst building causal explanations.",
            temperature=0.3,
        )

        chains = []
        for c in result.get("causal_chains", []):
            links = []
            finding_ids = []
            descriptions = []

            for link in c.get("links", []):
                if isinstance(link, dict):
                    finding_ids.append(link.get("finding_id", ""))
                    descriptions.append(link.get("role", ""))

            chains.append(CausalChain(
                finding_ids=finding_ids,
                descriptions=descriptions,
            ))

        return chains


async def build_relationship_graph(
    findings: List[Dict[str, Any]],
    topic: str,
    client: Optional[InferenceClient] = None,
) -> RelationshipGraph:
    """Convenience function to build relationship graph.

    Args:
        findings: List of finding dicts with 'id', 'content', 'type' keys
        topic: Research topic
        client: Inference client

    Returns:
        Complete RelationshipGraph
    """
    # Convert dicts to FindingInfo
    finding_infos = []
    for i, f in enumerate(findings):
        finding_infos.append(FindingInfo(
            id=f.get("id", f"f_{i+1}"),
            content=f.get("content", ""),
            finding_type=f.get("type", "unknown"),
            summary=f.get("summary"),
            date_text=f.get("date_text"),
            actors=f.get("actors", []),
        ))

    builder = RelationshipBuilder(client)
    return await builder.build_graph(finding_infos, topic)
