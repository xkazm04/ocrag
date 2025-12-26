# API Services Overview

Complete reference for all backend API endpoints with integration suitability indicators.

**Legend:**
- **UI**: Suitable for client integration (React app, dashboards)
- **Actor**: Candidate for Apify actor implementation (automated workflows, report generation)

---

## Research API (`/api/research`)

| Endpoint | Method | Description | UI | Actor |
|----------|--------|-------------|:--:|:-----:|
| `/start` | POST | Start research session with SSE streaming progress | | |
| `/sessions` | GET | List research sessions with filtering | ✓ | |
| `/sessions/{id}` | GET | Get specific research session details | ✓ | |
| `/sessions/{id}/findings` | GET | Get findings for a session with type/confidence filter | ✓ | |
| `/sessions/{id}/sources` | GET | Get sources for a session with credibility filter | ✓ | |
| `/sessions/{id}/perspectives` | GET | Get analysis perspectives for a session | ✓ | |
| `/sessions/{id}` | DELETE | Delete a research session and related data | ✓ | |
| `/sessions/{id}/continue` | POST | Continue research with additional queries (SSE) | | |
| `/templates` | GET | List available research templates | ✓ | |
| `/perspectives` | GET | List available analysis perspectives | ✓ | |
| `/cache/stats` | GET | Get research cache statistics | ✓ | |
| `/cache` | DELETE | Clear research cache by workspace/template | ✓ | |
| `/health` | GET | Health check for research module | ✓ | ✓ |
| `/submit` | POST | Submit async research job (returns job_id) | ✓ | ✓ |
| `/status/{job_id}` | GET | Poll job status with progress and results | ✓ | ✓ |
| `/jobs` | GET | List research jobs with status filter | ✓ | |
| `/jobs/{job_id}` | DELETE | Cancel pending/running job | ✓ | |
| `/verify` | POST | Fact-check statement using web + knowledge base | ✓ | ✓ |
| `/extract-evidence` | POST | Extract evidence from document (PDF/text) | | ✓ |

---

## Reports API (`/api/research/reports`)

| Endpoint | Method | Description | UI | Actor |
|----------|--------|-------------|:--:|:-----:|
| `/generate` | POST | Generate report in JSON/Markdown/HTML/PDF format | ✓ | ✓ |
| `/variants` | GET | List available report variants by template type | ✓ | |
| `/formats` | GET | List available output formats with requirements | ✓ | |
| `/preview/{session_id}` | GET | Quick markdown preview of report content | ✓ | |

---

## Knowledge Explorer API (`/api/research/knowledge`)

| Endpoint | Method | Description | UI | Actor |
|----------|--------|-------------|:--:|:-----:|
| `/graph` | POST | Get entity relationship graph for visualization | ✓ | |
| `/timeline` | POST | Get chronological timeline of events/claims | ✓ | ✓ |
| `/corroborate` | POST | Analyze evidence corroboration across sources | ✓ | ✓ |
| `/patterns` | POST | Detect entity clusters, temporal bursts, anomalies | ✓ | ✓ |
| `/ask` | POST | Investigative Q&A with RAG and citations | ✓ | ✓ |
| `/entity-profile` | POST | Get comprehensive entity profile with connections | ✓ | |
| `/financial` | POST | Query financial transactions with aggregations | ✓ | ✓ |
| `/stats` | GET | Get knowledge base statistics | ✓ | |

---

## OCR API (`/ocr`)

| Endpoint | Method | Description | UI | Actor |
|----------|--------|-------------|:--:|:-----:|
| `/info` | GET | Get available OCR engines and their status | ✓ | |
| `/process` | POST | Process document with multiple OCR engines | ✓ | ✓ |
| `/process/{engine_id}` | POST | Process document with single OCR engine | ✓ | ✓ |
| `/evaluate` | POST | Run comparative evaluation on OCR results | ✓ | |

---

## UI Integration Recommendations

Top 5 services recommended for React/dashboard integration:

### 1. Knowledge Graph Visualization (`POST /knowledge/graph`)
Interactive network visualization of entity relationships. Returns nodes and edges suitable for D3.js, Cytoscape, or vis.js graph libraries. Enables users to explore connections between people, organizations, and claims.

### 2. Research Sessions Dashboard (`GET /sessions` + `/sessions/{id}/*`)
Complete session management with findings, sources, and perspectives. Build a research history browser with drill-down capabilities for detailed analysis review.

### 3. Investigative Q&A Interface (`POST /knowledge/ask`)
Natural language query interface with RAG-powered answers and citations. Perfect for a chat-like investigation interface where users ask questions about the knowledge base.

### 4. Timeline Visualization (`POST /knowledge/timeline`)
Chronological event browser with entity activity tracking. Ideal for interactive timeline components showing when events occurred and who was involved.

### 5. Report Preview & Generation (`GET /reports/preview/{id}` + `POST /reports/generate`)
Full report generation workflow with preview capability. Users can preview in markdown, then export to HTML or PDF formats for sharing.

---

## Actor Implementation Recommendations

Top 5 services recommended for Apify actor development:

### 1. Deep Research Actor (`POST /submit` + `GET /status/{job_id}`)
**Use Case**: Automated investigative research on topics/entities
- Submit research query with template (investigative, financial, competitive)
- Poll for completion with progress tracking
- Collect findings, perspectives, and source analysis
- Output: Structured research session with 50+ findings per query

### 2. Document Evidence Extractor (`POST /extract-evidence`)
**Use Case**: Batch document processing pipeline
- Process PDF documents or text content
- Extract structured claims with confidence scores
- Automatic quality filtering and deduplication
- Output: Knowledge claims ready for database insertion

### 3. Report Generation Actor (`POST /reports/generate`)
**Use Case**: Scheduled report generation service
- Generate reports from completed research sessions
- Support multiple variants: executive summary, timeline, dossier
- Output formats: JSON, Markdown, HTML, PDF-ready HTML
- Ideal for periodic briefing generation

### 4. Fact Verification Actor (`POST /verify`)
**Use Case**: Automated claim verification service
- Verify statements against web sources and knowledge base
- Get verdict (supported/contradicted/inconclusive) with confidence
- Collect supporting and contradicting evidence
- Output: Verification report with source citations

### 5. Financial Intelligence Actor (`POST /knowledge/financial` + `/patterns`)
**Use Case**: Financial transaction analysis and pattern detection
- Query financial transactions with filters (amount, parties, dates)
- Detect suspicious patterns and temporal anomalies
- Aggregate by payer/payee/type for money flow analysis
- Output: Financial summary with pattern alerts

---

## Authentication

All endpoints currently operate without authentication. For production deployment, implement:
- API key authentication for Actor integrations
- JWT tokens for UI client sessions
- Rate limiting per workspace

## Error Handling

Standard HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid parameters)
- `404` - Resource not found
- `503` - Service unavailable (e.g., Gemini API down)
- `500` - Internal server error

All errors return JSON with `detail` field explaining the issue.
