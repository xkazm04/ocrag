# Intelligent RAG System — Enhanced Requirements

## Addendum: Addressing Bottlenecks & Alternative Architecture

This document extends the original requirements with:
1. **Part 11**: Pre-filter system using DB metadata + LLM query transformation
2. **Part 12**: Enhanced document map extraction prompts for quality improvement
3. **Part 13**: Alternative architecture — Agentic SQL RAG with LangChain

---

## Part 11: Pre-Filter System (Before Map Consultation)

### Concept

Add a lightweight pre-filtering layer that uses PostgreSQL metadata queries and LLM-based query transformation to reduce the candidate document set *before* consulting the document map. This keeps the map consultation focused and efficient at scale.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENHANCED RETRIEVAL FLOW                             │
└─────────────────────────────────────────────────────────────────────────────┘

User Query: "What were APAC revenue figures in Q3?"
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 1: QUERY ANALYSIS & TRANSFORMATION                         │
│                                                                  │
│ LLM extracts structured filters from natural language:           │
│ {                                                                │
│   "time_references": ["Q3", "2025"],                            │
│   "entities": ["APAC"],                                         │
│   "topics": ["revenue", "financial"],                           │
│   "document_types": ["financial_report", "earnings"],           │
│   "transformed_query": "APAC region revenue Q3 2025 figures"    │
│ }                                                                │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 2: DATABASE PRE-FILTER                                     │
│                                                                  │
│ SQL query against document metadata:                             │
│                                                                  │
│ SELECT id FROM documents                                         │
│ WHERE workspace_id = 'default'                                   │
│   AND (                                                          │
│     metadata->>'topics' @> '["revenue"]'                        │
│     OR metadata->>'topics' @> '["financial"]'                   │
│   )                                                              │
│   AND (                                                          │
│     metadata->>'entities'->'dates' @> '["Q3"]'                  │
│     OR filename ILIKE '%Q3%'                                    │
│     OR filename ILIKE '%earnings%'                              │
│   )                                                              │
│ LIMIT 20;                                                        │
│                                                                  │
│ Result: [doc_001, doc_003, doc_007, doc_012, doc_015]           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 3: FOCUSED MAP CONSULTATION                                │
│                                                                  │
│ Document map filtered to only candidate documents:               │
│ - Smaller context = faster + cheaper                             │
│ - More precise selection                                         │
│ - No re-ranking needed post-retrieval                           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 4: RETRIEVE & GENERATE                                     │
│                                                                  │
│ (Existing flow)                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Implementation

#### 1. Enhanced Document Metadata Schema

```python
# backend/app/db/models.py — Extended

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(50), primary_key=True)
    workspace_id = Column(String(50), default="default", index=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    size_class = Column(String(20), default="small")
    token_count = Column(Integer, default=0)
    
    # Enhanced metadata for filtering (JSONB for PostgreSQL)
    metadata = Column(JSONB, default={})
    
    # Denormalized fields for fast filtering
    document_type = Column(String(50), index=True)  # financial_report, legal, technical, etc.
    primary_date = Column(Date, index=True)          # Main date reference in document
    date_range_start = Column(Date)                  # For documents spanning periods
    date_range_end = Column(Date)
    
    # Array fields for containment queries
    topics = Column(ARRAY(String), default=[])       # ["revenue", "APAC", "growth"]
    entities_orgs = Column(ARRAY(String), default=[])  # ["Acme Corp", "TechVentures"]
    entities_people = Column(ARRAY(String), default=[])
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_topics_gin', topics, postgresql_using='gin'),
        Index('idx_entities_orgs_gin', entities_orgs, postgresql_using='gin'),
        Index('idx_document_type', document_type),
        Index('idx_date_range', date_range_start, date_range_end),
    )
```

#### 2. Query Analyzer

```python
# backend/app/core/query_analyzer.py

"""
Query analysis and transformation for pre-filtering.
Extracts structured metadata from natural language queries.
"""

from typing import Optional
from datetime import date
from pydantic import BaseModel
from app.core.gemini_client import get_gemini_client


class QueryAnalysis(BaseModel):
    """Structured query analysis result."""
    original_query: str
    transformed_query: str  # Cleaned/expanded for better matching
    
    # Temporal filters
    time_references: list[str] = []  # ["Q3", "2025", "last quarter"]
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    
    # Entity filters
    organizations: list[str] = []
    people: list[str] = []
    locations: list[str] = []
    
    # Topic filters
    topics: list[str] = []
    
    # Document type hints
    likely_document_types: list[str] = []
    
    # Query characteristics
    is_comparison: bool = False  # "compare X and Y"
    is_temporal: bool = False    # "what changed", "over time"
    is_factual: bool = False     # "what is", "how much"
    is_analytical: bool = False  # "why", "analyze", "explain"
    
    # Confidence
    extraction_confidence: float = 0.0


QUERY_ANALYSIS_PROMPT = """
Analyze this search query and extract structured metadata for database filtering.

QUERY: "{query}"

CURRENT DATE: {current_date}

Extract the following (be precise, only extract what's clearly stated or strongly implied):

1. **Time References**: Any dates, quarters, years, relative time ("last month", "recent")
   - Convert relative times to date ranges based on current date
   
2. **Organizations**: Company names, institutions, departments mentioned

3. **People**: Names of individuals mentioned

4. **Locations**: Geographic references (countries, regions, cities)

5. **Topics**: Key themes/subjects (e.g., "revenue", "compliance", "architecture")
   - Include synonyms and related terms

6. **Document Type Hints**: What kind of document would answer this?
   - Options: financial_report, legal_contract, technical_doc, correspondence, 
     presentation, policy, research, meeting_notes, other

7. **Query Characteristics**:
   - is_comparison: Does it compare multiple things?
   - is_temporal: Does it ask about changes over time?
   - is_factual: Does it ask for specific facts/numbers?
   - is_analytical: Does it ask for analysis/explanation?

8. **Transformed Query**: Rewrite the query to be more search-friendly
   - Expand abbreviations
   - Add synonyms in parentheses
   - Remove filler words

OUTPUT AS JSON:
{{
    "original_query": "...",
    "transformed_query": "...",
    "time_references": [...],
    "date_from": "YYYY-MM-DD" or null,
    "date_to": "YYYY-MM-DD" or null,
    "organizations": [...],
    "people": [...],
    "locations": [...],
    "topics": [...],
    "likely_document_types": [...],
    "is_comparison": bool,
    "is_temporal": bool,
    "is_factual": bool,
    "is_analytical": bool,
    "extraction_confidence": 0.0-1.0
}}
"""


class QueryAnalyzer:
    """Analyze queries to extract structured filters."""
    
    def __init__(self):
        self.gemini = get_gemini_client()
    
    async def analyze(self, query: str) -> QueryAnalysis:
        """
        Analyze query and extract structured metadata.
        Uses Gemini with minimal thinking for speed.
        """
        from datetime import datetime
        
        prompt = QUERY_ANALYSIS_PROMPT.format(
            query=query,
            current_date=datetime.now().strftime("%Y-%m-%d")
        )
        
        response = await self.gemini.client.aio.models.generate_content(
            model=self.gemini.model,
            contents=[{"text": prompt}],
            config={
                "thinking_config": {"thinking_level": "minimal"},  # Fast
                "response_mime_type": "application/json"
            }
        )
        
        result = self.gemini._parse_json_response(response.text)
        result["original_query"] = query
        
        return QueryAnalysis(**result)


def get_query_analyzer() -> QueryAnalyzer:
    return QueryAnalyzer()
```

