# Research Module

Deep investigative research system with multi-perspective analysis, relationship graphing, and knowledge extraction.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Enhanced Research Harness                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │    Query     │───▶│    Search    │───▶│   Extract    │       │
│  │ Decomposer   │    │   (Gemini)   │    │   Findings   │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                                        │               │
│         ▼                                        ▼               │
│  ┌──────────────┐                        ┌──────────────┐       │
│  │  Sub-Query   │                        │   Timeline   │       │
│  │  Execution   │                        │   Builder    │       │
│  └──────────────┘                        └──────────────┘       │
│                                                  │               │
│                                                  ▼               │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              Perspective Agents (Parallel)            │       │
│  ├──────────┬──────────┬──────────┬──────────┬─────────┤       │
│  │Historical│Financial │Journalist│Conspirat.│ Network │       │
│  └──────────┴──────────┴──────────┴──────────┴─────────┘       │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              Relationship Builder                      │       │
│  ├──────────────┬──────────────┬──────────────┐         │       │
│  │Relationships │Contradictions│ Causal Chains│         │       │
│  │    Graph     │  Detection   │   Building   │         │       │
│  └──────────────┴──────────────┴──────────────┘         │       │
│                                                          │       │
└──────────────────────────────────────────────────────────┘       │
```

## Dual-Client Architecture

| Client | Model | Purpose |
|--------|-------|---------|
| **Gemini Native** | `gemini-2.0-flash` | Web search with Google Search grounding |
| **OpenRouter** | `google/gemini-3-flash-preview` | Inference for perspectives, decomposition, relationships |

## Components

### 1. Query Decomposer (`decomposer.py`)

Analyzes complex queries and decomposes them into focused sub-queries.

**Features:**
- Detects long date ranges (>5 years) that benefit from temporal decomposition
- Identifies multi-theme queries for thematic decomposition
- Generates sub-queries with execution ordering and dependencies
- Supports batch composition with roles: `background`, `primary`, `synthesis`

**Strategies:**
- `temporal` - Split by time periods
- `thematic` - Split by themes/aspects
- `actor` - Split by key actors
- `hybrid` - Combination of strategies

### 2. Perspective Agents (`perspectives/`)

Five specialized analysis agents providing multi-perspective insights:

| Agent | Focus | Key Outputs |
|-------|-------|-------------|
| **Historical** | Historical context, precedents, patterns | Parallels, cycles, long-term forces |
| **Financial** | Economic motivations, money flows | Cui bono, stakeholders, sanctions impact |
| **Journalist** | Source credibility, contradictions | Propaganda patterns, unanswered questions |
| **Conspirator** | Hidden motivations, probable theories | Theory with supporting/counter evidence |
| **Network** | Actor relationships, power dynamics | Relationship map, intermediaries, brokers |

### 3. Relationship Builder (`relationship_builder.py`)

Builds a knowledge graph from research findings.

**Relationship Types:**
- `CAUSES` - Finding A led to/caused Finding B
- `SUPPORTS` - Finding A provides evidence for Finding B
- `CONTRADICTS` - Finding A conflicts with Finding B
- `EXPANDS` - Finding A adds detail to Finding B
- `PRECEDES` - Finding A happened before Finding B
- `INVOLVES` - Findings share common actors/entities

**Additional Analysis:**
- **Contradictions** - Conflicting claims with resolution hints
- **Research Gaps** - Missing coverage (temporal, actor, thematic, causal)
- **Causal Chains** - Sequences of cause-effect relationships

### 4. Date Utilities (`date_utils.py`)

Date extraction and timeline building.

**Supported Formats:**
- Full dates: `February 24, 2022`
- Month/year: `March 2014`
- Year ranges: `2014-2022`
- Relative: `early 2022`, `late 2021`
- Seasons: `spring 2014`

### 5. Schemas (`schemas/`)

Pydantic-style dataclasses for structured data:

- `finding.py` - Finding types with actors, sources, perspectives
- `perspective.py` - Analysis structures for each perspective type
- `relationship.py` - Graph edges, contradictions, gaps, chains

## Usage

### Basic Test
```python
from test_harness import ResearchTestHarness

harness = ResearchTestHarness()
result = await harness.run_test(
    query="Why did the Russia-Ukraine war start?",
    template_type="investigative",
    max_searches=5,
    perspectives=["political", "historical"],
    granularity="standard"
)
```

### Enhanced Test (All Features)
```python
from enhanced_harness import EnhancedResearchHarness

harness = EnhancedResearchHarness()
result = await harness.run_enhanced_test(
    query="Why did the Russia-Ukraine war start?",
    max_searches=4,
    run_decomposition=True,    # Query decomposition
    run_perspectives=True,     # 5 perspective agents
    run_relationships=True,    # Knowledge graph building
)
```

### Run Tests
```bash
# Basic inference client test
python test_inference.py

# Query decomposition test
python test_decomposer.py

# Perspective agents test
python test_perspectives.py

# Relationship builder test
python test_relationships.py

# Full enhanced integration test
python test_enhanced.py

