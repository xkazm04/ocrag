# Deep Research Implementation Plan

## Overview

This document outlines the implementation plan for three enhanced research capabilities:
1. **Recursive Chain-of-Investigation (CoI)** - N-level deep research with automatic follow-up generation
2. **Financial Trail Blazer Agent** - Specialized financial forensics pipeline
3. **Temporal Causality Graph** - Cause-effect relationship tracking

**Current State:** 2-level flat research (query → subqueries → answers)
**Target State:** N-level recursive research with integrated specialized services and causality tracking

---

## Design Decisions (Confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Configuration** | Default only, no user customization | Simplify initial implementation |
| **External APIs** | LLM-guided discovery, no hardcoded sources | International scope (UK, France, USVI, etc.) |
| **Causality** | Auto-extract during research | Seamless integration, richer output |
| **Service Integration** | Auto-invoke financial/causality from recursive | Unified deep research pipeline |
| **Cost Limits** | None for now | Evaluate after testing quality vs. cost |

---

## Direction 1: Recursive Chain-of-Investigation (CoI)

### 1.1 Problem Statement

Current `profile_research_service.py` and `job_processor.py` execute a fixed 2-level pipeline:
```
Query → Decomposition → Sub-queries → Answers → Done
```

This misses deeper insights:
- "Wexner granted Epstein POA" → WHY? WHO introduced them?
- "Epstein had $200M at death" → WHERE did it come from? WHAT happened to it?

### 1.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RecursiveResearchService                      │
├─────────────────────────────────────────────────────────────────┤
│  start_recursive_research(query, config) → ResearchTree         │
│                                                                  │
│  ┌─────────────────┐                                            │
│  │ ResearchNode    │ ←── Each node is a research unit           │
│  │ - query         │                                            │
│  │ - depth         │                                            │
│  │ - findings[]    │                                            │
│  │ - children[]    │ ←── Follow-up questions become children    │
│  │ - parent_id     │                                            │
│  │ - saturation    │ ←── 0.0-1.0, stops when high               │
│  └─────────────────┘                                            │
│                                                                  │
│  Process:                                                        │
│  1. Execute research at current node                            │
│  2. Generate follow-up questions (predecessors + consequences)  │
│  3. Filter by novelty (skip if already researched)              │
│  4. Create child nodes for novel questions                      │
│  5. Recurse until: depth_limit OR saturation_threshold OR       │
│     no_new_entities                                             │
│  6. Return full tree with provenance chain                      │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 New Database Schema

```sql
-- New table: research_trees (tracks recursive research sessions)
CREATE TABLE research_trees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    root_query TEXT NOT NULL,
    workspace_id TEXT NOT NULL DEFAULT 'default',
    config JSONB NOT NULL DEFAULT '{}',
    -- Config: {depth_limit, saturation_threshold, max_nodes, follow_up_types}
    status TEXT NOT NULL DEFAULT 'pending',
    -- pending, running, completed, failed, cancelled
    total_nodes INTEGER DEFAULT 0,
    completed_nodes INTEGER DEFAULT 0,
    max_depth_reached INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

-- New table: research_nodes (individual nodes in the tree)
CREATE TABLE research_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES research_trees(id) ON DELETE CASCADE,
    parent_node_id UUID REFERENCES research_nodes(id),
    query TEXT NOT NULL,
    query_type TEXT NOT NULL DEFAULT 'initial',
    -- initial, predecessor, consequence, detail, verification
    depth INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    -- pending, running, completed, skipped
    saturation_score FLOAT DEFAULT 0.0,
    -- 0.0 = novel, 1.0 = fully saturated (all info already known)
    findings_count INTEGER DEFAULT 0,
    new_entities_count INTEGER DEFAULT 0,
    skip_reason TEXT,
    -- If skipped: 'duplicate', 'saturated', 'depth_limit', 'irrelevant'
    session_id UUID REFERENCES research_sessions(id),
    -- Links to actual research execution
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    execution_time_ms INTEGER,
    UNIQUE(tree_id, query)
    -- Prevent duplicate queries within same tree
);

-- New table: node_follow_ups (generated follow-up questions)
CREATE TABLE node_follow_ups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id UUID NOT NULL REFERENCES research_nodes(id) ON DELETE CASCADE,
    follow_up_query TEXT NOT NULL,
    follow_up_type TEXT NOT NULL,
    -- predecessor, consequence, detail, verification, financial, temporal
    priority_score FLOAT DEFAULT 0.5,
    -- 0.0-1.0, higher = more important
    reasoning TEXT,
    -- Why this follow-up was generated
    target_node_id UUID REFERENCES research_nodes(id),
    -- Set when follow-up becomes a node
    status TEXT NOT NULL DEFAULT 'pending',
    -- pending, queued, executed, skipped
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient tree traversal
CREATE INDEX idx_research_nodes_tree_depth ON research_nodes(tree_id, depth);
CREATE INDEX idx_research_nodes_parent ON research_nodes(parent_node_id);
CREATE INDEX idx_node_follow_ups_source ON node_follow_ups(source_node_id);
```

### 1.4 New Schemas

**File:** `backend/app/research/schemas/recursive.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime
from enum import Enum

class FollowUpType(str, Enum):
    PREDECESSOR = "predecessor"      # What caused/enabled this?
    CONSEQUENCE = "consequence"      # What resulted from this?
    DETAIL = "detail"                # More specific information
    VERIFICATION = "verification"    # Confirm/verify this claim
    FINANCIAL = "financial"          # Follow money trail
    TEMPORAL = "temporal"            # What happened before/after?

class RecursiveResearchConfig(BaseModel):
    depth_limit: int = Field(default=5, ge=1, le=10)
    saturation_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_nodes: int = Field(default=50, ge=1, le=200)
    max_follow_ups_per_node: int = Field(default=5, ge=1, le=10)
    follow_up_types: List[FollowUpType] = Field(
        default=[FollowUpType.PREDECESSOR, FollowUpType.CONSEQUENCE]
    )
    min_priority_score: float = Field(default=0.3, ge=0.0, le=1.0)
    parallel_nodes: int = Field(default=3, ge=1, le=10)
    # Execute up to N nodes in parallel per depth level

class StartRecursiveResearchRequest(BaseModel):
    query: str
    workspace_id: str = "default"
    config: Optional[RecursiveResearchConfig] = None
    template_type: str = "investigative"
    focus_entities: Optional[List[str]] = None
    # Prioritize follow-ups involving these entities

class ResearchNodeStatus(BaseModel):
    id: UUID
    query: str
    query_type: str
    depth: int
    status: str
    saturation_score: float
    findings_count: int
    new_entities_count: int
    children_count: int
    skip_reason: Optional[str] = None

class FollowUpQuestion(BaseModel):
    query: str
    follow_up_type: FollowUpType
    priority_score: float
    reasoning: str
    source_finding_id: Optional[UUID] = None

class ResearchTreeStatus(BaseModel):
    tree_id: UUID
    root_query: str
    status: str
    total_nodes: int
    completed_nodes: int
    pending_nodes: int
    max_depth_reached: int
    progress_pct: float
    current_depth_nodes: List[ResearchNodeStatus]
    # Nodes currently being processed

class ResearchTreeResult(BaseModel):
    tree_id: UUID
    root_query: str
    config: RecursiveResearchConfig
    total_nodes: int
    max_depth_reached: int
    total_findings: int
    total_entities_discovered: int
    key_insights: List[str]
    reasoning_chains: List[List[str]]
    # [[Q1, Q2, Q3], [Q1, Q4, Q5]] - paths through tree
    duration_seconds: float
    token_usage: dict
    cost_usd: float
```

