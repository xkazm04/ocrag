# Intelligent RAG System

A modern document intelligence system powered by Gemini with **two RAG architectures** to compare: Document Map RAG and Agentic SQL RAG.

## Features

- **Dual RAG Modes**: Switch between Document Map RAG and Agentic SQL RAG via tabs
- **Document Map RAG**: One-shot retrieval using living document map
- **Agentic SQL RAG**: Iterative SQL queries with LLM reasoning
- **Smart Document Handling**: Small documents retrieved whole, large documents contextually chunked
- **Native OCR**: Gemini vision for PDF/image text extraction
- **Dark-Themed UI**: Modern Streamlit interface with tabbed chat

## Two RAG Architectures

### 1. Document Map RAG
- LLM-maintained index with essences, topics, and cross-references
- One-shot retrieval: single LLM call selects relevant docs
- Fast (1-2 LLM calls)
- Best for: Quick answers, topic-based search

### 2. Agentic SQL RAG
- Documents decomposed into structured SQL tables (claims, metrics, entities, topics)
- LLM plans and executes SQL queries iteratively
- Full query transparency
- Best for: Precise fact-finding, numerical analysis, multi-hop queries

## Architecture

```
+---------------+     +---------------+     +---------------+
|   Streamlit   |---->|   FastAPI     |---->|   PostgreSQL  |
|   Frontend    |     |   Backend     |     |   + Weaviate  |
|   (Tabs UI)   |     |   Port 8000   |     |   5432/8080   |
+---------------+     +-------+-------+     +---------------+
                              |
                     +--------+--------+
                     |                 |
              +------v------+   +------v------+
              | Doc Map RAG |   | SQL RAG     |
              | /api/chat   |   | /api/agentic|
              +-------------+   +-------------+
                              |
                      +-------v-------+
                      |    Gemini     |
                      |    Flash API  |
                      +---------------+
```

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### 2. Setup

```bash
# Navigate to the project
cd rag

# Create environment file
copy .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_key_here
```

### 3. Run

```bash
# Start all services
docker-compose up -d

# Wait for services to be healthy (about 30 seconds)
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Access

- **Frontend UI**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Usage

1. **Upload Documents**: Use the sidebar to upload PDF or image files
2. **Choose Extraction Mode**: Select "both" to enable both RAG modes
3. **Switch Tabs**: Use tabs to switch between Document Map RAG and Agentic SQL RAG
4. **Ask Questions**: Type questions in the chat input of either tab
5. **Compare Results**: Try the same query in both modes to compare

## API Endpoints

### Document Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload?extraction_mode=both` | Upload with mode (both/map_only/sql_only) |
| GET | `/api/documents/` | List all documents |
| DELETE | `/api/documents/{id}` | Delete document |

### Document Map RAG
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/query` | Query via document map |
| GET | `/api/chat/history/{session_id}` | Get chat history |

### Agentic SQL RAG
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agentic/query` | Query via SQL agent |
| GET | `/api/agentic/stats` | Get extraction statistics |
| GET | `/api/agentic/schema` | Get SQL schema description |

## Project Structure

```
rag/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── api/routes/
│       │   ├── documents.py
│       │   ├── chat.py           # Document Map RAG
│       │   └── agentic_chat.py   # Agentic SQL RAG
│       ├── core/
│       │   ├── gemini_client.py
│       │   ├── ocr_processor.py
│       │   ├── document_map.py
│       │   ├── retriever.py
│       │   └── agentic_sql/      # SQL RAG module
│       │       ├── schemas.py    # SQL table models
│       │       ├── extractor.py  # Structured extraction
│       │       ├── sql_tool.py   # SQL execution
│       │       └── agent.py      # Agentic agent
│       ├── db/
│       └── schemas/
├── frontend/
│   └── app.py                    # Tabbed UI
└── scripts/
    └── init_db.sql
```

## SQL Tables (Agentic Mode)

When using "both" or "sql_only" extraction, documents are decomposed into:

| Table | Description |
|-------|-------------|
| `sql_documents` | Document metadata (summary, purpose, dates) |
| `sql_claims` | Factual claims with topic and confidence |
| `sql_metrics` | Quantitative data with parsed values |
| `sql_entities` | Named entities (orgs, people, products) |
| `sql_topics` | Document topics (primary/secondary) |
| `sql_document_chunks` | Full text chunks for fallback |

## Comparison: When to Use Which

