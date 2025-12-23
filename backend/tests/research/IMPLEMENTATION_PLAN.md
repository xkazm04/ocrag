# Research System Redesign - Implementation Plan

## Overview

Redesign the research system to produce a **finding-centric knowledge graph** where each finding is enriched with multiple perspective analyses, linked to sources, actors, and related findings through causal/temporal relationships.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER QUERY                                     │
│            "Why did the Russia-Ukraine war start? (2014-2024)"          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    QUERY DECOMPOSER (OpenRouter)                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Detects: Large date range (10 years), complex multi-faceted     │    │
│  │ Output: Split into 3 research batches                            │    │
│  │   Batch 1: "Origins and Euromaidan (2013-2014)"                  │    │
│  │   Batch 2: "Donbas conflict and Minsk accords (2015-2021)"       │    │
│  │   Batch 3: "Full-scale invasion (2022-2024)"                     │    │
│  │ Metadata: { merge_strategy: "chronological", overlap_events: [] }│    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│   RESEARCH BATCH 1   │ │   RESEARCH BATCH 2   │ │   RESEARCH BATCH 3   │
│  (Gemini + Search)   │ │  (Gemini + Search)   │ │  (Gemini + Search)   │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FINDING EXTRACTOR                                │
│                    Produces: List[Finding] with                          │
│                    - content, type, date, actors                         │
│                    - source_refs (which sources support this)            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PERSPECTIVE ENRICHMENT (OpenRouter)                   │
│  For each Finding, run parallel perspective agents:                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │ Historical  │ │ Financial   │ │ Journalist  │ │ Conspirator │        │
│  │  Analyst    │ │  Analyst    │ │ (Fact-check)│ │ (Theorist)  │        │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘        │
│  Each produces: { perspective_type, analysis, implications,              │
│                   related_findings[], theory_probability? }              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      RELATIONSHIP BUILDER                                │
│  Links findings via: causes, supports, contradicts, expands, precedes    │
│  Detects: Contradictions, gaps, patterns                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        KNOWLEDGE GRAPH OUTPUT                            │
│  Findings + Perspectives + Relationships + Gaps + Contradictions         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Dual-Client Architecture

### 1. Gemini Native Client (google-genai SDK)
**Purpose**: Web search and grounded research
**Used for**:
- Query execution with Google Search
- Source gathering and synthesis
- Initial finding extraction

```python
from gemini_client import GeminiResearchClient, SearchMode

# For web search tasks
search_client = GeminiResearchClient(search_mode=SearchMode.GROUNDED)
response = await search_client.grounded_search(query)
```

### 2. OpenRouter Client (Gemini 2.0 Flash)
**Purpose**: Fast, cheap inference without web search
**Used for**:
- Query decomposition
- Perspective analysis (all 4+ perspectives)
- Relationship building
- Gap analysis
- Pattern detection

```python
from openrouter_client import OpenRouterClient

# For inference-only tasks (no search)
inference_client = OpenRouterClient(model="google/gemini-2.0-flash-001")
response = await inference_client.generate_json(prompt, system_prompt)
```

**Cost comparison** (per 1M tokens):
- Gemini with Search: ~$0.075 input / $0.30 output + search costs
- OpenRouter Gemini Flash: ~$0.10 input / $0.40 output (no search overhead)

---

## Component Design

### 1. Query Decomposer

**File**: `decomposer.py`

**Triggers decomposition when**:
- Date range > 3 years
- Multiple distinct topics detected
- Query complexity score > threshold

**Output schema**:
```python
@dataclass
class DecomposedQuery:
    original_query: str
    requires_decomposition: bool
    batches: List[ResearchBatch]
    merge_strategy: str  # "chronological", "thematic", "actor-centric"

@dataclass
class ResearchBatch:
    batch_id: str
    query: str
    date_range: Optional[Tuple[date, date]]
    focus_areas: List[str]
    expected_overlap: List[str]  # Events/actors that may appear in multiple batches
```