#### 3. Pre-Filter Service

```python
# backend/app/core/prefilter.py

"""
Database pre-filtering based on query analysis.
Reduces candidate set before document map consultation.
"""

from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import array

from app.db.models import Document
from app.core.query_analyzer import QueryAnalysis


class PreFilterService:
    """Pre-filter documents using PostgreSQL metadata queries."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def filter_candidates(
        self,
        analysis: QueryAnalysis,
        workspace_id: str = "default",
        max_candidates: int = 50
    ) -> list[str]:
        """
        Return candidate document IDs based on query analysis.
        Uses metadata filtering — no embeddings, no LLM calls.
        """
        conditions = [Document.workspace_id == workspace_id]
        
        # Document type filter
        if analysis.likely_document_types:
            conditions.append(
                Document.document_type.in_(analysis.likely_document_types)
            )
        
        # Topic filter (array overlap)
        if analysis.topics:
            # Match if document has ANY of the query topics
            conditions.append(
                Document.topics.overlap(analysis.topics)
            )
        
        # Organization filter
        if analysis.organizations:
            conditions.append(
                Document.entities_orgs.overlap(analysis.organizations)
            )
        
        # People filter
        if analysis.people:
            conditions.append(
                Document.entities_people.overlap(analysis.people)
            )
        
        # Date range filter
        if analysis.date_from and analysis.date_to:
            conditions.append(
                or_(
                    # Document's date range overlaps query range
                    and_(
                        Document.date_range_start <= analysis.date_to,
                        Document.date_range_end >= analysis.date_from
                    ),
                    # Or primary date is within range
                    and_(
                        Document.primary_date >= analysis.date_from,
                        Document.primary_date <= analysis.date_to
                    )
                )
            )
        elif analysis.date_from:
            conditions.append(
                or_(
                    Document.date_range_end >= analysis.date_from,
                    Document.primary_date >= analysis.date_from
                )
            )
        elif analysis.date_to:
            conditions.append(
                or_(
                    Document.date_range_start <= analysis.date_to,
                    Document.primary_date <= analysis.date_to
                )
            )
        
        # Filename search (fallback for time references like "Q3")
        if analysis.time_references:
            filename_conditions = [
                Document.filename.ilike(f"%{ref}%")
                for ref in analysis.time_references
            ]
            if filename_conditions:
                conditions.append(or_(*filename_conditions))
        
        # Build query with relevance scoring
        # Score based on how many filters match
        query = (
            select(Document.id)
            .where(and_(*conditions))
            .limit(max_candidates)
        )
        
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]
    
    async def get_filtered_map(
        self,
        candidate_ids: list[str],
        full_map: dict
    ) -> dict:
        """
        Return a filtered document map containing only candidate documents.
        """
        if not candidate_ids:
            return full_map  # Fall back to full map
        
        candidate_set = set(candidate_ids)
        
        filtered_map = {
            "corpus_id": full_map.get("corpus_id"),
            "corpus_summary": full_map.get("corpus_summary"),
            "documents": [
                doc for doc in full_map.get("documents", [])
                if doc["id"] in candidate_set
            ],
            "cross_references": full_map.get("cross_references", {})
        }
        
        return filtered_map


def get_prefilter_service(db: AsyncSession) -> PreFilterService:
    return PreFilterService(db)
```

#### 4. Updated Retriever with Pre-Filtering

```python
# backend/app/core/retriever.py — Enhanced

async def retrieve(
    self,
    query: str,
    workspace_id: str = "default",
    max_documents: int = 5,
    use_prefilter: bool = True  # NEW: Toggle pre-filtering
) -> list[dict]:
    """
    Retrieve relevant documents/chunks for query.
    
    Enhanced flow:
    1. Analyze query for structured filters
    2. Pre-filter candidates via PostgreSQL
    3. Consult filtered document map
    4. Fetch selected documents/chunks
    """
    from app.core.query_analyzer import get_query_analyzer
    from app.core.prefilter import get_prefilter_service
    
    # Get full document map
    document_map = await self.map_manager.get_map(workspace_id)
    
    if not document_map["documents"]:
        return []
    
    # NEW: Pre-filtering stage
    if use_prefilter and len(document_map["documents"]) > 10:
        # Analyze query
        analyzer = get_query_analyzer()
        analysis = await analyzer.analyze(query)
        
        # Get candidates from database
        prefilter = get_prefilter_service(self.db)
        candidate_ids = await prefilter.filter_candidates(
            analysis=analysis,
            workspace_id=workspace_id,
            max_candidates=50
        )
        
        if candidate_ids:
            # Use filtered map for consultation
            document_map = await prefilter.get_filtered_map(
                candidate_ids, document_map
            )
    
    # Consult map for final selection (existing logic)
    retrieval_decision = await self.gemini.consult_map_for_retrieval(
        query, document_map
    )
    
    doc_ids_to_retrieve = retrieval_decision.get("retrieve", [])[:max_documents]
    
    # ... rest of existing retrieval logic
```

---

## Part 12: Enhanced Document Map Extraction Prompts

### Revised Document Map Schema

```python
# Improved schema with more structured fields for better extraction

DOCUMENT_MAP_ENTRY_SCHEMA = {
    "id": "string - unique document identifier",
    "filename": "string - original filename",
    "document_type": "enum - financial_report|legal_contract|technical_doc|correspondence|presentation|policy|research|meeting_notes|other",
    "size_class": "enum - small|large",
    
    "essence": {
        "summary": "string - 2-3 sentence core summary",
        "purpose": "string - why this document exists (inform, decide, record, etc.)",
        "key_conclusion": "string - the main takeaway or finding, if any"
    },
    
    "temporal": {
        "document_date": "date - when document was created/published",
        "period_covered": {
            "start": "date or null",
            "end": "date or null"
        },
        "temporal_markers": ["Q3 2025", "FY2024", etc.]
    },
    
    "entities": {
        "organizations": [
            {"name": "string", "role": "subject|mentioned|author|partner|competitor"}
        ],
        "people": [
            {"name": "string", "role": "string", "title": "string or null"}
        ],
        "products": ["string"],
        "locations": ["string"],
        "metrics": [
            {"name": "string", "value": "string", "context": "string"}
        ]
    },
    
    "topics": {
        "primary": ["string - main topics, max 5"],
        "secondary": ["string - related topics"],
        "keywords": ["string - specific terms for search"]
    },
    
    "structure": {
        "sections": ["string - main section headings"],
        "has_tables": "boolean",
        "has_charts": "boolean",
        "has_appendices": "boolean"
    },
    
    "retrieval_profile": {
        "answers_questions_about": ["string - what queries should retrieve this"],
        "use_when": "string - scenario description",
        "do_not_use_for": "string - explicit exclusions",
        "confidence_level": "high|medium|low - reliability of information"
    },
    
    "relationships": [
        {
            "target_doc_id": "string",
            "relation_type": "supersedes|superseded_by|references|referenced_by|related|contradicts|supports",
            "description": "string"
        }
    ],
    
    "chunks": [
        {
            "chunk_id": "string",
            "section": "string",
            "topic": "string",
            "retrieval_hint": "string"
        }
    ]
}
```

