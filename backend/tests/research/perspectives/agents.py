"""Perspective Agent Implementations.

Five specialized agents for multi-perspective analysis:
1. HistoricalAgent - Historical context and patterns
2. FinancialAgent - Economic motivations and impacts
3. JournalistAgent - Source credibility and contradictions
4. ConspiratorAgent - Hidden motivations and theories
5. NetworkAgent - Actor relationships and power dynamics
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .base import BasePerspectiveAgent, PerspectiveContext

# Handle both relative and direct imports
try:
    from ..schemas.perspective import (
        PerspectiveType,
        PerspectiveAnalysis,
        HistoricalAnalysis,
        FinancialAnalysis,
        JournalistAnalysis,
        ConspiratorAnalysis,
        NetworkAnalysis,
        SupportingEvidence,
        CounterEvidence,
        TheoryProbability,
        ContradictionDetail,
        RevealedRelationship,
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from schemas.perspective import (
        PerspectiveType,
        PerspectiveAnalysis,
        HistoricalAnalysis,
        FinancialAnalysis,
        JournalistAnalysis,
        ConspiratorAnalysis,
        NetworkAnalysis,
        SupportingEvidence,
        CounterEvidence,
        TheoryProbability,
        ContradictionDetail,
        RevealedRelationship,
    )


class HistoricalAgent(BasePerspectiveAgent):
    """Analyzes findings through historical context and patterns."""

    perspective_type = PerspectiveType.HISTORICAL
    name = "Historical Analyst"
    description = "Places events in historical context, identifies precedents and patterns"

    system_prompt = """You are a senior historian specializing in geopolitical history.

Your role is to:
1. Place current events in their proper historical context
2. Identify historical precedents and parallels
3. Recognize patterns that repeat across history
4. Explain the historical forces shaping current events
5. Identify long-term trends and their origins

Be specific about dates, cite historical events by name, and draw clear connections
between past and present. Your analysis should help readers understand WHY events
are unfolding as they are based on historical forces."""

    async def analyze_finding(
        self,
        finding_content: str,
        finding_type: str,
        context: PerspectiveContext,
    ) -> Dict[str, Any]:
        """Analyze a finding's historical significance."""

        prompt = f"""{self._build_context_prompt(context)}

FINDING TO ANALYZE:
Type: {finding_type}
Content: {finding_content}

Analyze this finding from a historical perspective:

1. What historical precedents relate to this finding?
2. What patterns from history does this reflect?
3. What long-term historical forces are at play?
4. How does this fit into the broader historical narrative?

Respond in JSON:
{{
    "historical_context": "Brief historical contextualization",
    "precedents": ["Historical precedent 1", "Historical precedent 2"],
    "patterns": ["Pattern 1", "Pattern 2"],
    "long_term_forces": ["Force 1", "Force 2"],
    "key_insight": "Most important historical insight"
}}"""

        return await self._generate_analysis(prompt)

    async def analyze_topic(
        self,
        context: PerspectiveContext,
    ) -> HistoricalAnalysis:
        """Provide comprehensive historical perspective on the topic."""

        findings_text = "\n".join(f"- {f}" for f in context.finding_summaries[:15])

        prompt = f"""{self._build_context_prompt(context)}

KEY FINDINGS:
{findings_text}

Provide a comprehensive HISTORICAL PERSPECTIVE analysis:

1. Place this topic in historical context (centuries/decades of relevant history)
2. Identify 3-5 key historical precedents with specific dates
3. Identify 2-3 recurring historical patterns
4. What historical forces explain current developments?
5. Key insights and warnings based on historical knowledge

Respond in JSON:
{{
    "analysis": "2-3 paragraph historical narrative placing events in context",
    "historical_parallels": ["Parallel event 1 with date", "Parallel event 2 with date"],
    "historical_patterns": ["Recurring pattern 1", "Recurring pattern 2"],
    "likely_consequences": ["Likely consequence 1", "Likely consequence 2"],
    "implications": ["Key implication 1", "Key implication 2"]
}}"""

        result = await self._generate_analysis(prompt)

        return HistoricalAnalysis(
            analysis=result.get("analysis", ""),
            historical_parallels=result.get("historical_parallels", []),
            historical_patterns=result.get("historical_patterns", []),
            likely_consequences=result.get("likely_consequences", []),
            implications=result.get("implications", []),
        )