| Use Case | Document Map RAG | Agentic SQL RAG |
|----------|-----------------|-----------------|
| "What documents discuss X?" | Best | Good |
| "What was Q3 revenue for Company Y?" | Good | Best |
| "Compare metrics across documents" | Limited | Best |
| Quick topic-based search | Best | Slower |
| Multi-hop analytical queries | Limited | Best |
| Speed | Fast (1-2 calls) | Slower (3-5+ calls) |

## Configuration

Environment variables (in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| GEMINI_API_KEY | Your Gemini API key | (required) |
| POSTGRES_USER | PostgreSQL user | raguser |
| POSTGRES_PASSWORD | PostgreSQL password | ragpass |
| POSTGRES_DB | PostgreSQL database | ragdb |
| ENVIRONMENT | development/production | development |

## Development

```bash
# Rebuild after code changes
docker-compose up --build

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down

# Stop and remove volumes (reset data)
docker-compose down -v
```

## Tech Stack

- **Backend**: FastAPI, Python 3.11
- **Frontend**: Streamlit (tabbed interface)
- **LLM**: Gemini Flash
- **Vector DB**: Weaviate (hybrid search fallback)
- **Relational DB**: PostgreSQL
- **Containerization**: Docker Compose

---

## Research Intelligence System

The platform includes a powerful research system with domain-specific templates and multi-perspective analysis.

### Research Templates

| Template | ID | Description | Default Perspectives |
|----------|-----|-------------|---------------------|
| **Investigative Research** | `investigative` | Deep investigative journalism research | political, economic, psychological, historical |
| **Competitive Intelligence** | `competitive` | Market and competitor analysis | market_position, competitive_advantage, swot, pricing_strategy |
| **Financial Analysis** | `financial` | Stock and investment research | valuation, risk, sentiment, fundamental |
| **Legal Research** | `legal` | Legal and regulatory research | compliance, precedent, regulatory_risk, jurisdiction |

### Research API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/research/submit` | Submit async research job |
| GET | `/research/status/{job_id}` | Poll job status and results |
| GET | `/research/sessions` | List research sessions |
| POST | `/research/verify` | Fact-check a statement |
| POST | `/research/extract-evidence` | Extract evidence from documents |

### Use Cases & Example Queries

#### Investigative Research
Best for: Journalism, due diligence, background investigations

| Query Type | Example |
|------------|---------|
| Actor Analysis | "Who are the key players in the FTX collapse?" |
| Timeline Construction | "Create timeline of Boeing 737 MAX incidents" |
| Relationship Mapping | "Map connections between Theranos executives" |
| Evidence Gathering | "What evidence links company X to fraud allegations?" |
| Pattern Detection | "What patterns exist in SEC enforcement against crypto" |

#### Competitive Intelligence
Best for: Market research, strategic planning, M&A due diligence

| Query Type | Example |
|------------|---------|
| Market Analysis | "Slack vs Microsoft Teams market comparison 2024" |
| Competitor Profiling | "Analyze Shopify's competitive positioning" |
| SWOT Analysis | "SWOT analysis for entering EV charging market" |
| Pricing Intelligence | "Compare SaaS pricing: HubSpot vs Salesforce vs Pipedrive" |
| Strategic Moves | "Recent M&A activity in cloud infrastructure" |
| Market Entry | "Competitive landscape for AI code assistants" |

#### Financial Analysis
Best for: Investment research, earnings analysis, risk assessment

| Query Type | Example |
|------------|---------|
| Earnings Analysis | "NVIDIA Q4 2024 earnings analysis and outlook" |
| Valuation | "Is Tesla overvalued at current multiples?" |
| Risk Assessment | "Credit risk factors for commercial real estate REITs" |
| Sector Analysis | "AI infrastructure investment thesis 2025" |
| Sentiment | "Market sentiment on Federal Reserve rate decisions" |
| Comparative | "Compare cloud margins: AWS vs Azure vs GCP" |

#### Legal Research
Best for: Compliance, regulatory analysis, case research

| Query Type | Example |
|------------|---------|
| Compliance | "GDPR compliance requirements for AI companies" |
| Case Law | "Recent Supreme Court decisions on Section 230" |
| Regulatory | "SEC crypto enforcement actions 2023-2024" |
| Multi-Jurisdictional | "Data privacy laws: EU vs California vs Brazil" |
| Risk Analysis | "Antitrust risks for big tech acquisitions" |
| Precedent | "Patent infringement precedents in software industry" |

### Jurisdictional Filtering

Research can be filtered by jurisdiction using:

1. **Topic Hierarchy**: Create topics like `Legal > USA > California` or `Legal > EU > Germany`
2. **Extracted Data**: Claims store `{"jurisdiction": "USA", "state": "CA"}` in `extracted_data`
3. **Tags**: Apply jurisdiction tags to claims (e.g., `["jurisdiction:eu", "country:germany"]`)

Example topic structure for legal research:
```
Legal Research/
├── United States/
│   ├── Federal/
│   ├── California/
│   ├── New York/
│   └── Texas/
├── European Union/
│   ├── GDPR/
│   ├── Germany/
│   └── France/
├── United Kingdom/
└── Asia Pacific/
    ├── Singapore/
    └── Japan/
```

### Entity Types by Domain

| Domain | Entity Types |
|--------|--------------|
| **General** | person, organization, location, product, concept |
| **Competitive** | competitor, market_segment, product_line |
| **Financial** | publicly_traded_company, security, fund |
| **Legal** | court, judge, legal_case, regulatory_body |

### Source Types by Domain

| Domain | Source Types |
|--------|--------------|
| **General** | news, academic, government, corporate, blog, social, wiki |
| **Financial** | sec_filing, earnings_report, analyst_report, financial_news, press_release |
| **Legal** | court_ruling, statute, regulation, legal_commentary |

### Relationship Types

| Category | Types |
|----------|-------|
| **Logical** | causes, supports, contradicts, expands, supersedes |
| **Reference** | related_to, part_of, precedes, derived_from |
| **Verification** | corroborates, refutes |
| **Competitive** | competes_with, partners_with |
| **Legal** | overrules, distinguishes, extends_precedent, cites |

### Research System Architecture

```
Research Request
       │
       ├── Template Selection (investigative/competitive/financial/legal)
       │
       ├── Search Query Generation (domain-specific angles)
       │
       ├── Source Discovery (Gemini grounded search)
       │
       ├── Finding Extraction (structured findings)
       │
       ├── Quality Filter (confidence, length, vagueness)
       │
       ├── Deduplication (against knowledge base)
       │
       ├── Multi-Perspective Analysis
       │   ├── Investigative: Historian, Economist, Political, Psychologist, Military
       │   ├── Competitive: MarketPosition, CompetitiveAdvantage, SWOT, PricingStrategy
       │   ├── Financial: Valuation, Risk, Sentiment, Fundamental
       │   └── Legal: Compliance, Precedent, RegulatoryRisk, Jurisdiction
       │
       └── Knowledge Base Integration
           ├── Topics (hierarchical)
           ├── Entities (deduplicated)
           ├── Claims (verified)
           └── Relationships (linked)
```

---

## Report Generation API

Transform research sessions into professional reports in multiple formats and variants.

### Report API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/research/reports/generate` | Generate report in specified format |
| GET | `/research/reports/variants` | List available report variants |
| GET | `/research/reports/formats` | List output formats |
| GET | `/research/reports/preview/{session_id}` | Quick preview in markdown |

### Output Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| `json` | Structured response with markdown + metadata | API integration, further processing |
| `markdown` | Raw markdown text file | Documentation, version control |
| `html` | LLM-styled HTML document | Web display, email, frontend rendering |

**Note on PDF Generation**: HTML output includes print-optimized CSS. Frontend apps can convert HTML to PDF using libraries like `html2pdf.js`, `jsPDF`, or browser print dialogs. This approach is preferred over server-side PDF generation as it:
- Eliminates server dependencies (WeasyPrint/GTK)
- Reduces server load
- Gives frontend control over print styling
- Works across all platforms

### Report Variants (16 Types)

#### Universal Variants (All Templates)

| Variant | ID | Description |
|---------|-----|-------------|
| **Executive Summary** | `executive_summary` | 1-2 page high-level overview with key findings, insights, and recommendations |
| **Full Report** | `full_report` | Comprehensive document with all sections, findings by category, complete source list |
| **Findings Only** | `findings_only` | Findings grouped by type (facts, events, patterns, gaps) with confidence scores |
| **Source Bibliography** | `source_bibliography` | Annotated source list with credibility ratings and snippets |

#### Investigative Template Variants

| Variant | ID | Description |
|---------|-----|-------------|
| **Timeline Report** | `timeline_report` | Chronological narrative of events with dates, actors, and confidence levels |
| **Actor Dossier** | `actor_dossier` | Entity profiles with roles, affiliations, aliases, and relationship mapping |
| **Evidence Brief** | `evidence_brief` | Evidence chain summary with direct evidence, corroborating facts, and gaps |

#### Competitive Intelligence Variants

| Variant | ID | Description |
|---------|-----|-------------|
| **Competitive Matrix** | `competitive_matrix` | Side-by-side competitor comparison table with positioning and differentiators |
| **SWOT Analysis** | `swot_analysis` | Structured SWOT format with categorized insights |
| **Battlecard** | `battlecard` | Sales enablement format with key differentiators, competitive weaknesses, talk tracks |

#### Financial Analysis Variants

| Variant | ID | Description |
|---------|-----|-------------|
| **Investment Thesis** | `investment_thesis` | Bull/bear case with key metrics, rating, and recommendations |
| **Earnings Summary** | `earnings_summary` | Financial metrics, guidance, analyst perspectives |
| **Risk Assessment** | `risk_assessment` | Risk factors categorized by severity (high/medium/low) with mitigation |

#### Legal Research Variants

| Variant | ID | Description |
|---------|-----|-------------|
| **Legal Brief** | `legal_brief` | IRAC format memorandum (Issue, Rule, Application, Conclusion) |
| **Case Digest** | `case_digest` | Case holdings, citations, precedents, and legal principles |
| **Compliance Checklist** | `compliance_checklist` | Requirements matrix with status (Met/Not Met/Pending) and priorities |

### Report Generation Examples

#### Generate Executive Summary
```bash
curl -X POST "http://localhost:8000/api/research/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-here",
    "variant": "executive_summary",
    "format": "json"
  }'
```

#### Generate Competitive Matrix as HTML
```bash
curl -X POST "http://localhost:8000/api/research/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-here",
    "variant": "competitive_matrix",
    "format": "html",
    "title": "Q4 2024 Competitor Analysis"
  }'
```

#### Generate Legal Brief as Markdown
```bash
curl -X POST "http://localhost:8000/api/research/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-here",
    "variant": "legal_brief",
    "format": "markdown"
  }'
```

### Report Styling

Each template type has its own visual style guide:

| Template | Tone | Visual Style |
|----------|------|--------------|
| **Investigative** | Journalistic, objective | Clean, newspaper-inspired, timeline emphasis |
| **Competitive** | Analytical, strategic | Modern dashboard, comparison tables, metrics |
| **Financial** | Quantitative, precise | Bloomberg-inspired, metric-heavy, ratings |
| **Legal** | Formal, authoritative | Traditional legal format, citations, minimal |

### Frontend PDF Generation

For React/Next.js apps receiving HTML reports, recommended PDF libraries:

```javascript
// Option 1: html2pdf.js (simplest)
import html2pdf from 'html2pdf.js';

const generatePDF = (htmlContent, filename) => {
  const element = document.createElement('div');
  element.innerHTML = htmlContent;

  html2pdf()
    .set({
      margin: 10,
      filename: `${filename}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2 },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    })
    .from(element)
    .save();
};