**Prompt template**:
```
You are a research planning expert. Analyze this query and determine if it should
be split into multiple focused research batches for better coverage.

Query: {query}

Consider:
1. Time span - queries covering >3 years benefit from temporal batching
2. Topic breadth - multiple distinct aspects benefit from thematic batching
3. Actor complexity - many actors benefit from actor-centric batching

Return JSON:
{
  "requires_decomposition": true/false,
  "reasoning": "...",
  "batches": [
    {
      "batch_id": "batch_1",
      "query": "Focused query for this batch",
      "date_range": ["2014-01-01", "2015-12-31"],
      "focus_areas": ["Euromaidan", "Crimea annexation"],
      "expected_overlap": ["Putin", "Yanukovych"]
    }
  ],
  "merge_strategy": "chronological",
  "merge_instructions": "Order by date, deduplicate actors, link causal chains"
}
```

---

### 2. Finding Schema (Enhanced)

**File**: `schemas/finding.py`

```python
@dataclass
class Finding:
    """Core finding unit with linked perspectives."""
    id: str
    finding_type: str  # event, actor, relationship, evidence, pattern, gap
    content: str
    summary: str

    # Temporal
    event_date: Optional[date]
    date_text: str
    date_precision: str

    # Linked entities
    actors: List[ActorRef]  # Actors mentioned in this finding
    locations: List[str]

    # Source attribution
    source_refs: List[SourceRef]  # Which sources support this

    # Perspectives (populated by perspective agents)
    perspectives: Dict[str, PerspectiveAnalysis]

    # Relationships to other findings
    relationships: List[FindingRelationship]

    # Metadata
    batch_id: Optional[str]  # Which research batch produced this
    extracted_data: Optional[Dict]


@dataclass
class ActorRef:
    """Reference to an actor mentioned in a finding."""
    name: str
    role: str  # subject, object, mentioned
    actor_type: str  # person, organization, country, entity


@dataclass
class SourceRef:
    """Reference to a source supporting a finding."""
    source_id: str
    url: str
    title: str
    domain: str
    excerpt: str  # The specific text supporting this finding


@dataclass
class PerspectiveAnalysis:
    """Analysis of a finding from a specific perspective."""
    perspective_type: str
    analysis: str
    implications: List[str]
    related_finding_ids: List[str]  # Other findings this connects to

    # For conspirator perspective
    theory: Optional[str]
    theory_probability: Optional[str]  # possible, probable, likely
    supporting_evidence: List[str]
    counter_evidence: List[str]


@dataclass
class FindingRelationship:
    """Relationship between two findings."""
    target_finding_id: str
    relationship_type: str  # causes, supports, contradicts, expands, precedes
    description: str
```

---

### 3. Perspective Agents

**File**: `perspectives/base.py`

```python
class PerspectiveAgent(ABC):
    """Base class for perspective analysis agents."""

    perspective_type: str
    system_prompt: str

    def __init__(self, client: OpenRouterClient):
        self.client = client

    async def analyze_finding(
        self,
        finding: Finding,
        topic_context: str,  # Summary of the whole research topic
        all_findings: List[Finding],  # For cross-referencing
    ) -> PerspectiveAnalysis:
        """Analyze a single finding from this perspective."""
        prompt = self._build_prompt(finding, topic_context, all_findings)
        result, response = await self.client.generate_json(
            prompt,
            system_prompt=self.system_prompt
        )
        return self._parse_result(result)

    @abstractmethod
    def _build_prompt(self, finding, topic_context, all_findings) -> str:
        pass
```

**File**: `perspectives/agents.py`