### Enhanced Extraction Prompt

```python
# backend/app/core/extraction_prompts.py

DOCUMENT_INTELLIGENCE_EXTRACTION_PROMPT = """
You are a document intelligence specialist. Analyze this document and extract structured metadata for a retrieval system.

DOCUMENT FILENAME: {filename}
DOCUMENT CONTENT:
---
{content}
---

EXTRACTION INSTRUCTIONS:

## 1. ESSENCE (Be precise and specific)
- **Summary**: Write exactly 2-3 sentences capturing WHAT this document contains. Be specific — mention actual numbers, names, and conclusions. Avoid vague descriptions.
  - BAD: "This document discusses financial performance."
  - GOOD: "Q3 2025 earnings report for Acme Corp showing $4.2B revenue (+12% YoY). APAC region drove growth while semiconductor supply issues impacted margins."

- **Purpose**: Why does this document exist? (to inform, to record a decision, to propose, to analyze, to comply, etc.)

- **Key Conclusion**: What is the single most important takeaway? If no clear conclusion, state "Informational document — no single conclusion."

## 2. TEMPORAL INFORMATION
- **Document Date**: When was this created? Look for dates in headers, footers, or content.
- **Period Covered**: What time period does this document describe? (e.g., "Q3 2025" → start: 2025-07-01, end: 2025-09-30)
- **Temporal Markers**: List all time references (quarters, years, "last month", specific dates)

## 3. ENTITIES (Be exhaustive but relevant)
- **Organizations**: 
  - List ALL companies, institutions, departments mentioned
  - Specify role: subject (doc is about them), author (they wrote it), mentioned (referenced), partner, competitor
  
- **People**:
  - List key individuals with their roles/titles if mentioned
  - Prioritize decision-makers, authors, subjects
  
- **Metrics**:
  - Extract specific numbers with context
  - Example: {{"name": "Revenue", "value": "$4.2B", "context": "Q3 2025, +12% YoY"}}

## 4. TOPICS
- **Primary Topics** (max 5): The main subjects. Be specific.
  - BAD: ["business", "money", "performance"]
  - GOOD: ["quarterly earnings", "APAC expansion", "semiconductor supply chain"]
  
- **Secondary Topics**: Related but not central topics

- **Keywords**: Specific terms someone might search for. Include:
  - Technical terms
  - Acronyms
  - Product names
  - Industry jargon

## 5. STRUCTURE
- List main section headings (helps with chunk navigation)
- Note if document contains tables, charts, appendices

## 6. RETRIEVAL PROFILE (Critical for search quality)
- **Answers Questions About**: List 5-10 specific questions this document can answer
  - Example: "What was Acme Corp's Q3 2025 revenue?"
  - Example: "How did APAC region perform in Q3?"
  
- **Use When**: Describe the scenario when this doc should be retrieved
  - Example: "User asks about Acme Corp financial performance in 2025"
  
- **Do Not Use For**: Explicit exclusions to avoid false matches
  - Example: "Not for Q2 or earlier periods. Not for competitor analysis."

- **Confidence Level**: 
  - HIGH: Official document, verified data, authoritative source
  - MEDIUM: Internal analysis, estimates, projections
  - LOW: Draft, unverified, speculative

## 7. RELATIONSHIPS (If inferable)
- Does this document reference other documents?
- Does it supersede a previous version?
- Is it related to a known project/initiative?

OUTPUT FORMAT (JSON):
{{
    "essence": {{
        "summary": "...",
        "purpose": "...",
        "key_conclusion": "..."
    }},
    "temporal": {{
        "document_date": "YYYY-MM-DD or null",
        "period_covered": {{
            "start": "YYYY-MM-DD or null",
            "end": "YYYY-MM-DD or null"
        }},
        "temporal_markers": [...]
    }},
    "entities": {{
        "organizations": [
            {{"name": "...", "role": "subject|mentioned|author|partner|competitor"}}
        ],
        "people": [
            {{"name": "...", "role": "...", "title": "..."}}
        ],
        "products": [...],
        "locations": [...],
        "metrics": [
            {{"name": "...", "value": "...", "context": "..."}}
        ]
    }},
    "topics": {{
        "primary": [...],
        "secondary": [...],
        "keywords": [...]
    }},
    "structure": {{
        "sections": [...],
        "has_tables": bool,
        "has_charts": bool,
        "has_appendices": bool
    }},
    "retrieval_profile": {{
        "answers_questions_about": [...],
        "use_when": "...",
        "do_not_use_for": "...",
        "confidence_level": "high|medium|low"
    }},
    "document_type": "financial_report|legal_contract|technical_doc|correspondence|presentation|policy|research|meeting_notes|other"
}}

IMPORTANT:
- Be SPECIFIC, not generic. Generic extractions are useless for retrieval.
- Include ACTUAL values, names, and numbers from the document.
- The "retrieval_profile" is the most important section — think carefully about what queries should find this document.
- If uncertain about a field, provide your best inference with reduced confidence, don't leave empty.
"""


CHUNK_CONTEXT_PROMPT = """
You are creating contextual metadata for a document chunk to aid retrieval.

PARENT DOCUMENT: {filename}
PARENT SUMMARY: {parent_summary}

THIS CHUNK (Section {chunk_position}):
---
{chunk_content}
---

PREVIOUS SECTION: {previous_section}
NEXT SECTION: {next_section}

Create retrieval metadata for this specific chunk:

1. **Section Topic**: What specific topic does THIS section cover?

2. **Key Information**: What unique information is ONLY in this chunk?
   - Specific numbers, decisions, names not in other sections

3. **Retrieval Hint**: When should a query retrieve THIS chunk specifically?
   - Be precise: "Retrieve for questions about Q3 APAC revenue breakdown by country"
   - Not: "Retrieve for financial questions"

4. **Contextual Note**: One sentence placing this chunk in document context
   - Example: "This section provides detailed APAC analysis following the executive summary of global results."

OUTPUT (JSON):
{{
    "section_topic": "...",
    "key_information": [...],
    "retrieval_hint": "...",
    "contextual_note": "..."
}}
"""
```

### Updated Gemini Client with New Prompts

```python
# backend/app/core/gemini_client.py — Updated method

async def extract_document_intelligence(
    self,
    content: str,
    filename: str
) -> dict:
    """
    Extract comprehensive intelligence from document for the document map.
    Uses enhanced prompt for higher quality extraction.
    """
    from app.core.extraction_prompts import DOCUMENT_INTELLIGENCE_EXTRACTION_PROMPT
    
    # Truncate content intelligently — keep beginning and end
    max_content_tokens = 80000
    if len(content) > max_content_tokens * 4:  # Rough char estimate
        # Keep first 60% and last 20% for better coverage
        split_point = int(max_content_tokens * 4 * 0.6)
        end_portion = int(max_content_tokens * 4 * 0.2)
        content_truncated = (
            content[:split_point] + 
            "\n\n[... CONTENT TRUNCATED FOR PROCESSING ...]\n\n" +
            content[-end_portion:]
        )
    else:
        content_truncated = content
    
    prompt = DOCUMENT_INTELLIGENCE_EXTRACTION_PROMPT.format(
        filename=filename,
        content=content_truncated
    )
    
    response = await self.client.aio.models.generate_content(
        model=self.model,
        contents=[{"text": prompt}],
        config={
            "thinking_config": {"thinking_level": "high"},  # Use deep thinking for quality
            "response_mime_type": "application/json"
        }
    )
    
    return self._parse_json_response(response.text)
```