class FinancialAgent(BasePerspectiveAgent):
    """Analyzes findings through economic and financial lens."""

    perspective_type = PerspectiveType.FINANCIAL
    name = "Financial Analyst"
    description = "Analyzes economic motivations, financial flows, and stakeholder interests"

    system_prompt = """You are a senior financial analyst specializing in geopolitical economics.

Your role is to:
1. Identify the economic motivations behind political actions
2. Trace financial flows and their implications
3. Identify stakeholders and their financial interests
4. Analyze economic sanctions, trade relationships, and market impacts
5. Follow the money to understand true motivations

Be specific about dollar amounts, trade volumes, and economic metrics when possible.
Your analysis should reveal the financial interests driving events."""

    async def analyze_finding(
        self,
        finding_content: str,
        finding_type: str,
        context: PerspectiveContext,
    ) -> Dict[str, Any]:
        """Analyze a finding's financial implications."""

        prompt = f"""{self._build_context_prompt(context)}

FINDING TO ANALYZE:
Type: {finding_type}
Content: {finding_content}

Analyze this finding from a FINANCIAL/ECONOMIC perspective:

1. What economic motivations might be at play?
2. Who benefits financially from this?
3. What financial flows or interests are involved?
4. What are the economic implications?

Respond in JSON:
{{
    "economic_context": "Brief economic context",
    "beneficiaries": ["Who benefits financially"],
    "financial_interests": ["Key financial interests at stake"],
    "economic_impacts": ["Economic impact 1", "Economic impact 2"],
    "follow_the_money": "Key insight about financial motivations"
}}"""

        return await self._generate_analysis(prompt)

    async def analyze_topic(
        self,
        context: PerspectiveContext,
    ) -> FinancialAnalysis:
        """Provide comprehensive financial perspective on the topic."""

        findings_text = "\n".join(f"- {f}" for f in context.finding_summaries[:15])

        prompt = f"""{self._build_context_prompt(context)}

KEY FINDINGS:
{findings_text}

Provide a comprehensive FINANCIAL/ECONOMIC PERSPECTIVE analysis:

1. What are the major economic motivations driving this situation?
2. Who are the key financial stakeholders and what are their interests?
3. What financial flows (trade, investment, sanctions) are relevant?
4. What economic sectors are impacted?
5. What does "following the money" reveal?

Respond in JSON:
{{
    "analysis": "2-3 paragraph financial analysis narrative",
    "cui_bono": ["Who benefits 1", "Who benefits 2"],
    "financial_mechanisms": ["Financial mechanism 1", "Financial mechanism 2"],
    "money_flows": [
        {{"from": "Entity A", "to": "Entity B", "mechanism": "Trade/Investment/etc"}}
    ],
    "sanctions_relevance": "How sanctions play a role",
    "implications": ["Economic implication 1", "Economic implication 2"]
}}"""

        result = await self._generate_analysis(prompt)

        return FinancialAnalysis(
            analysis=result.get("analysis", ""),
            cui_bono=result.get("cui_bono", []),
            financial_mechanisms=result.get("financial_mechanisms", []),
            money_flows=result.get("money_flows", []),
            sanctions_relevance=result.get("sanctions_relevance", ""),
            implications=result.get("implications", []),
        )