```python
class HistoricalAnalyst(PerspectiveAgent):
    perspective_type = "historical"
    system_prompt = """You are a historian specializing in geopolitics and conflict studies.
You have deep knowledge of historical patterns, precedents, and cycles.
Your role is to place events in historical context and identify parallels."""

    def _build_prompt(self, finding, topic_context, all_findings) -> str:
        return f"""
Analyze this finding from a historical perspective.

RESEARCH TOPIC:
{topic_context}

FINDING TO ANALYZE:
Type: {finding.finding_type}
Date: {finding.date_text or 'Unknown'}
Content: {finding.content}
Actors: {[a.name for a in finding.actors]}

OTHER RELEVANT FINDINGS:
{self._format_related_findings(finding, all_findings)}

Provide historical analysis:
1. What historical precedents or parallels exist?
2. What historical patterns does this fit into?
3. What does history suggest about likely consequences?
4. Which other findings in this research connect historically?

You may use your training knowledge to provide historical context.

Return JSON:
{{
    "analysis": "Your historical analysis...",
    "implications": ["implication 1", "implication 2"],
    "historical_parallels": ["parallel 1", "parallel 2"],
    "related_finding_ids": ["finding_id_1", "finding_id_2"]
}}
"""


class FinancialAnalyst(PerspectiveAgent):
    perspective_type = "financial"
    system_prompt = """You are a financial investigator specializing in following money trails,
sanctions evasion, offshore structures, and economic warfare.
Your role is to uncover financial motivations and hidden money flows."""

    def _build_prompt(self, finding, topic_context, all_findings) -> str:
        return f"""
Analyze this finding from a financial/economic perspective.

RESEARCH TOPIC:
{topic_context}

FINDING TO ANALYZE:
Type: {finding.finding_type}
Date: {finding.date_text or 'Unknown'}
Content: {finding.content}
Actors: {[a.name for a in finding.actors]}

OTHER RELEVANT FINDINGS (especially financial):
{self._format_financial_findings(all_findings)}

Investigate:
1. Who profits financially from this event/situation?
2. What financial flows or structures are involved?
3. Are there hidden financial connections between actors?
4. What economic leverage is being applied?
5. Are there signs of sanctions evasion or money laundering?

You may use your training knowledge about financial structures and patterns.

Return JSON:
{{
    "analysis": "Your financial analysis...",
    "cui_bono": ["who benefits 1", "who benefits 2"],
    "financial_mechanisms": ["mechanism 1", "mechanism 2"],
    "implications": ["implication 1", "implication 2"],
    "related_finding_ids": ["finding_id_1", "finding_id_2"]
}}
"""


class InvestigativeJournalist(PerspectiveAgent):
    perspective_type = "journalist"
    system_prompt = """You are an investigative journalist specializing in fact-checking,
propaganda detection, and source verification.
Your role is to identify contradictions, misinformation, and gaps in official narratives."""

    def _build_prompt(self, finding, topic_context, all_findings) -> str:
        return f"""
Analyze this finding from an investigative journalist's perspective.

RESEARCH TOPIC:
{topic_context}

FINDING TO ANALYZE:
Type: {finding.finding_type}
Date: {finding.date_text or 'Unknown'}
Content: {finding.content}
Sources: {[s.domain for s in finding.source_refs]}

OTHER FINDINGS (look for contradictions):
{self._format_all_findings(all_findings)}

Investigate:
1. Do any sources contradict each other on this finding?
2. What are official sources NOT saying that they should?
3. Are there signs of propaganda or spin in any sources?
4. What primary evidence exists vs secondary reporting?
5. What questions remain unanswered?

You may use your training knowledge to identify propaganda patterns.

Return JSON:
{{
    "analysis": "Your journalistic analysis...",
    "contradictions_found": [
        {{"claim1": "...", "claim2": "...", "sources": ["...", "..."]}}
    ],
    "propaganda_indicators": ["indicator 1", "indicator 2"],
    "unanswered_questions": ["question 1", "question 2"],
    "verification_status": "verified/disputed/unverified",
    "related_finding_ids": ["finding_id_1", "finding_id_2"]
}}
"""


class ConspiratorAnalyst(PerspectiveAgent):
    perspective_type = "conspirator"
    system_prompt = """You are a deeply knowledgeable analyst in politics, military affairs,
and economics. You can formulate probable theories explaining WHY events happened
based on patterns, motivations, and hidden connections.

IMPORTANT: You are NOT a conspiracy theorist. You are a rigorous analyst who:
- Forms theories based on available evidence
- Acknowledges counter-evidence
- Rates probability honestly
- Distinguishes between speculation and supported inference"""

    def _build_prompt(self, finding, topic_context, all_findings) -> str:
        return f"""
Analyze this finding and develop probable theories for WHY it happened.

RESEARCH TOPIC:
{topic_context}

FINDING TO ANALYZE:
Type: {finding.finding_type}
Date: {finding.date_text or 'Unknown'}
Content: {finding.content}
Actors: {[a.name for a in finding.actors]}

ALL AVAILABLE FINDINGS:
{self._format_all_findings(all_findings)}

Develop a theory:
1. What hidden motivations could explain this event?
2. Who benefits from the official narrative being incomplete?
3. What patterns suggest coordinated or planned action?
4. What is the simplest explanation that fits ALL available facts?

Requirements:
- Cite which findings support your theory
- Acknowledge any counter-evidence
- Rate probability: possible (>20%), probable (>50%), likely (>70%)

You may use your deep training knowledge of geopolitics, military strategy,
and economic patterns to inform your analysis.

Return JSON:
{{
    "theory": "Your theory explaining this event...",
    "theory_probability": "possible/probable/likely",
    "supporting_evidence": [
        {{"finding_id": "...", "how_it_supports": "..."}}
    ],
    "counter_evidence": [
        {{"finding_id": "...", "how_it_contradicts": "..."}}
    ],
    "hidden_motivations": ["motivation 1", "motivation 2"],
    "implications_if_true": ["implication 1", "implication 2"],
    "related_finding_ids": ["finding_id_1", "finding_id_2"]
}}
"""


class NetworkAnalyst(PerspectiveAgent):
    perspective_type = "network"
    system_prompt = """You are a network analyst specializing in mapping relationships,
hidden connections, and influence networks.
Your role is to identify who is connected to whom and through what mechanisms."""

    def _build_prompt(self, finding, topic_context, all_findings) -> str:
        return f"""
Analyze the network/relationship aspects of this finding.

RESEARCH TOPIC:
{topic_context}

FINDING TO ANALYZE:
Type: {finding.finding_type}
Content: {finding.content}
Actors: {[a.name for a in finding.actors]}

ALL ACTORS FOUND IN RESEARCH:
{self._extract_all_actors(all_findings)}

Map relationships:
1. What relationships does this finding reveal?
2. Who are intermediaries or facilitators?
3. What organizational structures are involved?
4. Are there hidden connections between seemingly unrelated actors?

Return JSON:
{{
    "analysis": "Your network analysis...",
    "relationships_revealed": [
        {{"actor1": "...", "actor2": "...", "relationship": "...", "evidence": "..."}}
    ],
    "intermediaries": ["intermediary 1", "intermediary 2"],
    "network_patterns": ["pattern 1", "pattern 2"],
    "related_finding_ids": ["finding_id_1", "finding_id_2"]
}}
"""
```