---

## Part 13: Alternative Architecture — Agentic SQL RAG with LangChain

### Concept

Replace the document map + vector approach with a fully structured data extraction system. Documents are parsed into SQL tables, and an LLM agent iteratively queries the database using SQL tools until it has sufficient information to answer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AGENTIC SQL RAG ARCHITECTURE                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  User Question  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      GEMINI 3 FLASH (THINKING MODE)                     │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  AGENT REASONING LOOP                                            │   │
│  │                                                                   │   │
│  │  1. Analyze question → determine information needs               │   │
│  │  2. Plan SQL queries → what tables/columns needed                │   │
│  │  3. Execute query via SQL tool → get results                     │   │
│  │  4. Evaluate results → sufficient? need more?                    │   │
│  │  5. If insufficient → refine query, explore related tables       │   │
│  │  6. Synthesize final answer from accumulated data                │   │
│  │                                                                   │   │
│  │  [All reasoning happens within single Gemini call with thinking] │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  SQL TOOL                                                        │   │
│  │  - Execute SELECT queries                                        │   │
│  │  - Read-only access                                              │   │
│  │  - Return results as JSON                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        POSTGRESQL DATABASE                              │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  documents  │  │   claims    │  │   metrics   │  │  entities   │   │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤   │
│  │ id          │  │ id          │  │ id          │  │ id          │   │
│  │ filename    │  │ document_id │  │ document_id │  │ document_id │   │
│  │ doc_type    │  │ claim_text  │  │ metric_name │  │ entity_name │   │
│  │ summary     │  │ confidence  │  │ value       │  │ entity_type │   │
│  │ created_at  │  │ source_sect │  │ unit        │  │ role        │   │
│  └─────────────┘  │ topic       │  │ period      │  │ context     │   │
│                   └─────────────┘  │ context     │  └─────────────┘   │
│                                    └─────────────┘                     │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────┐│
│  │   topics    │  │relationships│  │         document_chunks         ││
│  ├─────────────┤  ├─────────────┤  ├─────────────────────────────────┤│
│  │ id          │  │ source_doc  │  │ id                              ││
│  │ document_id │  │ target_doc  │  │ document_id                     ││
│  │ topic_name  │  │ rel_type    │  │ chunk_text (for fallback)       ││
│  │ is_primary  │  │ description │  │ section                         ││
│  └─────────────┘  └─────────────┘  └─────────────────────────────────┘│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Project Structure Extension

```
intelligent-rag/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── ...
│   │   │   ├── agentic_sql/              # NEW: Agentic SQL RAG module
│   │   │   │   ├── __init__.py
│   │   │   │   ├── extractor.py          # Document → SQL extraction
│   │   │   │   ├── agent.py              # LangChain agent setup
│   │   │   │   ├── sql_tool.py           # SQL execution tool
│   │   │   │   ├── prompts.py            # Agent prompts
│   │   │   │   └── schemas.py            # SQL table schemas
│   │   │   │
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── ...
│   │   │   │   └── agentic_chat.py       # NEW: Agentic RAG endpoints
```

### Requirements Addition

```
# backend/requirements.txt — additions

# LangChain
langchain==0.3.14
langchain-google-genai==2.0.8
langchain-community==0.3.14

# SQL utilities
sqlparse==0.5.3
```

### Implementation

#### 1. SQL Table Schemas

```python
# backend/app/core/agentic_sql/schemas.py

"""
SQL schemas for structured document data.
Documents are decomposed into normalized tables for precise querying.
"""

from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Float, 
    ForeignKey, Boolean, Date, Enum, Index
)
from sqlalchemy.orm import relationship
from app.db.models import Base
import enum


class ConfidenceLevel(enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EntityType(enum.Enum):
    ORGANIZATION = "organization"
    PERSON = "person"
    PRODUCT = "product"
    LOCATION = "location"
    EVENT = "event"


class RelationType(enum.Enum):
    SUPERSEDES = "supersedes"
    REFERENCES = "references"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    RELATED = "related"


# Core document table (simplified from main schema)
class SQLDocument(Base):
    __tablename__ = "sql_documents"
    
    id = Column(String(50), primary_key=True)
    workspace_id = Column(String(50), index=True)
    filename = Column(String(255))
    document_type = Column(String(50))
    summary = Column(Text)
    purpose = Column(String(255))
    key_conclusion = Column(Text)
    document_date = Column(Date)
    period_start = Column(Date)
    period_end = Column(Date)
    confidence_level = Column(String(20))
    token_count = Column(Integer)
    created_at = Column(DateTime)


class SQLClaim(Base):
    """Factual claims extracted from documents."""
    __tablename__ = "sql_claims"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), ForeignKey("sql_documents.id"), index=True)
    
    claim_text = Column(Text, nullable=False)  # The actual claim
    claim_type = Column(String(50))  # fact, opinion, prediction, recommendation
    topic = Column(String(100), index=True)
    
    confidence = Column(String(20))  # high, medium, low
    source_section = Column(String(255))  # Where in doc this came from
    
    # For verification
    is_quantitative = Column(Boolean, default=False)
    can_be_verified = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_claims_topic', topic),
        Index('idx_claims_document', document_id),
    )


class SQLMetric(Base):
    """Quantitative metrics extracted from documents."""
    __tablename__ = "sql_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), ForeignKey("sql_documents.id"), index=True)
    
    metric_name = Column(String(100), nullable=False, index=True)  # "Revenue", "Growth Rate"
    value = Column(String(100), nullable=False)  # "4.2B", "12%"
    numeric_value = Column(Float)  # 4200000000, 0.12 (parsed for comparison)
    unit = Column(String(50))  # "USD", "percent", "units"
    
    period = Column(String(50))  # "Q3 2025", "FY2024"
    period_start = Column(Date)
    period_end = Column(Date)
    
    context = Column(Text)  # Additional context
    comparison_base = Column(String(100))  # "YoY", "QoQ", "vs budget"
    
    entity_name = Column(String(255))  # Who this metric is about
    category = Column(String(100), index=True)  # "financial", "operational", "growth"
    
    __table_args__ = (
        Index('idx_metrics_name', metric_name),
        Index('idx_metrics_period', period_start, period_end),
        Index('idx_metrics_entity', entity_name),
    )


class SQLEntity(Base):
    """Named entities extracted from documents."""
    __tablename__ = "sql_entities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), ForeignKey("sql_documents.id"), index=True)
    
    entity_name = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), index=True)  # organization, person, product, location
    role = Column(String(50))  # subject, author, mentioned, competitor
    
    title = Column(String(255))  # For people
    context = Column(Text)  # Additional context about entity in this doc
    
    __table_args__ = (
        Index('idx_entities_name_type', entity_name, entity_type),
    )


class SQLTopic(Base):
    """Topics associated with documents."""
    __tablename__ = "sql_topics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), ForeignKey("sql_documents.id"), index=True)
    
    topic_name = Column(String(100), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    
    __table_args__ = (
        Index('idx_topics_name', topic_name),
    )


class SQLRelationship(Base):
    """Relationships between documents."""
    __tablename__ = "sql_relationships"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_document_id = Column(String(50), ForeignKey("sql_documents.id"), index=True)
    target_document_id = Column(String(50), ForeignKey("sql_documents.id"), index=True)
    
    relationship_type = Column(String(50))  # supersedes, references, supports, contradicts
    description = Column(Text)


class SQLDocumentChunk(Base):
    """Full text chunks for fallback retrieval."""
    __tablename__ = "sql_document_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(50), ForeignKey("sql_documents.id"), index=True)
    
    chunk_index = Column(Integer)
    section_name = Column(String(255))
    chunk_text = Column(Text, nullable=False)
    token_count = Column(Integer)


# Schema description for LLM
SQL_SCHEMA_DESCRIPTION = """
DATABASE SCHEMA:

## sql_documents
Main document metadata table.
Columns:
- id: Unique document identifier
- workspace_id: Workspace for multi-tenancy
- filename: Original filename
- document_type: Type (financial_report, legal_contract, technical_doc, etc.)
- summary: 2-3 sentence summary
- purpose: Why document exists
- key_conclusion: Main takeaway
- document_date: When created
- period_start, period_end: Time period covered
- confidence_level: Data reliability (high/medium/low)

## sql_claims
Factual claims extracted from documents.
Columns:
- id, document_id: Identifiers
- claim_text: The actual claim statement
- claim_type: fact, opinion, prediction, recommendation
- topic: Topic category
- confidence: Claim reliability
- source_section: Section of document
- is_quantitative: If claim involves numbers
- can_be_verified: If claim is verifiable

## sql_metrics
Quantitative metrics extracted from documents.
Columns:
- id, document_id: Identifiers  
- metric_name: Name (Revenue, Growth Rate, Headcount, etc.)
- value: String value ($4.2B, 12%)
- numeric_value: Parsed float for comparison
- unit: Unit of measurement
- period: Time period string (Q3 2025)
- period_start, period_end: Date range
- context: Additional context
- comparison_base: Comparison type (YoY, QoQ)
- entity_name: Who metric is about
- category: Metric category (financial, operational)

## sql_entities
Named entities extracted from documents.
Columns:
- id, document_id: Identifiers
- entity_name: Name of entity
- entity_type: organization, person, product, location
- role: subject, author, mentioned, competitor
- title: Title (for people)
- context: Context in document

## sql_topics
Topics associated with documents.
Columns:
- id, document_id: Identifiers
- topic_name: Topic name
- is_primary: If primary topic (vs secondary)

## sql_relationships  
Relationships between documents.
Columns:
- id: Identifier
- source_document_id, target_document_id: Related documents
- relationship_type: supersedes, references, supports, contradicts
- description: Relationship description

## sql_document_chunks
Full text chunks for fallback.
Columns:
- id, document_id: Identifiers
- chunk_index: Order in document
- section_name: Section heading
- chunk_text: Full text
- token_count: Size

COMMON QUERY PATTERNS:
- Join metrics with documents for context
- Filter by period_start/period_end for time ranges
- Use entity_name to find all info about specific company/person
- Use topics to find related documents
- Check confidence_level for reliability filtering
"""
```