class JournalistAgent(BasePerspectiveAgent):
    """Analyzes source credibility and identifies contradictions."""

    perspective_type = PerspectiveType.JOURNALIST
    name = "Investigative Journalist"
    description = "Evaluates source credibility, identifies propaganda, finds contradictions"

    system_prompt = """You are a senior investigative journalist specializing in fact-checking.

Your role is to:
1. Critically evaluate source credibility and potential biases
2. Identify propaganda, misinformation, and spin
3. Find contradictions between different claims or sources
4. Distinguish between facts, claims, and opinions
5. Identify what information is missing or being obscured

Be skeptical but fair. Note when sources have potential conflicts of interest.
Your analysis should help readers understand what to trust and what to question."""

    async def analyze_finding(
        self,
        finding_content: str,
        finding_type: str,
        context: PerspectiveContext,
    ) -> Dict[str, Any]:
        """Analyze a finding for credibility and contradictions."""

        prompt = f"""{self._build_context_prompt(context)}

FINDING TO ANALYZE:
Type: {finding_type}
Content: {finding_content}

Analyze this finding from a JOURNALIST'S CRITICAL perspective:

1. How credible is this claim? What would need verification?
2. Are there potential biases or propaganda elements?
3. Does this contradict other known information?
4. What's missing from this account?

Respond in JSON:
{{
    "credibility_assessment": "Assessment of claim credibility",
    "verification_needed": ["What needs verification"],
    "potential_biases": ["Potential bias 1"],
    "propaganda_indicators": ["Any propaganda red flags"],
    "contradictions": ["Any contradictions with other info"],
    "missing_context": ["What's missing"],
    "trust_level": "high/medium/low/unverified"
}}"""

        return await self._generate_analysis(prompt)

    async def analyze_topic(
        self,
        context: PerspectiveContext,
    ) -> JournalistAnalysis:
        """Provide comprehensive journalist perspective on the topic."""

        findings_text = "\n".join(f"- {f}" for f in context.finding_summaries[:15])

        prompt = f"""{self._build_context_prompt(context)}

KEY FINDINGS:
{findings_text}

Provide a comprehensive INVESTIGATIVE JOURNALISM analysis:

1. Evaluate the overall credibility of sources in this topic
2. Identify any propaganda or misinformation patterns
3. Find contradictions between different claims
4. What important questions remain unanswered?
5. What would a thorough fact-check reveal?

Respond in JSON:
{{
    "analysis": "2-3 paragraph critical analysis narrative",
    "contradictions_found": [
        {{"claim1": "First claim", "claim2": "Contradicting claim", "source1": "Source A", "source2": "Source B", "significance": "Why this matters"}}
    ],
    "propaganda_indicators": ["Propaganda pattern 1", "Propaganda pattern 2"],
    "unanswered_questions": ["Question 1", "Question 2"],
    "verification_status": "verified/disputed/unverified",
    "source_bias_notes": ["Bias note 1", "Bias note 2"],
    "implications": ["Implication for understanding truth"]
}}"""

        result = await self._generate_analysis(prompt)

        # Parse contradictions
        contradictions = []
        for c in result.get("contradictions_found", []):
            if isinstance(c, dict):
                contradictions.append(ContradictionDetail(
                    claim1=c.get("claim1", ""),
                    claim2=c.get("claim2", ""),
                    source1=c.get("source1", ""),
                    source2=c.get("source2", ""),
                    significance=c.get("significance", ""),
                ))

        return JournalistAnalysis(
            analysis=result.get("analysis", ""),
            contradictions_found=contradictions,
            propaganda_indicators=result.get("propaganda_indicators", []),
            unanswered_questions=result.get("unanswered_questions", []),
            verification_status=result.get("verification_status", "unverified"),
            source_bias_notes=result.get("source_bias_notes", []),
            implications=result.get("implications", []),
        )