# Evaluation test suite
python -m tests.research.run_test --list
python -m tests.research.run_test ukraine_war_origins
```

## Output Structure

### JSON Result Format
```json
{
  "query": "Research query",
  "decomposition": {
    "needs_decomposition": true,
    "strategy": "hybrid",
    "detected_themes": ["Theme1", "Theme2"],
    "sub_queries": [...]
  },
  "findings": [
    {
      "type": "event|actor|evidence|pattern|gap",
      "content": "Finding content",
      "summary": "Brief summary",
      "date_text": "February 2022"
    }
  ],
  "timeline": [
    {"date": "February 24, 2022", "summary": "Event summary"}
  ],
  "perspectives": {
    "historical": {"analysis": "...", "data": {...}},
    "financial": {"analysis": "...", "data": {...}},
    "journalist": {"analysis": "...", "data": {...}},
    "conspirator": {"analysis": "...", "data": {...}},
    "network": {"analysis": "...", "data": {...}}
  },
  "relationship_graph": {
    "relationships": [...],
    "contradictions": [...],
    "gaps": [...],
    "causal_chains": [...]
  },
  "metrics": {
    "total_tokens": 9473,
    "total_cost_usd": 0.0022
  }
}
```

## Performance

Typical enhanced test metrics:
- **Duration**: 60-90 seconds
- **Token Usage**: ~10,000-15,000 tokens
- **Cost**: ~$0.002-0.004 USD
- **Findings**: 20-30 findings extracted
- **Sources**: 15-25 web sources

## File Structure

```
tests/research/
├── README.md                  # This file
├── gemini_client.py           # Gemini native client with Google Search
├── inference_client.py        # OpenRouter client for inference
├── test_harness.py            # Base research test harness
├── enhanced_harness.py        # Enhanced harness with all features
├── decomposer.py              # Query decomposition
├── relationship_builder.py    # Knowledge graph building
├── date_utils.py              # Date extraction and timeline
├── evaluation.py              # Test result evaluation
├── run_test.py                # Test runner with CLI
│
├── perspectives/              # Perspective agents
│   ├── __init__.py
│   ├── base.py                # Base agent class
│   ├── agents.py              # 5 specialized agents
│   └── runner.py              # Parallel execution
│
├── schemas/                   # Data schemas
│   ├── __init__.py
│   ├── finding.py             # Finding structures
│   ├── perspective.py         # Perspective analysis structures
│   └── relationship.py        # Graph relationships
│
├── supabase/                  # Database schemas
│   ├── schema.sql             # Complete base schema with advanced indexes
│   └── migrations/
│       └── 001_add_research_enhancements.sql  # New tables for enhanced features
│
├── test_cases/                # Test case definitions
│   └── ukraine_war.py         # Ukraine war test cases
│
├── results/                   # Test output JSON files
│
└── test_*.py                  # Individual test scripts
```

## Database Setup (Supabase)

The research module uses Supabase (PostgreSQL) for persistent storage. Schema files are located in two places:

### Schema Files

| File | Location | Purpose |
|------|----------|---------|
| `supabase_schema.sql` | `backend/app/research/supabase/` | **Base schema** - Core tables for research sessions, findings, sources, perspectives |
| `schema.sql` | `backend/tests/research/supabase/` | **Complete schema** - Base + enhanced perspective types + advanced indexes |
| `001_add_research_enhancements.sql` | `backend/tests/research/supabase/migrations/` | **Migration** - New tables for decomposition, relationships, finding-level perspectives |

### Setup Instructions

**Scenario 1: Existing Deployment (Base Schema Already Applied)**

If you already have the base schema deployed from `backend/app/research/supabase/supabase_schema.sql`:

```bash
# Only run the migration to add new tables
psql -d your_database -f backend/tests/research/supabase/migrations/001_add_research_enhancements.sql
```

This adds:
- `query_decompositions` - Query decomposition tracking
- `sub_queries` - Sub-queries from decomposition
- `finding_relationships` - Finding-to-finding relationships
- `research_contradictions` - Detected contradictions between findings
- `research_gaps` - Identified research gaps
- `causal_chains` - Cause-effect sequences
- `finding_perspectives` - Finding-level perspective analyses

**Scenario 2: Fresh Deployment**

If starting fresh, run both in order:

```bash
# 1. Run base schema
psql -d your_database -f backend/app/research/supabase/supabase_schema.sql

# 2. Run migration for enhanced features
psql -d your_database -f backend/tests/research/supabase/migrations/001_add_research_enhancements.sql
```

Or alternatively, run the complete schema which includes advanced indexes:

```bash
# Complete schema with advanced indexes (base tables only)
psql -d your_database -f backend/tests/research/supabase/schema.sql

# Then run migration for new tables
psql -d your_database -f backend/tests/research/supabase/migrations/001_add_research_enhancements.sql
```

### Advanced Indexing

Both schema files include advanced indexing strategies optimized for high-volume tables:

- **Composite indexes** - Multi-column indexes for common query patterns
- **Partial indexes** - Filtered indexes (e.g., high-priority gaps only)
- **GIN indexes** - For array columns (`finding_ids`, `detected_themes`)
- **JSONB indexes** - For querying inside `analysis_data` JSON fields
- **BRIN indexes** - Time-series optimization for `created_at` columns
- **Hash indexes** - Fast exact-match lookups on UUIDs

Storage optimizations are also included:
- Adjusted `fillfactor` for frequently updated tables
- Custom `autovacuum` settings for high-write tables
- Extended statistics targets for better query planning

## Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_google_api_key       # For Gemini native client
OPENROUTER_API_KEY=your_openrouter_key   # For inference client

# Optional
GEMINI_API_KEY=your_gemini_key           # Alternative to GOOGLE_API_KEY
SUPABASE_URL=your_supabase_url           # For database persistence
SUPABASE_KEY=your_supabase_key           # Supabase API key
```

## Dependencies

```
google-genai          # Google Gemini SDK
httpx                 # Async HTTP client
python-dotenv         # Environment variable loading
```