### 1.5 New Service

**File:** `backend/app/research/services/recursive_research_service.py`

```python
class RecursiveResearchService:
    """
    Executes N-level recursive research by automatically generating
    and pursuing follow-up questions until saturation or limits.
    """

    def __init__(
        self,
        db: SupabaseResearchDB,
        gemini_client: GeminiResearchClient,
        inference_client: InferenceClient
    ):
        self.db = db
        self.gemini = gemini_client
        self.inference = inference_client
        self.orchestrator = ResearchOrchestrator(db, gemini_client)

    async def start_recursive_research(
        self,
        request: StartRecursiveResearchRequest
    ) -> AsyncGenerator[ResearchTreeStatus, None]:
        """
        Main entry point. Creates tree and processes nodes breadth-first.
        Yields status updates as nodes complete.
        """
        # 1. Create research tree record
        # 2. Create root node
        # 3. Process nodes level by level (BFS with parallel execution)
        # 4. For each completed node:
        #    a. Generate follow-up questions
        #    b. Filter by novelty and priority
        #    c. Create child nodes
        # 5. Yield progress updates
        # 6. Return final tree result
        pass

    async def _process_node(
        self,
        node_id: UUID,
        tree_config: RecursiveResearchConfig
    ) -> Tuple[List[Finding], List[FollowUpQuestion]]:
        """
        Execute research for a single node and generate follow-ups.
        """
        # 1. Check saturation (have we seen this before?)
        # 2. Execute research via orchestrator
        # 3. Extract findings and entities
        # 4. Generate follow-up questions
        # 5. Calculate saturation score
        # 6. Return findings and follow-ups
        pass

    async def _generate_follow_ups(
        self,
        node_query: str,
        findings: List[Finding],
        follow_up_types: List[FollowUpType],
        existing_queries: Set[str]
    ) -> List[FollowUpQuestion]:
        """
        Use LLM to generate follow-up questions based on findings.
        """
        prompt = f"""
        Based on this research query and its findings, generate follow-up questions.

        Original Query: {node_query}

        Findings:
        {self._format_findings(findings)}

        Generate follow-up questions for these types:
        {[t.value for t in follow_up_types]}

        For PREDECESSOR questions, ask "What caused this?", "What enabled this?", "Who introduced X to Y?"
        For CONSEQUENCE questions, ask "What resulted from this?", "What happened next?", "How did this affect X?"
        For DETAIL questions, ask for specific dates, amounts, locations, participants.
        For VERIFICATION questions, ask "Is this claim verified?", "What is the evidence for X?"

        Already researched (DO NOT repeat):
        {list(existing_queries)[:20]}

        Return JSON:
        {{
            "follow_ups": [
                {{
                    "query": "specific question",
                    "type": "predecessor|consequence|detail|verification",
                    "priority": 0.0-1.0,
                    "reasoning": "why this matters",
                    "source_finding": "which finding triggered this"
                }}
            ]
        }}
        """
        # Execute LLM call and parse response
        pass

    async def _calculate_saturation(
        self,
        query: str,
        findings: List[Finding],
        workspace_id: str
    ) -> float:
        """
        Calculate how much of this query's answer space is already known.
        Returns 0.0 (novel) to 1.0 (fully saturated).
        """
        # 1. Get existing claims matching query topic
        # 2. Compare new findings to existing claims
        # 3. Calculate overlap ratio
        # 4. Adjust for entity novelty
        pass

    async def _filter_follow_ups(
        self,
        follow_ups: List[FollowUpQuestion],
        config: RecursiveResearchConfig,
        existing_queries: Set[str]
    ) -> List[FollowUpQuestion]:
        """
        Filter and prioritize follow-up questions.
        """
        filtered = []
        for fu in follow_ups:
            # Skip if already researched
            if fu.query in existing_queries:
                continue
            # Skip if below priority threshold
            if fu.priority_score < config.min_priority_score:
                continue
            # Skip if not in allowed types
            if fu.follow_up_type not in config.follow_up_types:
                continue
            filtered.append(fu)

        # Sort by priority, take top N
        filtered.sort(key=lambda x: x.priority_score, reverse=True)
        return filtered[:config.max_follow_ups_per_node]

    async def get_tree_result(
        self,
        tree_id: UUID
    ) -> ResearchTreeResult:
        """
        Compile final results from completed tree.
        """
        # 1. Get all nodes
        # 2. Build reasoning chains (paths from root to leaves)
        # 3. Aggregate findings
        # 4. Generate key insights summary
        # 5. Calculate stats
        pass

    async def get_reasoning_chain(
        self,
        tree_id: UUID,
        leaf_node_id: UUID
    ) -> List[str]:
        """
        Get the question chain from root to a specific leaf node.
        Useful for understanding how a conclusion was reached.
        """
        chain = []
        current_node = await self.db.get_research_node(leaf_node_id)
        while current_node:
            chain.insert(0, current_node.query)
            if current_node.parent_node_id:
                current_node = await self.db.get_research_node(
                    current_node.parent_node_id
                )
            else:
                break
        return chain
```

### 1.6 New API Endpoints

**Add to:** `backend/app/research/router.py`

```python
# Recursive Research Endpoints

@router.post("/research/recursive/start")
async def start_recursive_research(
    request: StartRecursiveResearchRequest,
    db: SupabaseResearchDB = Depends(get_db)
) -> StreamingResponse:
    """
    Start recursive research session with automatic follow-up generation.
    Returns SSE stream with progress updates.
    """
    service = RecursiveResearchService(db, gemini_client, inference_client)

    async def event_generator():
        async for status in service.start_recursive_research(request):
            yield f"data: {status.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/research/recursive/submit")
async def submit_recursive_research(
    request: StartRecursiveResearchRequest,
    background_tasks: BackgroundTasks,
    db: SupabaseResearchDB = Depends(get_db)
) -> dict:
    """
    Submit recursive research as background job.
    Returns tree_id for polling.
    """
    tree_id = await db.create_research_tree(request)
    background_tasks.add_task(
        process_recursive_research,
        tree_id,
        request.workspace_id
    )
    return {"tree_id": tree_id, "status": "pending"}

@router.get("/research/recursive/{tree_id}/status")
async def get_recursive_status(
    tree_id: UUID,
    db: SupabaseResearchDB = Depends(get_db)
) -> ResearchTreeStatus:
    """Get current status of recursive research tree."""
    return await db.get_tree_status(tree_id)

@router.get("/research/recursive/{tree_id}/result")
async def get_recursive_result(
    tree_id: UUID,
    db: SupabaseResearchDB = Depends(get_db)
) -> ResearchTreeResult:
    """Get final result of completed recursive research."""
    service = RecursiveResearchService(db, gemini_client, inference_client)
    return await service.get_tree_result(tree_id)

@router.get("/research/recursive/{tree_id}/nodes")
async def get_tree_nodes(
    tree_id: UUID,
    depth: Optional[int] = None,
    status: Optional[str] = None,
    db: SupabaseResearchDB = Depends(get_db)
) -> List[ResearchNodeStatus]:
    """Get nodes in tree, optionally filtered by depth or status."""
    return await db.get_tree_nodes(tree_id, depth=depth, status=status)

@router.get("/research/recursive/{tree_id}/chain/{node_id}")
async def get_reasoning_chain(
    tree_id: UUID,
    node_id: UUID,
    db: SupabaseResearchDB = Depends(get_db)
) -> List[str]:
    """Get question chain from root to specific node."""
    service = RecursiveResearchService(db, gemini_client, inference_client)
    return await service.get_reasoning_chain(tree_id, node_id)
```