class ConspiratorAgent(BasePerspectiveAgent):
    """Proposes probable hidden motivations and theories."""

    perspective_type = PerspectiveType.CONSPIRATOR
    name = "Intelligence Analyst"
    description = "Expert analyst proposing probable hidden motivations and theories"

    system_prompt = """You are a senior intelligence analyst with deep expertise in geopolitics,
military strategy, and covert operations.

Your role is to:
1. Propose PROBABLE theories about hidden motivations (not wild speculation)
2. Identify what powerful actors might not want publicly known
3. Connect dots between seemingly unrelated events
4. Consider what intelligence agencies might know but not share
5. Propose theories grounded in evidence with probability assessments

IMPORTANT: You propose PROBABLE theories based on:
- Historical patterns of similar situations
- Known behaviors of key actors
- Evidence that suggests hidden motivations
- Logical deduction from available facts

Rate each theory as: 'possible' (could be true), 'probable' (likely true),
or 'likely' (probably true based on evidence pattern).

You are NOT a conspiracy theorist. You are a sophisticated analyst who understands
that official narratives often don't tell the whole story."""

    async def analyze_finding(
        self,
        finding_content: str,
        finding_type: str,
        context: PerspectiveContext,
    ) -> Dict[str, Any]:
        """Analyze a finding for hidden motivations."""

        prompt = f"""{self._build_context_prompt(context)}

FINDING TO ANALYZE:
Type: {finding_type}
Content: {finding_content}

Analyze this finding like an INTELLIGENCE ANALYST looking for hidden motivations:

1. What hidden motivations might explain this?
2. What might powerful actors not want known?
3. What would an intelligence analyst suspect?
4. What evidence supports these suspicions?

Respond in JSON:
{{
    "surface_narrative": "What the official story says",
    "hidden_motivations": ["Possible hidden motivation"],
    "cui_bono": "Who truly benefits and how",
    "intelligence_assessment": "What an intelligence analyst would note",
    "probability": "possible/probable/likely",
    "supporting_evidence": ["Evidence supporting this view"]
}}"""

        return await self._generate_analysis(prompt, temperature=0.5)

    async def analyze_topic(
        self,
        context: PerspectiveContext,
    ) -> ConspiratorAnalysis:
        """Provide comprehensive intelligence analyst perspective."""

        findings_text = "\n".join(f"- {f}" for f in context.finding_summaries[:15])

        prompt = f"""{self._build_context_prompt(context)}

KEY FINDINGS:
{findings_text}

Provide a comprehensive INTELLIGENCE ANALYST perspective:

Propose ONE well-reasoned theory about hidden motivations that explains
patterns in this topic. This should be a PROBABLE theory based on evidence,
not wild speculation.

Include:
1. The theory itself
2. Supporting evidence from the findings
3. Counter-evidence that challenges the theory
4. Hidden motivations this theory reveals
5. Probability assessment

Respond in JSON:
{{
    "analysis": "2-3 paragraph intelligence analysis narrative",
    "theory": "Clear statement of the probable hidden motivation/theory",
    "theory_probability": "possible/probable/likely",
    "supporting_evidence": [
        {{"finding_id": "ref", "how_it_supports": "Why it supports the theory"}}
    ],
    "counter_evidence": [
        {{"finding_id": "ref", "how_it_contradicts": "How it challenges the theory"}}
    ],
    "hidden_motivations": ["Hidden motivation 1", "Hidden motivation 2"],
    "implications_if_true": ["Implication 1", "Implication 2"],
    "implications": ["Key implication"]
}}"""

        result = await self._generate_analysis(prompt, temperature=0.5)

        # Parse probability
        prob_str = result.get("theory_probability", "possible").lower()
        probability = TheoryProbability.POSSIBLE
        if prob_str == "probable":
            probability = TheoryProbability.PROBABLE
        elif prob_str == "likely":
            probability = TheoryProbability.LIKELY

        # Parse evidence
        supporting = []
        for e in result.get("supporting_evidence", []):
            if isinstance(e, dict):
                supporting.append(SupportingEvidence(
                    finding_id=e.get("finding_id", ""),
                    how_it_supports=e.get("how_it_supports", ""),
                ))

        counter = []
        for e in result.get("counter_evidence", []):
            if isinstance(e, dict):
                counter.append(CounterEvidence(
                    finding_id=e.get("finding_id", ""),
                    how_it_contradicts=e.get("how_it_contradicts", ""),
                ))

        return ConspiratorAnalysis(
            analysis=result.get("analysis", ""),
            theory=result.get("theory", ""),
            theory_probability=probability,
            supporting_evidence=supporting,
            counter_evidence=counter,
            hidden_motivations=result.get("hidden_motivations", []),
            implications_if_true=result.get("implications_if_true", []),
            implications=result.get("implications", []),
        )