// Option 2: Browser print dialog (built-in)
const printToPDF = (htmlContent) => {
  const printWindow = window.open('', '_blank');
  printWindow.document.write(htmlContent);
  printWindow.document.close();
  printWindow.print();
};
```

### Report Architecture

```
POST /research/reports/generate
         │
         ▼
┌─────────────────┐
│ Data Aggregator │ ◄── Sessions, Findings, Perspectives, Sources
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────────────────┐
│ Markdown        │      │ Composers:                    │
│ Composer        │ ◄────│ • ExecutiveSummaryComposer    │
│ (Template-aware)│      │ • FullReportComposer          │
└────────┬────────┘      │ • InvestigativeComposer       │
         │               │ • CompetitiveComposer         │
         ▼               │ • FinancialComposer           │
┌─────────────────┐      │ • LegalComposer               │
│ Format Router   │      └──────────────────────────────┘
└────────┬────────┘
         │
   ┌─────┼─────┬─────────┐
   ▼     ▼     ▼         ▼
 JSON  MARKDOWN  HTML   (Future)
                  │
             ┌────┴────┐
             │OpenRouter│
             │ Gemini   │
             └────┬────┘
                  │
                  ▼
             Styled HTML
                  │
                  ▼
          Frontend PDF
          (html2pdf.js)
```