### 1.7 Integration Points

| Existing Component | Integration |
|-------------------|-------------|
| `ResearchOrchestrator` | Used by `RecursiveResearchService._process_node()` for actual research execution |
| `FindingDeduplicator` | Used for saturation calculation and preventing duplicate findings |
| `TopicMatcher` | Used to match follow-up queries to existing topics |
| `SupabaseResearchDB` | Extended with new tree/node operations |
| `JobProcessor` | Can delegate to recursive service for complex queries |

---

## Direction 2: Financial Trail Blazer Agent

### 2.1 Problem Statement

Current web search is poor at financial forensics:
- Generic searches return journalism, not primary sources
- Transaction chains are buried in SEC filings, court documents, corporate registries
- No structured extraction of: amounts, dates, parties, account flows

### 2.2 Proposed Architecture

**Key Design:** No hardcoded external APIs. LLM-guided source discovery with specialized
financial prompts that instruct the model to find and cite appropriate sources based on
jurisdiction (US SEC filings, UK Companies House, French RCS, offshore registries, etc.).

```
┌─────────────────────────────────────────────────────────────────┐
│                    FinancialResearchService                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LLM-Guided Source Discovery (International):                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Prompt instructs LLM to:                                │   │
│  │ - Identify appropriate registries for jurisdiction      │   │
│  │   (SEC for US, Companies House for UK, RCS for France)  │   │
│  │ - Search for corporate filings based on entity location │   │
│  │ - Find court documents, property records, news sources  │   │
│  │ - Cite primary sources when available                   │   │
│  │ - Note evidence strength (official filing vs journalism)│   │
│  │ - Handle offshore jurisdictions (BVI, Cayman, Panama)   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Transaction Chain Model:                                        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐     │
│  │ Entity  │───▶│ Transfer│───▶│ Entity  │───▶│ Transfer│───▶  │
│  │ A       │    │ $X, date│    │ B       │    │ $Y, date│      │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘     │
│       │              │              │              │            │
│       ▼              ▼              ▼              ▼            │
│  [bank, trust]  [purpose]    [shell, trust]  [purpose]         │
│                                                                  │
│  Capabilities:                                                   │
│  - trace_money_forward(entity, amount?) → chain of recipients   │
│  - trace_money_backward(entity, amount?) → chain of sources     │
│  - find_corporate_structure(entity) → parent/subsidiary tree    │
│  - find_property_transfers(entity) → real estate transactions   │
│  - find_beneficial_owners(company) → ultimate owners            │
│  - detect_shell_companies(entity) → suspicious patterns         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 New Database Schema

```sql
-- Financial entities (companies, trusts, accounts)
CREATE TABLE financial_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES knowledge_entities(id),
    -- Link to main entity if exists
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    -- corporation, llc, trust, foundation, bank_account, brokerage
    jurisdiction TEXT,
    -- State/country of incorporation
    registration_number TEXT,
    -- Corp ID, EIN, etc.
    status TEXT,
    -- active, dissolved, merged, unknown
    incorporation_date DATE,
    dissolution_date DATE,
    registered_agent TEXT,
    registered_address TEXT,
    metadata JSONB DEFAULT '{}',
    -- SEC CIK, OpenCorporates URL, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Financial transactions
CREATE TABLE financial_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES financial_entities(id),
    target_entity_id UUID REFERENCES financial_entities(id),
    transaction_type TEXT NOT NULL,
    -- transfer, sale, purchase, loan, investment, donation, fee, settlement
    amount DECIMAL(20, 2),
    currency TEXT DEFAULT 'USD',
    transaction_date DATE,
    transaction_date_precision TEXT DEFAULT 'day',
    -- day, month, year, approximate
    description TEXT,
    purpose TEXT,
    evidence_strength TEXT DEFAULT 'medium',
    -- high, medium, low, alleged
    source_document TEXT,
    -- Reference to source (SEC filing, court doc, etc.)
    source_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Corporate relationships (ownership, control)
CREATE TABLE corporate_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_entity_id UUID REFERENCES financial_entities(id),
    child_entity_id UUID REFERENCES financial_entities(id),
    relationship_type TEXT NOT NULL,
    -- owns, controls, subsidiary, affiliate, director, officer, registered_agent
    ownership_percentage DECIMAL(5, 2),
    -- NULL if not ownership
    start_date DATE,
    end_date DATE,
    evidence_strength TEXT DEFAULT 'medium',
    source_document TEXT,
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Beneficial ownership (who ultimately controls)
CREATE TABLE beneficial_owners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_entity_id UUID REFERENCES financial_entities(id),
    owner_entity_id UUID REFERENCES knowledge_entities(id),
    -- Person or ultimate parent company
    ownership_type TEXT NOT NULL,
    -- direct, indirect, beneficial, nominee
    ownership_percentage DECIMAL(5, 2),
    control_type TEXT,
    -- voting, economic, both
    evidence_strength TEXT DEFAULT 'medium',
    source_document TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Property records
CREATE TABLE property_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_address TEXT NOT NULL,
    property_type TEXT,
    -- residential, commercial, land, mixed
    jurisdiction TEXT,
    -- County, State
    parcel_id TEXT,
    owner_entity_id UUID REFERENCES financial_entities(id),
    purchase_date DATE,
    purchase_price DECIMAL(20, 2),
    sale_date DATE,
    sale_price DECIMAL(20, 2),
    current_assessed_value DECIMAL(20, 2),
    source_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SEC filings reference
CREATE TABLE sec_filings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cik TEXT NOT NULL,
    -- SEC Central Index Key
    accession_number TEXT NOT NULL UNIQUE,
    filing_type TEXT NOT NULL,
    -- 13F, 10-K, 10-Q, DEF 14A, Form 4, etc.
    filing_date DATE NOT NULL,
    company_name TEXT,
    entity_id UUID REFERENCES financial_entities(id),
    document_url TEXT,
    extracted_data JSONB DEFAULT '{}',
    -- Parsed holdings, transactions, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_fin_transactions_source ON financial_transactions(source_entity_id);