class NetworkAgent(BasePerspectiveAgent):
    """Maps actor relationships and power dynamics."""

    perspective_type = PerspectiveType.NETWORK
    name = "Network Analyst"
    description = "Maps relationships between actors and analyzes power dynamics"

    system_prompt = """You are a network analyst specializing in mapping relationships
between political actors, organizations, and power structures.

Your role is to:
1. Identify key actors and their roles
2. Map relationships between actors (alliances, conflicts, dependencies)
3. Identify power dynamics and hierarchies
4. Find hidden connections and influence networks
5. Understand how information and power flow

Your analysis should create a clear picture of WHO is connected to WHOM
and HOW those relationships shape events."""

    async def analyze_finding(
        self,
        finding_content: str,
        finding_type: str,
        context: PerspectiveContext,
    ) -> Dict[str, Any]:
        """Analyze a finding for actor relationships."""

        prompt = f"""{self._build_context_prompt(context)}

FINDING TO ANALYZE:
Type: {finding_type}
Content: {finding_content}

Analyze this finding for ACTOR RELATIONSHIPS and NETWORK dynamics:

1. What actors are involved or implied?
2. What relationships does this reveal?
3. What power dynamics are at play?
4. How does this connect to the broader network?

Respond in JSON:
{{
    "actors_identified": ["Actor 1", "Actor 2"],
    "relationships": [
        {{"actor_1": "Name", "actor_2": "Name", "relationship": "type", "description": "details"}}
    ],
    "power_dynamics": "Description of power relationships",
    "network_insight": "Key insight about the network"
}}"""

        return await self._generate_analysis(prompt)

    async def analyze_topic(
        self,
        context: PerspectiveContext,
    ) -> NetworkAnalysis:
        """Provide comprehensive network analysis of the topic."""

        findings_text = "\n".join(f"- {f}" for f in context.finding_summaries[:15])
        actors_text = ", ".join(context.actors[:15]) if context.actors else "Not specified"

        prompt = f"""{self._build_context_prompt(context)}

KEY FINDINGS:
{findings_text}

KNOWN ACTORS: {actors_text}

Provide a comprehensive NETWORK ANALYSIS:

1. Map the key actors and their roles
2. Identify relationships between actors (allies, enemies, dependencies)
3. Analyze power dynamics and hierarchies
4. Identify key power brokers and influencers
5. Map the overall network structure

Respond in JSON:
{{
    "analysis": "2-3 paragraph network analysis narrative",
    "relationships_revealed": [
        {{"actor1": "Name", "actor2": "Name", "relationship_type": "ally/enemy/dependent", "evidence": "Evidence for relationship"}}
    ],
    "intermediaries": ["Actor who bridges groups"],
    "network_patterns": ["Pattern in the network structure"],
    "hidden_connections": ["Unexpected connection between actors"],
    "implications": ["Implication of network structure"]
}}"""

        result = await self._generate_analysis(prompt)

        # Parse relationships
        relationships = []
        for r in result.get("relationships_revealed", []):
            if isinstance(r, dict):
                relationships.append(RevealedRelationship(
                    actor1=r.get("actor1", ""),
                    actor2=r.get("actor2", ""),
                    relationship_type=r.get("relationship_type", "related"),
                    evidence=r.get("evidence", ""),
                ))

        return NetworkAnalysis(
            analysis=result.get("analysis", ""),
            relationships_revealed=relationships,
            intermediaries=result.get("intermediaries", []),
            network_patterns=result.get("network_patterns", []),
            hidden_connections=result.get("hidden_connections", []),
            implications=result.get("implications", []),
        )