#### 2. Document to SQL Extractor

```python
# backend/app/core/agentic_sql/extractor.py

"""
Extract structured data from documents and populate SQL tables.
Uses Gemini 3 Flash to decompose documents into relational data.
"""

from datetime import datetime, date
from typing import Optional
import re
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gemini_client import get_gemini_client
from app.core.agentic_sql.schemas import (
    SQLDocument, SQLClaim, SQLMetric, SQLEntity, SQLTopic, 
    SQLRelationship, SQLDocumentChunk
)


STRUCTURED_EXTRACTION_PROMPT = """
You are a data extraction specialist. Extract structured information from this document 
for storage in a relational database.

DOCUMENT: {filename}
CONTENT:
---
{content}
---

Extract the following as JSON:

## 1. DOCUMENT METADATA
{{
    "document_type": "financial_report|legal_contract|technical_doc|correspondence|presentation|policy|research|meeting_notes|other",
    "summary": "2-3 sentence summary",
    "purpose": "Why this document exists",
    "key_conclusion": "Main takeaway",
    "document_date": "YYYY-MM-DD or null",
    "period_start": "YYYY-MM-DD or null",
    "period_end": "YYYY-MM-DD or null",
    "confidence_level": "high|medium|low"
}}

## 2. CLAIMS
Extract factual statements, opinions, predictions, and recommendations.
[
    {{
        "claim_text": "The exact claim",
        "claim_type": "fact|opinion|prediction|recommendation",
        "topic": "Topic category",
        "confidence": "high|medium|low",
        "source_section": "Section name or heading",
        "is_quantitative": true/false,
        "can_be_verified": true/false
    }}
]
- Extract 10-30 key claims depending on document length
- Be precise — include specific details from the claim
- Focus on important/actionable claims

## 3. METRICS
Extract all quantitative data points.
[
    {{
        "metric_name": "Revenue|Growth Rate|Headcount|etc",
        "value": "The value as written ($4.2B, 12%, etc)",
        "numeric_value": 4200000000 (parsed float, null if unparseable),
        "unit": "USD|percent|units|etc",
        "period": "Q3 2025|FY2024|etc",
        "period_start": "YYYY-MM-DD or null",
        "period_end": "YYYY-MM-DD or null",
        "context": "Additional context",
        "comparison_base": "YoY|QoQ|vs budget|absolute|null",
        "entity_name": "Who this metric is about",
        "category": "financial|operational|growth|headcount|performance|other"
    }}
]
- Extract ALL numeric data points
- Parse numeric values for comparison (convert "4.2B" to 4200000000)
- Infer period dates from context

## 4. ENTITIES
Extract all named entities.
[
    {{
        "entity_name": "Name",
        "entity_type": "organization|person|product|location",
        "role": "subject|author|mentioned|competitor|partner",
        "title": "Title for people or null",
        "context": "Why entity is mentioned"
    }}
]

## 5. TOPICS
[
    {{"topic_name": "...", "is_primary": true/false}}
]
- 3-5 primary topics, 5-10 secondary topics
- Be specific (not "business" but "quarterly earnings analysis")

OUTPUT FORMAT:
{{
    "metadata": {{...}},
    "claims": [...],
    "metrics": [...],
    "entities": [...],
    "topics": [...]
}}
"""


class StructuredExtractor:
    """Extract structured data from documents for SQL storage."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.gemini = get_gemini_client()
    
    async def extract_and_store(
        self,
        document_id: str,
        workspace_id: str,
        filename: str,
        content: str,
        chunks: Optional[list[dict]] = None
    ) -> dict:
        """
        Extract structured data and store in SQL tables.
        
        Returns extraction statistics.
        """
        # Extract structured data via Gemini
        extraction = await self._extract_structured_data(filename, content)
        
        # Store document metadata
        await self._store_document(
            document_id, workspace_id, filename, 
            extraction["metadata"], len(content) // 4
        )
        
        # Store claims
        claims_count = await self._store_claims(
            document_id, extraction.get("claims", [])
        )
        
        # Store metrics
        metrics_count = await self._store_metrics(
            document_id, extraction.get("metrics", [])
        )
        
        # Store entities
        entities_count = await self._store_entities(
            document_id, extraction.get("entities", [])
        )
        
        # Store topics
        topics_count = await self._store_topics(
            document_id, extraction.get("topics", [])
        )
        
        # Store chunks for fallback
        if chunks:
            await self._store_chunks(document_id, chunks)
        
        await self.db.commit()
        
        return {
            "document_id": document_id,
            "claims_extracted": claims_count,
            "metrics_extracted": metrics_count,
            "entities_extracted": entities_count,
            "topics_extracted": topics_count
        }
    
    async def _extract_structured_data(self, filename: str, content: str) -> dict:
        """Use Gemini to extract structured data."""
        # Truncate for context limits
        max_chars = 300000
        if len(content) > max_chars:
            content = content[:int(max_chars * 0.7)] + "\n...\n" + content[-int(max_chars * 0.2):]
        
        prompt = STRUCTURED_EXTRACTION_PROMPT.format(
            filename=filename,
            content=content
        )
        
        response = await self.gemini.client.aio.models.generate_content(
            model=self.gemini.model,
            contents=[{"text": prompt}],
            config={
                "thinking_config": {"thinking_level": "high"},
                "response_mime_type": "application/json"
            }
        )
        
        return self.gemini._parse_json_response(response.text)
    
    async def _store_document(
        self, doc_id: str, workspace_id: str, 
        filename: str, metadata: dict, token_count: int
    ):
        """Store document metadata."""
        doc = SQLDocument(
            id=doc_id,
            workspace_id=workspace_id,
            filename=filename,
            document_type=metadata.get("document_type", "other"),
            summary=metadata.get("summary", ""),
            purpose=metadata.get("purpose", ""),
            key_conclusion=metadata.get("key_conclusion", ""),
            document_date=self._parse_date(metadata.get("document_date")),
            period_start=self._parse_date(metadata.get("period_start")),
            period_end=self._parse_date(metadata.get("period_end")),
            confidence_level=metadata.get("confidence_level", "medium"),
            token_count=token_count,
            created_at=datetime.utcnow()
        )
        self.db.add(doc)
    
    async def _store_claims(self, doc_id: str, claims: list) -> int:
        """Store extracted claims."""
        for claim_data in claims:
            claim = SQLClaim(
                document_id=doc_id,
                claim_text=claim_data.get("claim_text", ""),
                claim_type=claim_data.get("claim_type", "fact"),
                topic=claim_data.get("topic", ""),
                confidence=claim_data.get("confidence", "medium"),
                source_section=claim_data.get("source_section", ""),
                is_quantitative=claim_data.get("is_quantitative", False),
                can_be_verified=claim_data.get("can_be_verified", True)
            )
            self.db.add(claim)
        return len(claims)
    
    async def _store_metrics(self, doc_id: str, metrics: list) -> int:
        """Store extracted metrics."""
        for metric_data in metrics:
            metric = SQLMetric(
                document_id=doc_id,
                metric_name=metric_data.get("metric_name", ""),
                value=metric_data.get("value", ""),
                numeric_value=metric_data.get("numeric_value"),
                unit=metric_data.get("unit", ""),
                period=metric_data.get("period", ""),
                period_start=self._parse_date(metric_data.get("period_start")),
                period_end=self._parse_date(metric_data.get("period_end")),
                context=metric_data.get("context", ""),
                comparison_base=metric_data.get("comparison_base"),
                entity_name=metric_data.get("entity_name", ""),
                category=metric_data.get("category", "other")
            )
            self.db.add(metric)
        return len(metrics)
    
    async def _store_entities(self, doc_id: str, entities: list) -> int:
        """Store extracted entities."""
        for entity_data in entities:
            entity = SQLEntity(
                document_id=doc_id,
                entity_name=entity_data.get("entity_name", ""),
                entity_type=entity_data.get("entity_type", "organization"),
                role=entity_data.get("role", "mentioned"),
                title=entity_data.get("title"),
                context=entity_data.get("context", "")
            )
            self.db.add(entity)
        return len(entities)
    
    async def _store_topics(self, doc_id: str, topics: list) -> int:
        """Store document topics."""
        for topic_data in topics:
            topic = SQLTopic(
                document_id=doc_id,
                topic_name=topic_data.get("topic_name", ""),
                is_primary=topic_data.get("is_primary", False)
            )
            self.db.add(topic)
        return len(topics)
    
    async def _store_chunks(self, doc_id: str, chunks: list):
        """Store text chunks for fallback."""
        for i, chunk in enumerate(chunks):
            db_chunk = SQLDocumentChunk(
                document_id=doc_id,
                chunk_index=i,
                section_name=chunk.get("section", ""),
                chunk_text=chunk.get("content", ""),
                token_count=chunk.get("token_count", 0)
            )
            self.db.add(db_chunk)
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
```