CREATE INDEX idx_fin_transactions_target ON financial_transactions(target_entity_id);
CREATE INDEX idx_fin_transactions_date ON financial_transactions(transaction_date);
CREATE INDEX idx_corp_relationships_parent ON corporate_relationships(parent_entity_id);
CREATE INDEX idx_corp_relationships_child ON corporate_relationships(child_entity_id);
CREATE INDEX idx_property_owner ON property_records(owner_entity_id);
CREATE INDEX idx_sec_filings_cik ON sec_filings(cik);
```

### 2.4 New Schemas

**File:** `backend/app/research/schemas/financial.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

class FinancialEntityType(str, Enum):
    CORPORATION = "corporation"
    LLC = "llc"
    TRUST = "trust"
    FOUNDATION = "foundation"
    PARTNERSHIP = "partnership"
    BANK_ACCOUNT = "bank_account"
    BROKERAGE = "brokerage"
    SHELL_COMPANY = "shell_company"
    UNKNOWN = "unknown"

class TransactionType(str, Enum):
    TRANSFER = "transfer"
    SALE = "sale"
    PURCHASE = "purchase"
    LOAN = "loan"
    INVESTMENT = "investment"
    DONATION = "donation"
    FEE = "fee"
    SETTLEMENT = "settlement"
    SALARY = "salary"
    GIFT = "gift"

class EvidenceStrength(str, Enum):
    HIGH = "high"          # Primary source (SEC filing, court doc)
    MEDIUM = "medium"      # Reliable journalism with sources
    LOW = "low"            # Single source, unverified
    ALLEGED = "alleged"    # Claimed but disputed

class FinancialEntity(BaseModel):
    id: Optional[UUID] = None
    name: str
    entity_type: FinancialEntityType
    jurisdiction: Optional[str] = None
    registration_number: Optional[str] = None
    status: Optional[str] = None
    incorporation_date: Optional[date] = None
    dissolution_date: Optional[date] = None
    linked_person_id: Optional[UUID] = None  # Link to knowledge_entities

class FinancialTransaction(BaseModel):
    id: Optional[UUID] = None
    source_entity: FinancialEntity
    target_entity: FinancialEntity
    transaction_type: TransactionType
    amount: Optional[Decimal] = None
    currency: str = "USD"
    transaction_date: Optional[date] = None
    date_precision: str = "day"
    description: Optional[str] = None
    purpose: Optional[str] = None
    evidence_strength: EvidenceStrength = EvidenceStrength.MEDIUM
    source_document: Optional[str] = None
    source_url: Optional[str] = None

class TransactionChain(BaseModel):
    """A sequence of connected transactions"""
    transactions: List[FinancialTransaction]
    total_amount: Optional[Decimal] = None
    start_entity: str
    end_entity: str
    chain_length: int
    time_span_days: Optional[int] = None

class CorporateStructure(BaseModel):
    """Hierarchical corporate ownership structure"""
    root_entity: FinancialEntity
    subsidiaries: List["CorporateStructure"] = []
    ownership_percentage: Optional[float] = None
    relationship_type: str = "subsidiary"

class BeneficialOwner(BaseModel):
    owner_name: str
    owner_entity_id: Optional[UUID] = None
    ownership_percentage: Optional[float] = None
    ownership_type: str  # direct, indirect, beneficial, nominee
    control_type: Optional[str] = None  # voting, economic, both
    evidence_strength: EvidenceStrength

class PropertyRecord(BaseModel):
    address: str
    property_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    owner: str
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    sale_date: Optional[date] = None
    sale_price: Optional[Decimal] = None
    source_url: Optional[str] = None

# Request/Response schemas
class TraceMoneyRequest(BaseModel):
    entity_name: str
    entity_id: Optional[UUID] = None
    direction: Literal["forward", "backward", "both"] = "both"
    amount_filter: Optional[Decimal] = None  # Only transactions >= this amount
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    max_hops: int = Field(default=5, ge=1, le=10)
    include_shell_detection: bool = True

class TraceMoneyResponse(BaseModel):
    entity_name: str
    chains_found: int
    forward_chains: List[TransactionChain]
    backward_chains: List[TransactionChain]
    total_inflow: Optional[Decimal] = None
    total_outflow: Optional[Decimal] = None
    suspicious_patterns: List[str]
    shell_companies_detected: List[FinancialEntity]

class CorporateStructureRequest(BaseModel):
    entity_name: str
    entity_id: Optional[UUID] = None
    include_officers: bool = True
    include_historical: bool = False
    max_depth: int = Field(default=5, ge=1, le=10)

class CorporateStructureResponse(BaseModel):
    root_entity: FinancialEntity
    structure: CorporateStructure
    officers: List[dict]
    beneficial_owners: List[BeneficialOwner]
    total_subsidiaries: int
    jurisdictions: List[str]

class PropertySearchRequest(BaseModel):
    entity_name: str
    entity_id: Optional[UUID] = None
    include_historical: bool = True
    jurisdictions: Optional[List[str]] = None

class PropertySearchResponse(BaseModel):
    entity_name: str
    properties_found: int
    current_holdings: List[PropertyRecord]
    historical_transactions: List[PropertyRecord]
    total_current_value: Optional[Decimal] = None
