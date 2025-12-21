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