#### 3. SQL Execution Tool

```python
# backend/app/core/agentic_sql/sql_tool.py

"""
SQL execution tool for LangChain agent.
Provides read-only access to the structured document database.
"""

from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json


class SQLQueryInput(BaseModel):
    """Input for SQL query tool."""
    query: str = Field(
        description="The SQL SELECT query to execute. Must be read-only (SELECT only)."
    )
    explanation: str = Field(
        description="Brief explanation of why you're running this query and what you expect to find."
    )


class SQLQueryTool(BaseTool):
    """Tool for executing SQL queries against document database."""
    
    name: str = "sql_query"
    description: str = """
    Execute a SQL SELECT query against the document database.
    Use this to retrieve specific information from extracted document data.
    
    Available tables:
    - sql_documents: Document metadata (id, filename, summary, document_date, etc.)
    - sql_claims: Factual claims (claim_text, claim_type, topic, confidence)
    - sql_metrics: Quantitative data (metric_name, value, numeric_value, period, entity_name)
    - sql_entities: Named entities (entity_name, entity_type, role)
    - sql_topics: Document topics (topic_name, is_primary)
    - sql_document_chunks: Full text chunks (chunk_text, section_name)
    
    IMPORTANT:
    - Only SELECT queries allowed
    - Always include LIMIT clause (max 50)
    - Use JOINs to connect data across tables
    - Filter by workspace_id when relevant
    """
    args_schema: Type[BaseModel] = SQLQueryInput
    
    db: AsyncSession = None
    workspace_id: str = "default"
    
    def __init__(self, db: AsyncSession, workspace_id: str = "default"):
        super().__init__()
        self.db = db
        self.workspace_id = workspace_id
    
    async def _arun(self, query: str, explanation: str) -> str:
        """Execute query asynchronously."""
        # Validate query is SELECT only
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            return json.dumps({
                "error": "Only SELECT queries are allowed",
                "hint": "Rewrite your query as a SELECT statement"
            })
        
        # Check for dangerous keywords
        dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"]
        for keyword in dangerous:
            if keyword in query_upper:
                return json.dumps({
                    "error": f"Query contains forbidden keyword: {keyword}",
                    "hint": "Only read operations are permitted"
                })
        
        # Ensure LIMIT clause
        if "LIMIT" not in query_upper:
            query = query.rstrip(";") + " LIMIT 50"
        
        try:
            result = await self.db.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()
            
            # Convert to list of dicts
            data = [dict(zip(columns, row)) for row in rows]
            
            # Handle date serialization
            for row in data:
                for key, value in row.items():
                    if hasattr(value, 'isoformat'):
                        row[key] = value.isoformat()
            
            return json.dumps({
                "success": True,
                "row_count": len(data),
                "columns": list(columns),
                "data": data,
                "query_explanation": explanation
            }, indent=2, default=str)
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "hint": "Check your SQL syntax and table/column names",
                "query_attempted": query
            })
    
    def _run(self, query: str, explanation: str) -> str:
        """Sync wrapper — use _arun for async."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._arun(query, explanation)
        )
```