```

### 2.5 New Service

**File:** `backend/app/research/services/financial_research_service.py`

```python
class FinancialResearchService:
    """
    Specialized financial forensics research service.
    Uses LLM-guided source discovery for financial forensics (no hardcoded external APIs).
    """

    def __init__(
        self,
        db: SupabaseResearchDB,
        gemini_client: GeminiResearchClient,
    ):
        self.db = db
        self.gemini = gemini_client

    async def trace_money(
        self,
        request: TraceMoneyRequest
    ) -> TraceMoneyResponse:
        """
        Trace financial transactions forward and/or backward from an entity.

        Process:
        1. Identify all financial entities associated with person/company
        2. Search SEC filings for transactions (Form 4, 13F holdings changes)
        3. Search corporate records for ownership transfers
        4. Search court records for settlements, judgments
        5. Search web for reported transactions
        6. Build transaction chains
        7. Detect shell company patterns
        """
        # 1. Get/create financial entities for target
        entities = await self._get_financial_entities(
            request.entity_name,
            request.entity_id
        )

        forward_chains = []
        backward_chains = []

        if request.direction in ["forward", "both"]:
            forward_chains = await self._trace_forward(
                entities,
                request.max_hops,
                request.amount_filter,
                request.date_start,
                request.date_end
            )

        if request.direction in ["backward", "both"]:
            backward_chains = await self._trace_backward(
                entities,
                request.max_hops,
                request.amount_filter,
                request.date_start,
                request.date_end
            )

        # Detect suspicious patterns
        suspicious = []
        shell_companies = []
        if request.include_shell_detection:
            all_entities = self._extract_entities_from_chains(
                forward_chains + backward_chains
            )
            for entity in all_entities:
                if await self._is_shell_company(entity):
                    shell_companies.append(entity)
                    suspicious.append(
                        f"Potential shell company: {entity.name} ({entity.jurisdiction})"
                    )

        return TraceMoneyResponse(
            entity_name=request.entity_name,
            chains_found=len(forward_chains) + len(backward_chains),
            forward_chains=forward_chains,
            backward_chains=backward_chains,
            total_inflow=self._sum_chains(backward_chains),
            total_outflow=self._sum_chains(forward_chains),
            suspicious_patterns=suspicious,
            shell_companies_detected=shell_companies
        )

    async def get_corporate_structure(
        self,
        request: CorporateStructureRequest
    ) -> CorporateStructureResponse:
        """
        Build corporate ownership/control structure.

        Data sources:
        1. SEC EDGAR (for public companies)
        2. OpenCorporates (for registered companies)
        3. State corporate registries (via web search)
        4. Court documents (for revealed structures)
        """
        pass

    async def find_property_transfers(
        self,
        request: PropertySearchRequest
    ) -> PropertySearchResponse:
        """
        Find real estate owned/transferred by entity.

        Data sources:
        1. County assessor records (via web search)
        2. Court records (foreclosures, liens)
        3. News reports of property transactions
        """
        pass

    async def find_beneficial_owners(
        self,
        company_name: str
    ) -> List[BeneficialOwner]:
        """
        Identify ultimate beneficial owners of a company.
        Traces through shell companies and nominee structures.
        """
        pass

    async def _search_sec_filings(
        self,
        entity_name: str,
        filing_types: List[str]
    ) -> List[dict]:
        """Query SEC EDGAR for relevant filings."""
        # Use SEC EDGAR API
        # https://www.sec.gov/cgi-bin/browse-edgar
        pass

    async def _search_corporate_registry(
        self,
        entity_name: str,
        jurisdiction: Optional[str] = None
    ) -> List[FinancialEntity]:
        """Query corporate registries via OpenCorporates or direct."""
        # OpenCorporates API: https://api.opencorporates.com/
        pass

    async def _is_shell_company(
        self,
        entity: FinancialEntity
    ) -> bool:
        """
        Detect shell company indicators:
        - Registered in known secrecy jurisdictions
        - No physical address / registered agent only
        - No employees or revenue
        - Circular ownership patterns
        - Rapid ownership changes
        """
        shell_indicators = 0

        # Check jurisdiction (Delaware, Nevada, Wyoming, offshore)
        secrecy_jurisdictions = [
            "Delaware", "Nevada", "Wyoming",
            "Cayman Islands", "British Virgin Islands", "Panama"
        ]
        if entity.jurisdiction in secrecy_jurisdictions:
            shell_indicators += 1

        # Check for registered agent address only
        # Check for no public filings
        # etc.

        return shell_indicators >= 2

    async def _trace_forward(
        self,
        start_entities: List[FinancialEntity],
        max_hops: int,
        amount_filter: Optional[Decimal],
        date_start: Optional[date],
        date_end: Optional[date]
    ) -> List[TransactionChain]:
        """Trace where money went FROM these entities."""
        chains = []
        visited = set()

        async def trace_hop(
            current_entity: FinancialEntity,
            current_chain: List[FinancialTransaction],
            depth: int
        ):
            if depth >= max_hops:
                if current_chain:
                    chains.append(self._build_chain(current_chain))
                return

            if current_entity.id in visited:
                return
            visited.add(current_entity.id)

            # Find outgoing transactions
            transactions = await self._find_outgoing_transactions(
                current_entity,
                amount_filter,
                date_start,
                date_end
            )

            if not transactions:
                if current_chain:
                    chains.append(self._build_chain(current_chain))
                return

            for tx in transactions:
                await trace_hop(
                    tx.target_entity,
                    current_chain + [tx],
                    depth + 1
                )

        for entity in start_entities:
            await trace_hop(entity, [], 0)

        return chains
```

### 2.6 New API Endpoints

**Add to:** `backend/app/research/router.py`

```python
# Financial Research Endpoints

@router.post("/research/financial/trace-money")
async def trace_money(
    request: TraceMoneyRequest,
    db: SupabaseResearchDB = Depends(get_db)
) -> TraceMoneyResponse:
    """
    Trace financial transactions forward/backward from an entity.
    Identifies transaction chains and shell company patterns.
    """
    service = FinancialResearchService(db, gemini_client)
    return await service.trace_money(request)

@router.post("/research/financial/corporate-structure")
async def get_corporate_structure(
    request: CorporateStructureRequest,
    db: SupabaseResearchDB = Depends(get_db)
) -> CorporateStructureResponse:
    """
    Build corporate ownership hierarchy for an entity.
    Identifies subsidiaries, officers, and beneficial owners.
    """
    service = FinancialResearchService(db, gemini_client)
    return await service.get_corporate_structure(request)

@router.post("/research/financial/property-search")
async def search_properties(
    request: PropertySearchRequest,
    db: SupabaseResearchDB = Depends(get_db)
) -> PropertySearchResponse:
    """
    Find real estate holdings and transfers for an entity.
    """
    service = FinancialResearchService(db, gemini_client)
    return await service.find_property_transfers(request)

@router.get("/research/financial/entity/{entity_id}/transactions")
async def get_entity_transactions(
    entity_id: UUID,
    direction: Literal["inbound", "outbound", "all"] = "all",
    limit: int = 100,
    db: SupabaseResearchDB = Depends(get_db)
) -> List[FinancialTransaction]:
    """Get transactions for a financial entity."""
    return await db.get_financial_transactions(entity_id, direction, limit)

@router.get("/research/financial/entity/{entity_id}/beneficial-owners")
async def get_beneficial_owners(
    entity_id: UUID,
    db: SupabaseResearchDB = Depends(get_db)
) -> List[BeneficialOwner]:
    """Get beneficial owners of a company."""
    service = FinancialResearchService(db, gemini_client)
    entity = await db.get_financial_entity(entity_id)
    return await service.find_beneficial_owners(entity.name)
```

---

## Direction 3: Temporal Causality Graph

### 3.1 Problem Statement

Current system treats events as isolated facts. Missing:
- "X happened BECAUSE of Y"
- "X ENABLED Y to happen"
- "X PREVENTED Y from happening"
- Causal chains spanning multiple events

### 3.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CausalityService                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Causality Types:                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ CAUSED_BY    - Direct causation (A caused B)            │   │
│  │ ENABLED_BY   - Necessary condition (A enabled B)        │   │
│  │ PREVENTED_BY - Counterfactual (A prevented B)           │   │
│  │ TRIGGERED_BY - Immediate trigger (A triggered B)        │   │
│  │ PRECEDED     - Temporal order only (A before B)         │   │
│  │ RESULTED_IN  - Consequence (A resulted in B)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Event Timeline with Causality:                                 │
│                                                                  │
│  1991 ───┬─── Wexner grants POA ──────────────────────────────▶│
│          │         │                                            │
│          │         ▼ ENABLED                                    │
│  1995 ───┼─── Mansion transfer ($13.2M) ─────────────────────▶ │
│          │         │                                            │
│          │         ▼ ENABLED                                    │
│  2000 ───┼─── Giuffre recruitment ───────────────────────────▶ │
│          │         │                                            │
│          │         ▼ RESULTED_IN                               │
│  2005 ───┼─── Police investigation ──────────────────────────▶ │
│          │         │                                            │
│          │         ▼ TRIGGERED                                  │
│  2008 ───┼─── NPA signed ────────────────────────────────────▶ │
│          │         │                                            │
│          │         ▼ ENABLED (counterfactually)                │
│  2019 ───┴─── Continued operations ──────────────────────────▶ │
│                                                                  │
│  Capabilities:                                                   │
│  - extract_causality(event_a, event_b) → CausalLink            │
│  - find_causes(event) → List[CausalChain]                      │
│  - find_consequences(event) → List[CausalChain]                │
│  - build_causal_graph(topic) → CausalGraph                     │
│  - detect_causal_patterns(entity) → List[CausalPattern]        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Extended Database Schema

The existing `claim_relationships` table already supports causality types. We'll extend it:

```sql
-- Extend claim_relationships with causality metadata
ALTER TABLE claim_relationships ADD COLUMN IF NOT EXISTS
    causality_confidence FLOAT DEFAULT 0.5;
    -- 0.0-1.0, how confident are we in the causal link?