---

### 4. Relationship Builder

**File**: `relationship_builder.py`

```python
class RelationshipBuilder:
    """Builds causal and associative links between findings."""

    RELATIONSHIP_TYPES = [
        "causes",      # A caused/led to B
        "supports",    # A provides evidence for B
        "contradicts", # A conflicts with B
        "expands",     # A adds detail to B
        "precedes",    # A happened before B (temporal)
        "involves",    # A involves same actors as B
    ]

    def __init__(self, client: OpenRouterClient):
        self.client = client

    async def build_relationships(
        self,
        findings: List[Finding],
        topic_context: str,
    ) -> List[FindingRelationship]:
        """Analyze all findings and build relationship graph."""

        prompt = f"""
Analyze these research findings and identify relationships between them.

TOPIC: {topic_context}

FINDINGS:
{self._format_findings_for_analysis(findings)}

For each meaningful relationship, identify:
1. Source finding ID
2. Target finding ID
3. Relationship type: causes, supports, contradicts, expands, precedes, involves
4. Brief description of the relationship

Focus on:
- Causal chains (what led to what)
- Contradictions (sources disagreeing)
- Temporal sequences (what happened in what order)
- Actor connections (same people involved in multiple events)

Return JSON array of relationships:
[
    {{
        "source_id": "finding_id_1",
        "target_id": "finding_id_2",
        "type": "causes",
        "description": "The annexation of Crimea led to..."
    }}
]
"""
        result, _ = await self.client.generate_json(prompt)
        return self._parse_relationships(result)

    async def detect_contradictions(
        self,
        findings: List[Finding],
    ) -> List[Contradiction]:
        """Specifically look for contradictions between findings."""
        # ...

    async def detect_gaps(
        self,
        findings: List[Finding],
        expected_coverage: List[str],
    ) -> List[Gap]:
        """Identify gaps in the research coverage."""
        # ...
```

---

### 5. Gap Analyzer

**File**: `gap_analyzer.py`