#### 4. Agentic SQL RAG Agent

```python
# backend/app/core/agentic_sql/agent.py

"""
LangChain agent for Agentic SQL RAG.
Uses Gemini 3 Flash thinking capabilities for iterative query planning and execution.
"""

from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import AgentExecutor, create_tool_calling_agent
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.agentic_sql.sql_tool import SQLQueryTool
from app.core.agentic_sql.schemas import SQL_SCHEMA_DESCRIPTION


AGENT_SYSTEM_PROMPT = """You are an intelligent document analyst with access to a SQL database containing structured information extracted from documents.

{schema_description}

YOUR TASK:
Answer the user's question by querying the database. You have a sql_query tool to execute SELECT queries.

APPROACH:
1. **Understand the Question**: What information is needed? What tables are relevant?

2. **Plan Your Queries**: Think about which tables to query and how to join them.
   - Start with broad queries to understand what data exists
   - Then narrow down to specific information needed

3. **Execute Iteratively**: 
   - Run a query
   - Evaluate results — do you have enough information?
   - If not, refine and run additional queries
   - Look for related data that might help

4. **Synthesize Answer**: Once you have sufficient data, compose a clear answer.
   - Cite specific data points from query results
   - Note any limitations or gaps in the data
   - Indicate confidence level

QUERY BEST PRACTICES:
- Always JOIN tables when you need data from multiple sources
- Use WHERE clauses to filter relevant data
- Include LIMIT to avoid huge result sets
- Query sql_claims for factual statements
- Query sql_metrics for numerical data
- Query sql_entities to find information about specific companies/people
- Use sql_document_chunks as fallback for full text search

EXAMPLE QUERIES:
```sql
-- Find revenue metrics for a company
SELECT m.metric_name, m.value, m.period, d.filename
FROM sql_metrics m
JOIN sql_documents d ON m.document_id = d.id
WHERE m.entity_name ILIKE '%Acme%'
  AND m.category = 'financial'
ORDER BY m.period_start DESC
LIMIT 20;

-- Find claims about a topic
SELECT c.claim_text, c.confidence, d.filename, d.document_date
FROM sql_claims c
JOIN sql_documents d ON c.document_id = d.id
WHERE c.topic ILIKE '%revenue%'
  AND c.confidence = 'high'
LIMIT 20;

-- Find all info about an entity
SELECT e.entity_name, e.entity_type, e.role, e.context, d.filename
FROM sql_entities e
JOIN sql_documents d ON e.document_id = d.id
WHERE e.entity_name ILIKE '%John Smith%'
LIMIT 20;
```

IMPORTANT:
- If initial queries return no results, try broader searches
- If you can't find information, say so clearly
- Always explain your reasoning
- Cite the source documents when providing answers

Current workspace: {workspace_id}
"""


class AgenticSQLAgent:
    """
    Agentic RAG using SQL queries and Gemini 3 Flash thinking.
    
    The agent iteratively:
    1. Analyzes the question
    2. Plans SQL queries
    3. Executes queries
    4. Evaluates results
    5. Refines or synthesizes answer
    
    All reasoning happens within Gemini's thinking mode.
    """
    
    def __init__(self, db: AsyncSession, workspace_id: str = "default"):
        self.db = db
        self.workspace_id = workspace_id
        self.settings = get_settings()
        
        # Initialize Gemini via LangChain
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            google_api_key=self.settings.gemini_api_key,
            temperature=0,
            # Enable thinking mode via model config
            model_kwargs={
                "thinking_config": {"thinking_level": "high"}
            }
        )
        
        # Create SQL tool
        self.sql_tool = SQLQueryTool(db=db, workspace_id=workspace_id)
        
        # Create agent
        self.agent = self._create_agent()
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with SQL tool."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", AGENT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create tool-calling agent
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=[self.sql_tool],
            prompt=prompt
        )
        
        # Wrap in executor with iteration limit
        executor = AgentExecutor(
            agent=agent,
            tools=[self.sql_tool],
            verbose=True,
            max_iterations=10,  # Limit query iterations
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )
        
        return executor
    
    async def query(
        self,
        question: str,
        chat_history: Optional[list[dict]] = None
    ) -> dict:
        """
        Answer a question using iterative SQL queries.
        
        Returns:
            {
                "answer": str,
                "queries_executed": list[str],
                "sources": list[str],
                "reasoning_steps": list[str]
            }
        """
        # Format chat history for LangChain
        history_messages = []
        if chat_history:
            for msg in chat_history[-5:]:  # Last 5 messages
                if msg["role"] == "user":
                    history_messages.append(HumanMessage(content=msg["content"]))
                else:
                    history_messages.append(AIMessage(content=msg["content"]))
        
        # Execute agent
        result = await self.agent.ainvoke({
            "input": question,
            "chat_history": history_messages,
            "schema_description": SQL_SCHEMA_DESCRIPTION,
            "workspace_id": self.workspace_id
        })
        
        # Extract information from result
        answer = result.get("output", "I couldn't find an answer.")
        
        # Parse intermediate steps for transparency
        queries_executed = []
        sources = set()
        reasoning_steps = []
        
        for step in result.get("intermediate_steps", []):
            action, observation = step
            
            if hasattr(action, 'tool_input'):
                tool_input = action.tool_input
                if isinstance(tool_input, dict):
                    queries_executed.append(tool_input.get("query", ""))
                    reasoning_steps.append(tool_input.get("explanation", ""))
            
            # Extract source documents from query results
            if isinstance(observation, str):
                try:
                    import json
                    obs_data = json.loads(observation)
                    for row in obs_data.get("data", []):
                        if "filename" in row:
                            sources.add(row["filename"])
                except:
                    pass
        
        return {
            "answer": answer,
            "queries_executed": queries_executed,
            "sources": list(sources),
            "reasoning_steps": reasoning_steps,
            "iterations": len(result.get("intermediate_steps", []))
        }


def get_agentic_sql_agent(db: AsyncSession, workspace_id: str = "default") -> AgenticSQLAgent:
    return AgenticSQLAgent(db, workspace_id)
```

#### 5. API Routes for Agentic RAG