ALTER TABLE claim_relationships ADD COLUMN IF NOT EXISTS
    causality_mechanism TEXT;
    -- How does A cause B? "financial_dependency", "legal_authority", etc.

ALTER TABLE claim_relationships ADD COLUMN IF NOT EXISTS
    temporal_gap_days INTEGER;
    -- Days between events (NULL if unknown)

ALTER TABLE claim_relationships ADD COLUMN IF NOT EXISTS
    counterfactual_reasoning TEXT;
    -- "If A hadn't happened, B would not have occurred because..."

-- New table: causal_chains (pre-computed chains for fast queries)
CREATE TABLE causal_chains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_type TEXT NOT NULL,
    -- cause_chain, consequence_chain, enabling_chain
    start_claim_id UUID NOT NULL REFERENCES knowledge_claims(id),
    end_claim_id UUID NOT NULL REFERENCES knowledge_claims(id),
    chain_length INTEGER NOT NULL,
    claim_ids UUID[] NOT NULL,
    -- Ordered array of claim IDs in chain
    relationship_types TEXT[] NOT NULL,
    -- Ordered array of relationship types
    total_confidence FLOAT NOT NULL,
    -- Product of individual confidences
    narrative TEXT,
    -- Human-readable chain description
    workspace_id TEXT NOT NULL DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(start_claim_id, end_claim_id, chain_type)
);

-- New table: causal_patterns (detected recurring patterns)
CREATE TABLE causal_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_name TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    -- enabling_network, cover_up, escalation, retaliation
    description TEXT,
    involved_entities UUID[] NOT NULL,
    -- Array of entity IDs involved
    claim_ids UUID[] NOT NULL,
    -- Claims that form this pattern
    confidence FLOAT NOT NULL,
    first_detected_at TIMESTAMPTZ DEFAULT NOW(),
    occurrence_count INTEGER DEFAULT 1
);

-- Indexes for causal queries
CREATE INDEX idx_causal_chains_start ON causal_chains(start_claim_id);
CREATE INDEX idx_causal_chains_end ON causal_chains(end_claim_id);
CREATE INDEX idx_claim_rel_causality ON claim_relationships(relationship_type)
    WHERE relationship_type IN ('causes', 'enables', 'prevents', 'triggers', 'precedes');
```

### 3.4 New Schemas

**File:** `backend/app/research/schemas/causality.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from uuid import UUID
from datetime import datetime
from enum import Enum

class CausalityType(str, Enum):
    CAUSED_BY = "caused_by"       # Direct causation
    ENABLED_BY = "enabled_by"     # Necessary condition
    PREVENTED_BY = "prevented_by" # Blocked outcome
    TRIGGERED_BY = "triggered_by" # Immediate trigger
    PRECEDED = "preceded"         # Temporal only
    RESULTED_IN = "resulted_in"   # Consequence
    CONTRIBUTED_TO = "contributed_to"  # Partial cause

class CausalMechanism(str, Enum):
    FINANCIAL = "financial"           # Money enabled/caused
    LEGAL = "legal"                   # Legal authority/constraint
    ORGANIZATIONAL = "organizational" # Hierarchy/control
    INFORMATIONAL = "informational"   # Knowledge transfer
    SOCIAL = "social"                 # Relationship/trust
    PHYSICAL = "physical"             # Physical presence/action
    POLITICAL = "political"           # Political power/influence

class CausalLink(BaseModel):
    source_event: str
    source_claim_id: Optional[UUID] = None
    target_event: str
    target_claim_id: Optional[UUID] = None
    causality_type: CausalityType
    confidence: float = Field(ge=0.0, le=1.0)
    mechanism: Optional[CausalMechanism] = None
    temporal_gap_days: Optional[int] = None
    reasoning: str
    counterfactual: Optional[str] = None
    # "If X hadn't happened, Y would not have occurred"
    evidence: List[str] = []

class CausalChain(BaseModel):
    chain_id: Optional[UUID] = None
    chain_type: str  # cause_chain, consequence_chain
    events: List[str]  # Human-readable event descriptions
    claim_ids: List[UUID]
    links: List[CausalLink]
    total_confidence: float
    chain_length: int
    narrative: str  # "A led to B, which enabled C, resulting in D"
    time_span_days: Optional[int] = None

class CausalPattern(BaseModel):
    pattern_id: Optional[UUID] = None
    pattern_name: str
    pattern_type: str
    # enabling_network, cover_up, escalation, retaliation, protection_racket
    description: str
    involved_entities: List[str]
    events: List[str]
    confidence: float
    occurrences: int = 1

class CausalGraph(BaseModel):
    topic: str
    nodes: List[dict]  # {id, label, type, date}
    edges: List[dict]  # {source, target, type, confidence}
    key_causes: List[str]  # Root causes identified
    key_consequences: List[str]  # Final outcomes
    patterns_detected: List[CausalPattern]

# Request/Response schemas
class ExtractCausalityRequest(BaseModel):
    event_a: str
    event_a_claim_id: Optional[UUID] = None
    event_b: str
    event_b_claim_id: Optional[UUID] = None
    context: Optional[str] = None
    # Additional context to help determine causality

class FindCausesRequest(BaseModel):
    event: str
    event_claim_id: Optional[UUID] = None
    max_depth: int = Field(default=5, ge=1, le=10)
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    include_indirect: bool = True

class FindCausesResponse(BaseModel):
    event: str
    direct_causes: List[CausalLink]
    causal_chains: List[CausalChain]
    root_causes: List[str]  # Ultimate causes (no further causes found)
    total_causes_found: int

class FindConsequencesRequest(BaseModel):
    event: str
    event_claim_id: Optional[UUID] = None
    max_depth: int = Field(default=5, ge=1, le=10)
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    include_indirect: bool = True

class FindConsequencesResponse(BaseModel):
    event: str
    direct_consequences: List[CausalLink]
    consequence_chains: List[CausalChain]
    final_outcomes: List[str]  # Terminal consequences
    total_consequences_found: int