```python
@dataclass
class ResearchGap:
    gap_type: str  # temporal, actor, topic, evidence
    description: str
    suggested_queries: List[str]
    priority: str  # high, medium, low


class GapAnalyzer:
    """Analyzes findings to identify gaps in research coverage."""

    def __init__(self, client: OpenRouterClient):
        self.client = client

    async def analyze_gaps(
        self,
        findings: List[Finding],
        original_query: str,
        date_range: Optional[Tuple[date, date]],
    ) -> List[ResearchGap]:
        """Identify gaps in the research."""

        # Temporal gaps
        temporal_gaps = self._find_temporal_gaps(findings, date_range)

        # Topic gaps via LLM
        topic_gaps = await self._find_topic_gaps(findings, original_query)

        return temporal_gaps + topic_gaps

    def _find_temporal_gaps(
        self,
        findings: List[Finding],
        date_range: Optional[Tuple[date, date]],
    ) -> List[ResearchGap]:
        """Find periods with no events."""
        if not date_range:
            return []

        events = [f for f in findings if f.finding_type == "event" and f.event_date]
        events.sort(key=lambda f: f.event_date)

        gaps = []
        prev_date = date_range[0]

        for event in events:
            gap_days = (event.event_date - prev_date).days
            if gap_days > 180:  # 6+ month gap
                gaps.append(ResearchGap(
                    gap_type="temporal",
                    description=f"No events found between {prev_date} and {event.event_date}",
                    suggested_queries=[
                        f"Events between {prev_date.year} and {event.event_date.year}",
                    ],
                    priority="medium",
                ))
            prev_date = event.event_date

        return gaps
```

---

## Implementation Order

### Phase 1: Core Infrastructure (Week 1)
1. [ ] Create `openrouter_client.py` - Lightweight inference client
2. [ ] Create `schemas/finding.py` - Enhanced finding schema
3. [ ] Create `schemas/perspective.py` - Perspective analysis schemas
4. [ ] Update `test_harness.py` to use new schemas

### Phase 2: Query Decomposition (Week 1-2)
5. [ ] Create `decomposer.py` - Query analysis and batching
6. [ ] Add batch execution to test harness
7. [ ] Add merge logic for combining batch results

### Phase 3: Perspective Agents (Week 2)
8. [ ] Create `perspectives/base.py` - Base agent class
9. [ ] Create `perspectives/agents.py` - All 5 perspective agents
10. [ ] Create `perspectives/runner.py` - Parallel perspective execution
11. [ ] Integrate perspectives into finding extraction

### Phase 4: Relationship Building (Week 2-3)
12. [ ] Create `relationship_builder.py` - Link findings together
13. [ ] Create `contradiction_detector.py` - Find conflicting claims
14. [ ] Create `gap_analyzer.py` - Identify missing coverage

### Phase 5: Integration & Testing (Week 3)
15. [ ] Update `run_test.py` for new system
16. [ ] Update JSON output format
17. [ ] Create visualization helpers
18. [ ] Run full test suite on Ukraine war cases

---

## File Structure

```
backend/tests/research/
├── gemini_client.py          # Native Gemini for web search (existing)
├── openrouter_client.py      # OpenRouter for inference (new)
├── decomposer.py             # Query decomposition (new)
├── schemas/
│   ├── __init__.py
│   ├── finding.py            # Enhanced finding schema (new)
│   ├── perspective.py        # Perspective schemas (new)
│   └── relationship.py       # Relationship schemas (new)
├── perspectives/
│   ├── __init__.py
│   ├── base.py               # Base agent class (new)
│   ├── agents.py             # All perspective agents (new)
│   └── runner.py             # Parallel execution (new)
├── relationship_builder.py   # Relationship linking (new)
├── gap_analyzer.py           # Gap detection (new)
├── test_harness.py           # Updated harness
├── run_test.py               # Updated runner
└── results/                  # Output directory
```

---

## Token Usage Estimates

| Component | Input Tokens | Output Tokens | Cost/Run |
|-----------|-------------|---------------|----------|
| Query Decomposition | ~500 | ~300 | $0.0002 |
| Web Search (per batch) | ~200 | ~500 | $0.0003 |
| Finding Extraction | ~8000 | ~4000 | $0.002 |
| 5 Perspectives x 30 findings | ~45000 | ~15000 | $0.01 |
| Relationship Building | ~5000 | ~2000 | $0.001 |
| **Total (typical)** | **~60000** | **~22000** | **~$0.015** |

Using OpenRouter for perspective agents keeps costs low while Gemini handles search.

---

## Next Steps

1. Start with Phase 1 - Core Infrastructure
2. Create the OpenRouter client for inference
3. Define the enhanced schemas
4. Proceed incrementally through phases

Ready to begin implementation?