```python
# backend/app/api/routes/agentic_chat.py

"""
API routes for Agentic SQL RAG.
Alternative to document-map-based RAG.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import uuid

from app.db.postgres import get_db
from app.db.models import ChatHistory
from app.core.agentic_sql.agent import get_agentic_sql_agent

router = APIRouter()


class AgenticQueryRequest(BaseModel):
    query: str
    workspace_id: str = "default"
    session_id: Optional[str] = None


class AgenticQueryResponse(BaseModel):
    answer: str
    queries_executed: list[str]
    sources: list[str]
    reasoning_steps: list[str]
    iterations: int
    session_id: str


@router.post("/query", response_model=AgenticQueryResponse)
async def agentic_query(
    request: AgenticQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Query documents using Agentic SQL RAG.
    
    The agent will:
    1. Analyze your question
    2. Plan and execute SQL queries iteratively
    3. Synthesize an answer from the results
    
    Returns the answer along with transparency into the queries executed.
    """
    from sqlalchemy import select
    
    # Get chat history if session provided
    chat_history = []
    if request.session_id:
        result = await db.execute(
            select(ChatHistory)
            .where(
                ChatHistory.session_id == request.session_id,
                ChatHistory.workspace_id == request.workspace_id
            )
            .order_by(ChatHistory.created_at.desc())
            .limit(10)
        )
        history_records = result.scalars().all()
        chat_history = [
            {"role": h.role, "content": h.content}
            for h in reversed(history_records)
        ]
    
    # Create agent and execute query
    agent = get_agentic_sql_agent(db, request.workspace_id)
    result = await agent.query(request.query, chat_history)
    
    # Generate session ID if not provided
    session_id = request.session_id or f"agentic_{uuid.uuid4().hex[:12]}"
    
    # Store chat history
    user_msg = ChatHistory(
        workspace_id=request.workspace_id,
        session_id=session_id,
        role="user",
        content=request.query
    )
    db.add(user_msg)
    
    assistant_msg = ChatHistory(
        workspace_id=request.workspace_id,
        session_id=session_id,
        role="assistant",
        content=result["answer"],
        citations=[{"sources": result["sources"]}]
    )
    db.add(assistant_msg)
    
    await db.commit()
    
    return AgenticQueryResponse(
        answer=result["answer"],
        queries_executed=result["queries_executed"],
        sources=result["sources"],
        reasoning_steps=result["reasoning_steps"],
        iterations=result["iterations"],
        session_id=session_id
    )


@router.get("/schema")
async def get_schema():
    """Return the SQL schema description for reference."""
    from app.core.agentic_sql.schemas import SQL_SCHEMA_DESCRIPTION
    return {"schema": SQL_SCHEMA_DESCRIPTION}
```

#### 6. Updated Main App with Both RAG Modes

```python
# backend/app/main.py — Updated

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.api.routes import documents, chat, health, agentic_chat  # Added agentic_chat
from app.db.postgres import init_db
from app.db.weaviate import init_weaviate


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db()
    await init_weaviate()
    yield


app = FastAPI(
    title="Intelligent RAG API",
    description="""
    Document intelligence with two RAG modes:
    
    1. **Document Map RAG** (/api/chat): Uses living document map for one-shot retrieval
    2. **Agentic SQL RAG** (/api/agentic): Uses iterative SQL queries with LLM reasoning
    
    Both powered by Gemini 3 Flash.
    """,
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["Document Map RAG"])
app.include_router(agentic_chat.router, prefix="/api/agentic", tags=["Agentic SQL RAG"])  # NEW
```

#### 7. Updated Document Upload to Support Both Modes

```python
# backend/app/api/routes/documents.py — Add to upload endpoint

from app.core.agentic_sql.extractor import StructuredExtractor

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = "default",
    extraction_mode: str = "both",  # NEW: "map_only", "sql_only", "both"
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and process a document.
    
    extraction_mode:
    - "map_only": Only populate document map (original RAG)
    - "sql_only": Only populate SQL tables (agentic RAG)
    - "both": Populate both (default, recommended)
    """
    # ... existing OCR and processing code ...
    
    # Original document map flow
    if extraction_mode in ["map_only", "both"]:
        map_manager = DocumentMapManager(db)
        doc_entry = await map_manager.add_document(
            workspace_id=workspace_id,
            document_id=doc_id,
            filename=file.filename,
            content=result["content"],
            size_class=result["size_class"],
            chunks=result["chunks"]
        )
    
    # NEW: Agentic SQL extraction flow
    if extraction_mode in ["sql_only", "both"]:
        extractor = StructuredExtractor(db)
        sql_stats = await extractor.extract_and_store(
            document_id=doc_id,
            workspace_id=workspace_id,
            filename=file.filename,
            content=result["content"],
            chunks=result["chunks"]
        )
    
    return DocumentResponse(
        id=doc_id,
        filename=file.filename,
        size_class=result["size_class"],
        token_count=result["metadata"].get("token_count", 0),
        chunk_count=len(result["chunks"]) if result["chunks"] else 0,
        essence=doc_entry["essence"]["summary"] if extraction_mode != "sql_only" else "",
        topics=doc_entry["topics"]["primary"] if extraction_mode != "sql_only" else [],
        sql_extraction=sql_stats if extraction_mode != "map_only" else None  # NEW
    )
```

---

## Comparison: Document Map RAG vs Agentic SQL RAG

| Aspect | Document Map RAG | Agentic SQL RAG |
|--------|------------------|-----------------|
| **Retrieval** | One-shot via map consultation | Iterative via SQL queries |
| **Flexibility** | Fixed schema (essence, topics) | Open-ended queries |
| **Precision** | Good for topic matching | Excellent for specific facts/metrics |
| **Explainability** | Medium (retrieval reasoning) | High (see exact queries) |
| **Complex queries** | May miss nuance | Handles multi-hop naturally |
| **Speed** | Faster (1-2 LLM calls) | Slower (multiple iterations) |
| **Cost** | Lower | Higher (more LLM calls) |
| **Best for** | Quick answers, topic search | Analytical queries, fact-finding |

### When to Use Which

**Document Map RAG**:
- "What documents do we have about X?"
- "Summarize our Q3 performance"
- General knowledge questions
- Quick lookups

**Agentic SQL RAG**:
- "What was the exact revenue for APAC in Q3?"
- "Compare growth rates across all quarters"
- "Find all claims about competitor X"
- Numerical analysis
- Multi-step reasoning

---

## UI Extension for Mode Selection

```python
# frontend/app.py — Add mode selector

# In the chat interface section
rag_mode = st.radio(
    "RAG Mode",
    ["📚 Document Map", "🔍 Agentic SQL"],
    horizontal=True,
    help="Document Map: Fast, topic-based. Agentic SQL: Precise, iterative."
)

if rag_mode == "📚 Document Map":
    endpoint = "/api/chat/query"
else:
    endpoint = "/api/agentic/query"

# Show query transparency for Agentic mode
if rag_mode == "🔍 Agentic SQL" and st.session_state.messages:
    last_msg = st.session_state.messages[-1]
    if last_msg.get("queries_executed"):
        with st.expander("🔬 Query Transparency"):
            for i, (query, reasoning) in enumerate(zip(
                last_msg["queries_executed"],
                last_msg.get("reasoning_steps", [])
            )):
                st.markdown(f"**Step {i+1}**: {reasoning}")
                st.code(query, language="sql")
```

---

*Enhanced requirements document — December 2025*
*Addresses: Pre-filtering, quality extraction, alternative architecture*