class BuildCausalGraphRequest(BaseModel):
    topic: str
    topic_id: Optional[UUID] = None
    entity_focus: Optional[List[str]] = None
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
```

### 3.5 New Service

**File:** `backend/app/research/services/causality_service.py`

```python
class CausalityService:
    """
    Extracts and manages causal relationships between events/claims.
    Builds causal graphs and detects causal patterns.
    """

    def __init__(
        self,
        db: SupabaseResearchDB,
        inference_client: InferenceClient
    ):
        self.db = db
        self.inference = inference_client

    async def extract_causality(
        self,
        request: ExtractCausalityRequest
    ) -> CausalLink:
        """
        Determine causal relationship between two events using LLM.

        Returns the most likely causal link with confidence and reasoning.
        """
        prompt = f"""
        Analyze the causal relationship between these two events:

        Event A: {request.event_a}
        Event B: {request.event_b}

        Additional context: {request.context or 'None provided'}

        Determine:
        1. Is there a causal relationship? (yes/no/uncertain)
        2. What type of relationship?
           - caused_by: A directly caused B
           - enabled_by: A was necessary for B but didn't directly cause it
           - prevented_by: A prevented B from happening
           - triggered_by: A was the immediate trigger for B
           - preceded: A happened before B but no clear causation
           - resulted_in: B is a consequence of A
           - contributed_to: A partially contributed to B
        3. What is the mechanism? (financial, legal, organizational, etc.)
        4. Confidence level (0.0-1.0)
        5. Counterfactual test: "If A hadn't happened, would B still have occurred?"

        Return JSON:
        {{
            "has_causal_relationship": true/false,
            "causality_type": "caused_by|enabled_by|...",
            "direction": "a_to_b|b_to_a|bidirectional|none",
            "mechanism": "financial|legal|organizational|...",
            "confidence": 0.0-1.0,
            "reasoning": "explanation of causal link",
            "counterfactual": "If A hadn't happened...",
            "evidence_needed": ["what evidence would confirm this"]
        }}
        """

        result, _ = await self.inference.generate_json(prompt)

        if not result.get("has_causal_relationship"):
            return CausalLink(
                source_event=request.event_a,
                target_event=request.event_b,
                causality_type=CausalityType.PRECEDED,
                confidence=0.1,
                reasoning="No clear causal relationship detected"
            )

        # Build and return CausalLink
        return CausalLink(
            source_event=request.event_a if result["direction"] == "a_to_b" else request.event_b,
            target_event=request.event_b if result["direction"] == "a_to_b" else request.event_a,
            causality_type=CausalityType(result["causality_type"]),
            confidence=result["confidence"],
            mechanism=CausalMechanism(result["mechanism"]) if result.get("mechanism") else None,
            reasoning=result["reasoning"],
            counterfactual=result.get("counterfactual"),
            evidence=result.get("evidence_needed", [])
        )

    async def find_causes(
        self,
        request: FindCausesRequest
    ) -> FindCausesResponse:
        """
        Find all causes (direct and indirect) of an event.

        Process:
        1. Get direct causes from existing relationships
        2. For each direct cause, recursively find its causes
        3. Build causal chains
        4. Identify root causes (no further causes found)
        """
        direct_causes = []
        causal_chains = []
        root_causes = []
        visited = set()

        async def trace_causes(
            current_event: str,
            current_claim_id: Optional[UUID],
            current_chain: List[CausalLink],
            depth: int
        ):
            if depth >= request.max_depth:
                return

            if current_claim_id and current_claim_id in visited:
                return
            if current_claim_id:
                visited.add(current_claim_id)

            # Find causes of current event
            causes = await self._get_causes_of(
                current_event,
                current_claim_id,
                request.min_confidence
            )

            if not causes:
                # This is a root cause
                if current_chain:
                    root_causes.append(current_event)
                    causal_chains.append(self._build_chain(current_chain))
                return

            if depth == 0:
                direct_causes.extend(causes)

            for cause in causes:
                await trace_causes(
                    cause.source_event,
                    cause.source_claim_id,
                    current_chain + [cause],
                    depth + 1
                )

        await trace_causes(
            request.event,
            request.event_claim_id,
            [],
            0
        )

        return FindCausesResponse(
            event=request.event,
            direct_causes=direct_causes,
            causal_chains=causal_chains,
            root_causes=list(set(root_causes)),
            total_causes_found=len(visited)
        )

    async def find_consequences(
        self,
        request: FindConsequencesRequest
    ) -> FindConsequencesResponse:
        """
        Find all consequences (direct and indirect) of an event.
        Mirror of find_causes but following forward in time.
        """
        # Similar implementation to find_causes but tracing forward
        pass

    async def build_causal_graph(
        self,
        request: BuildCausalGraphRequest
    ) -> CausalGraph:
        """
        Build complete causal graph for a topic.

        Process:
        1. Get all claims for topic
        2. Extract temporal ordering
        3. Determine causal relationships between temporally adjacent events
        4. Build graph structure
        5. Detect patterns
        """
        # 1. Get claims
        claims = await self.db.get_claims_by_topic(
            request.topic_id,
            request.time_start,
            request.time_end
        )

        # 2. Sort by date
        claims_sorted = sorted(
            claims,
            key=lambda c: c.temporal_context.get("date") or "9999"
        )

        # 3. Extract causality between adjacent/related events
        edges = []
        for i, claim_a in enumerate(claims_sorted):
            for claim_b in claims_sorted[i+1:i+5]:  # Check next 4 events
                link = await self.extract_causality(
                    ExtractCausalityRequest(
                        event_a=claim_a.content,
                        event_a_claim_id=claim_a.id,
                        event_b=claim_b.content,
                        event_b_claim_id=claim_b.id
                    )
                )
                if link.confidence >= request.min_confidence:
                    edges.append({
                        "source": str(claim_a.id),
                        "target": str(claim_b.id),
                        "type": link.causality_type.value,
                        "confidence": link.confidence,
                        "mechanism": link.mechanism.value if link.mechanism else None
                    })

        # 4. Build nodes
        nodes = [
            {
                "id": str(c.id),
                "label": c.content[:100],
                "type": c.claim_type,
                "date": c.temporal_context.get("date")
            }
            for c in claims_sorted
        ]

        # 5. Detect patterns
        patterns = await self._detect_patterns(nodes, edges, request.entity_focus)

        # 6. Identify root causes and final outcomes
        root_causes = self._find_root_nodes(nodes, edges)
        final_outcomes = self._find_leaf_nodes(nodes, edges)

        return CausalGraph(
            topic=request.topic,
            nodes=nodes,
            edges=edges,
            key_causes=root_causes,
            key_consequences=final_outcomes,
            patterns_detected=patterns
        )

    async def _detect_patterns(
        self,
        nodes: List[dict],
        edges: List[dict],
        entity_focus: Optional[List[str]]
    ) -> List[CausalPattern]:
        """
        Detect recurring causal patterns.

        Patterns to detect:
        - Enabling network: Multiple entities enabling a single outcome
        - Cover-up: Actions to hide/minimize consequences
        - Escalation: Progressive increase in severity
        - Retaliation: Response to perceived threats
        - Protection racket: Reciprocal protection relationships
        """
        patterns = []

        # Use LLM to detect patterns
        prompt = f"""
        Analyze this causal graph for patterns:

        Nodes: {nodes[:20]}
        Edges: {edges[:30]}

        Look for these pattern types:
        1. Enabling Network: Multiple people/orgs enabling a single bad outcome
        2. Cover-up: Sequence of actions to hide wrongdoing
        3. Escalation: Events getting progressively worse
        4. Protection: People protecting each other from consequences
        5. Retaliation: Response to threats or exposure

        Return JSON:
        {{
            "patterns": [
                {{
                    "type": "enabling_network|cover_up|escalation|protection|retaliation",
                    "name": "short descriptive name",
                    "description": "what the pattern shows",
                    "involved_nodes": ["node_id1", "node_id2"],
                    "confidence": 0.0-1.0
                }}
            ]
        }}
        """

        result, _ = await self.inference.generate_json(prompt)

        for p in result.get("patterns", []):
            patterns.append(CausalPattern(
                pattern_name=p["name"],
                pattern_type=p["type"],
                description=p["description"],
                involved_entities=[],  # Would need entity extraction
                events=[nodes[n]["label"] for n in p["involved_nodes"] if n in nodes],
                confidence=p["confidence"]
            ))

        return patterns

    async def _get_causes_of(
        self,
        event: str,
        claim_id: Optional[UUID],
        min_confidence: float
    ) -> List[CausalLink]:
        """Get known causes of an event from database."""
        if claim_id:
            # Query existing relationships
            relationships = await self.db.get_related_claims(
                claim_id,
                relationship_types=["causes", "enables", "triggers"]
            )
            return [
                CausalLink(
                    source_event=r.source_claim.content,
                    source_claim_id=r.source_claim_id,
                    target_event=event,
                    target_claim_id=claim_id,
                    causality_type=CausalityType(r.relationship_type),
                    confidence=r.strength or 0.5,
                    reasoning="From existing knowledge base"
                )
                for r in relationships
                if (r.strength or 0.5) >= min_confidence
            ]
        return []
```

### 3.6 New API Endpoints

**Add to:** `backend/app/research/router.py`

```python
# Causality Endpoints

@router.post("/research/causality/extract")
async def extract_causality(
    request: ExtractCausalityRequest,
    db: SupabaseResearchDB = Depends(get_db)
) -> CausalLink:
    """
    Determine causal relationship between two events.
    Uses LLM reasoning with counterfactual analysis.
    """
    service = CausalityService(db, inference_client)
    return await service.extract_causality(request)

@router.post("/research/causality/find-causes")
async def find_causes(
    request: FindCausesRequest,
    db: SupabaseResearchDB = Depends(get_db)
) -> FindCausesResponse:
    """
    Find all causes (direct and indirect) of an event.
    Traces back through causal chains to root causes.
    """
    service = CausalityService(db, inference_client)
    return await service.find_causes(request)

@router.post("/research/causality/find-consequences")
async def find_consequences(
    request: FindConsequencesRequest,
    db: SupabaseResearchDB = Depends(get_db)
) -> FindConsequencesResponse:
    """
    Find all consequences (direct and indirect) of an event.
    Traces forward through causal chains to final outcomes.
    """
    service = CausalityService(db, inference_client)
    return await service.find_consequences(request)

@router.post("/research/causality/build-graph")
async def build_causal_graph(
    request: BuildCausalGraphRequest,
    db: SupabaseResearchDB = Depends(get_db)
) -> CausalGraph:
    """
    Build complete causal graph for a topic.
    Identifies patterns and key causal relationships.
    """
    service = CausalityService(db, inference_client)
    return await service.build_causal_graph(request)

@router.get("/research/causality/patterns/{topic_id}")
async def get_causal_patterns(
    topic_id: UUID,
    pattern_type: Optional[str] = None,
    db: SupabaseResearchDB = Depends(get_db)
) -> List[CausalPattern]:
    """Get detected causal patterns for a topic."""
    return await db.get_causal_patterns(topic_id, pattern_type)

@router.get("/research/causality/chain/{claim_id}")
async def get_causal_chain(
    claim_id: UUID,
    direction: Literal["causes", "consequences", "both"] = "both",
    max_depth: int = 5,
    db: SupabaseResearchDB = Depends(get_db)
) -> dict:
    """Get pre-computed causal chains for a claim."""
    return await db.get_causal_chains(claim_id, direction, max_depth)
```

---

## Implementation Order & Dependencies

### Phase 1: Foundation (Shared Components)

```
Week 1-2:
├── Database migrations for all three directions
├── Base schema classes (recursive.py, financial.py, causality.py)
├── DB operation classes for new tables
└── Unit tests for schemas
```

### Phase 2: Recursive CoI

```
Week 3-4:
├── RecursiveResearchService core
├── Follow-up generation logic
├── Saturation calculation
├── Tree traversal and result compilation
├── API endpoints
└── Integration tests
```

### Phase 3: Temporal Causality

```
Week 5-6:
├── CausalityService core
├── LLM prompts for causality extraction
├── Causal chain building
├── Pattern detection
├── API endpoints
└── Integration with existing claim_relationships
```

### Phase 4: Financial Trail Blazer

```
Week 7-9:
├── FinancialResearchService core
├── Transaction chain tracing
├── Shell company detection
├── Corporate structure building
├── API endpoints
└── Integration tests with mock data
```

### Phase 5: Integration

```
Week 10:
├── Integrate recursive research with financial/causality
├── End-to-end testing with Epstein case data
├── Performance optimization
└── Documentation
```

---

## Testing Strategy

### Unit Tests
- Schema validation
- Database operations
- LLM prompt parsing
- Chain building algorithms

### Integration Tests
- Full recursive research flow
- Financial transaction tracing
- Causal graph building
- API endpoint testing

### Validation Tests (Epstein Case)
- "Trace Wexner money to Epstein" → Should find POA, mansion transfer
- "Find causes of 2008 NPA" → Should trace to Palm Beach investigation, legal pressure
- "Find consequences of NPA" → Should find continued operations, 2019 arrest
- "Recursive research: How did Epstein acquire wealth?" → Should reach 5+ levels

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| LLM hallucination in causality | Require evidence citations, confidence thresholds |
| Infinite recursion | Strict depth limits, saturation detection, visited set |
| Cost explosion from deep research | Node limits, cost tracking, user budgets |
| Slow performance | Parallel execution, pre-computation of chains, caching |

---

## Success Metrics

1. **Depth Improvement**: Average research depth increases from 2 to 5+ levels
2. **Financial Coverage**: 80% of financial questions answered with primary source citations
3. **Causality Accuracy**: Manual validation shows 85%+ accurate causal links
4. **Query Time**: Deep research completes in <5 minutes for typical queries
5. **User Value**: Investigation reports include 3x more actionable insights

---

## Files to Create

```
backend/app/research/
├── schemas/
│   ├── recursive.py          # NEW
│   ├── financial.py          # NEW
│   └── causality.py          # NEW
├── services/
│   ├── recursive_research_service.py  # NEW
│   ├── financial_research_service.py  # NEW
│   └── causality_service.py           # NEW
├── db/
│   ├── recursive.py          # NEW (tree/node operations)
│   ├── financial.py          # NEW (transaction operations)
│   └── causality.py          # NEW (causal chain operations)
└── supabase/migrations/
    ├── 005_add_recursive_research.sql  # NEW
    ├── 006_add_financial_entities.sql  # NEW
    └── 007_extend_causality.sql        # NEW
```


*Document created: December 29, 2025*
*Status: Design Decisions Confirmed - Ready for Implementation*
