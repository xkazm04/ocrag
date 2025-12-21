# Intelligent RAG System with Gemini 3 Flash

## Project Overview

Build a modern document intelligence system that leverages Gemini 3 Flash for OCR, intelligent RAG, and conversational retrieval. The system uses a paradigm-shifting approach where small documents are retrieved whole, large documents are contextually chunked, and a "living document map" enables one-shot retrieval without re-ranking.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DOCKER COMPOSE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │  Streamlit  │   │   FastAPI   │   │  Weaviate   │   │  PostgreSQL │     │
│  │    UI       │──▶│   Backend   │──▶│   Vector    │   │  Relational │     │
│  │  Port 8501  │   │  Port 8000  │   │  Port 8080  │   │  Port 5432  │     │
│  └─────────────┘   └──────┬──────┘   └─────────────┘   └─────────────┘     │
│                           │                                                 │
│                           ▼                                                 │
│                    ┌─────────────┐                                         │
│                    │ Gemini 3    │                                         │
│                    │ Flash API   │                                         │
│                    └─────────────┘                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: Streamlit with dark theme
- **LLM**: Gemini 3 Flash (gemini-3-flash-preview)
- **Vector DB**: Weaviate (for chunk embeddings as fallback/hybrid search)
- **Relational DB**: PostgreSQL (document metadata, map storage, chat history)
- **Containerization**: Docker Compose

---

## Part 1: Project Structure

```
intelligent-rag/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Settings and configuration
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── documents.py    # Document upload, delete, list
│   │   │   │   ├── chat.py         # Chat/query endpoints
│   │   │   │   └── health.py       # Health checks
│   │   │   └── dependencies.py     # Shared dependencies
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── gemini_client.py    # Unified Gemini 3 Flash client
│   │   │   ├── ocr_processor.py    # PDF/Image OCR with Gemini
│   │   │   ├── document_map.py     # Living document map management
│   │   │   ├── retriever.py        # One-shot retrieval logic
│   │   │   └── chunker.py          # Semantic chunking for large docs
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── postgres.py         # PostgreSQL connection and models
│   │   │   ├── weaviate.py         # Weaviate client and schemas
│   │   │   └── models.py           # SQLAlchemy models
│   │   │
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── document.py         # Pydantic schemas for documents
│   │       ├── chat.py             # Chat request/response schemas
│   │       └── map.py              # Document map schemas
│   │
│   └── alembic/                    # Database migrations
│       ├── alembic.ini
│       └── versions/
│
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                      # Main Streamlit app
│   ├── components/
│   │   ├── __init__.py
│   │   ├── sidebar.py              # Document management sidebar
│   │   ├── chat.py                 # Chat interface
│   │   └── file_upload.py          # File upload component
│   └── styles/
│       └── dark_theme.py           # Dark theme configuration
│
└── scripts/
    ├── init_db.sql                 # PostgreSQL initialization
    └── seed_weaviate.py            # Weaviate schema setup
```

---

## Part 2: Docker Configuration

### docker-compose.yml

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: rag-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-raguser}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-ragpass}
      POSTGRES_DB: ${POSTGRES_DB:-ragdb}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-raguser}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - rag-network

  # Weaviate Vector Database
  weaviate:
    image: semitechnologies/weaviate:1.28.2
    container_name: rag-weaviate
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'none'
      ENABLE_MODULES: ''
      CLUSTER_HOSTNAME: 'node1'
    volumes:
      - weaviate_data:/var/lib/weaviate
    ports:
      - "8080:8080"
      - "50051:50051"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/v1/.well-known/ready"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - rag-network

  # FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: rag-backend
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - POSTGRES_URL=postgresql+asyncpg://${POSTGRES_USER:-raguser}:${POSTGRES_PASSWORD:-ragpass}@postgres:5432/${POSTGRES_DB:-ragdb}
      - WEAVIATE_URL=http://weaviate:8080
      - ENVIRONMENT=${ENVIRONMENT:-development}
    volumes:
      - ./backend/app:/app/app
      - document_storage:/app/storage
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      weaviate:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - rag-network

  # Streamlit Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: rag-frontend
    environment:
      - BACKEND_URL=http://backend:8000
    volumes:
      - ./frontend:/app
    ports:
      - "8501:8501"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - rag-network

volumes:
  postgres_data:
  weaviate_data:
  document_storage:

networks:
  rag-network:
    driver: bridge
```

### .env.example

```env
# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# PostgreSQL
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpass
POSTGRES_DB=ragdb

# Environment
ENVIRONMENT=development
```

---

## Part 3: Backend Implementation

### backend/Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create storage directory
RUN mkdir -p /app/storage

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### backend/requirements.txt

```
# FastAPI and server
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.19

# Database
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.0

# Weaviate
weaviate-client==4.9.6

# Gemini
google-genai==1.0.0

# PDF processing
pymupdf==1.25.1
Pillow==11.0.0

# Utilities
pydantic==2.10.3
pydantic-settings==2.7.0
python-dotenv==1.0.1
httpx==0.28.1
tenacity==9.0.0
tiktoken==0.8.0

# Async utilities
aiofiles==24.1.0
```

### backend/app/config.py

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API Keys
    gemini_api_key: str
    
    # Database
    postgres_url: str
    weaviate_url: str = "http://weaviate:8080"
    
    # Document processing
    small_doc_threshold_tokens: int = 50000  # ~35-40 pages
    chunk_size_tokens: int = 8000
    chunk_overlap_tokens: int = 500
    
    # Gemini settings
    gemini_model: str = "gemini-3-flash-preview"
    default_thinking_level: str = "medium"
    
    # Storage
    storage_path: str = "/app/storage"
    
    # Environment
    environment: str = "development"
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### backend/app/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.api.routes import documents, chat, health
from app.db.postgres import init_db
from app.db.weaviate import init_weaviate


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    await init_db()
    await init_weaviate()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Intelligent RAG API",
    description="Document intelligence with Gemini 3 Flash",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
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
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
```

### backend/app/core/gemini_client.py

```python
"""
Unified Gemini 3 Flash client for OCR, extraction, retrieval, and chat.
Implements context caching for cost optimization.
"""
import base64
from typing import Optional
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


class GeminiClient:
    """Unified client for all Gemini 3 Flash operations."""
    
    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        self._cached_map_id: Optional[str] = None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def ocr_pdf(
        self,
        pdf_bytes: bytes,
        extraction_prompt: Optional[str] = None
    ) -> dict:
        """
        Extract text and structure from PDF using Gemini's native vision.
        
        Returns:
            {
                "content": str,  # Markdown formatted content
                "metadata": {
                    "pages": int,
                    "has_tables": bool,
                    "has_images": bool,
                    "estimated_tokens": int
                }
            }
        """
        prompt = extraction_prompt or """
        Extract ALL content from this PDF document.
        
        Output format:
        1. Convert to clean Markdown preserving structure
        2. Preserve tables as Markdown tables
        3. Describe images/charts in [IMAGE: description] blocks
        4. Maintain headers, lists, and formatting
        5. For multi-column layouts, process left-to-right
        
        After the content, provide metadata as JSON:
        ```json
        {"pages": N, "has_tables": bool, "has_images": bool}
        ```
        """
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                types.Part.from_text(text=prompt)
            ],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="medium"),
                response_mime_type="text/plain"
            )
        )
        
        return self._parse_ocr_response(response.text)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def extract_document_intelligence(
        self,
        content: str,
        filename: str
    ) -> dict:
        """
        Extract intelligence from document for the document map.
        
        Returns:
            {
                "essence": str,
                "topics": list[str],
                "entities": dict,
                "retrieval_hints": str,
                "suggested_chunks": list[dict] | None
            }
        """
        prompt = f"""
        Analyze this document and extract structured intelligence.
        
        Document filename: {filename}
        
        Content:
        {content[:100000]}  # Limit for context
        
        Provide a JSON response with:
        {{
            "essence": "2-3 sentence summary of core content and purpose",
            "topics": ["topic1", "topic2", ...],  // Key themes for retrieval
            "entities": {{
                "organizations": [...],
                "people": [...],
                "dates": [...],
                "metrics": [...],
                "locations": [...]
            }},
            "retrieval_hints": "What questions would this document answer? What queries should retrieve this?",
            "document_type": "financial_report|legal_contract|technical_doc|correspondence|other",
            "suggested_chunk_boundaries": [
                {{"start_marker": "Section 1...", "end_marker": "Section 2...", "topic": "..."}}
            ] // Only if document is long, null otherwise
        }}
        """
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="high"),
                response_mime_type="application/json"
            )
        )
        
        return self._parse_json_response(response.text)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def consult_map_for_retrieval(
        self,
        query: str,
        document_map: dict
    ) -> dict:
        """
        One-shot retrieval: consult document map to select documents/chunks.
        
        Returns:
            {
                "retrieve": ["doc_id", "doc_id_chunk_N", ...],
                "reasoning": str
            }
        """
        prompt = f"""
        You are a retrieval specialist. Given a user query and document map,
        select the MINIMAL set of documents/chunks needed to answer the query.
        
        USER QUERY: {query}
        
        DOCUMENT MAP:
        {self._format_map_for_prompt(document_map)}
        
        Instructions:
        1. Analyze query intent and information needs
        2. Match against document essences, topics, and retrieval hints
        3. For small documents (size_class="small"), return doc_id
        4. For large documents, return specific chunk_ids (e.g., "doc_123_c2")
        5. Consider cross-references for multi-hop queries
        6. Return MINIMAL set - don't over-retrieve
        
        Response format (JSON):
        {{
            "retrieve": ["doc_001", "doc_042_c3", "doc_042_c4"],
            "reasoning": "Brief explanation of selection logic"
        }}
        """
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="low"),  # Fast
                response_mime_type="application/json"
            )
        )
        
        return self._parse_json_response(response.text)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def generate_answer(
        self,
        query: str,
        retrieved_content: list[dict],
        chat_history: Optional[list[dict]] = None
    ) -> dict:
        """
        Generate answer using retrieved documents.
        
        Args:
            query: User's question
            retrieved_content: List of {"id": str, "content": str, "context": str}
            chat_history: Previous messages for context
        
        Returns:
            {
                "answer": str,
                "citations": [{"doc_id": str, "excerpt": str}],
                "confidence": float
            }
        """
        # Build context
        context_parts = []
        for doc in retrieved_content:
            context_parts.append(f"""
[Document: {doc['id']}]
{doc.get('context', '')}

{doc['content']}
---
""")
        
        history_text = ""
        if chat_history:
            history_text = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in chat_history[-5:]  # Last 5 messages
            ])
        
        prompt = f"""
        Answer the user's question using ONLY the provided documents.
        
        DOCUMENTS:
        {''.join(context_parts)}
        
        {f'CHAT HISTORY:{chr(10)}{history_text}' if history_text else ''}
        
        USER QUESTION: {query}
        
        Instructions:
        1. Answer directly and concisely
        2. Cite sources using [doc_id] format
        3. If information is insufficient, say so clearly
        4. Do not hallucinate - only use provided content
        
        Response format (JSON):
        {{
            "answer": "Your comprehensive answer with [doc_id] citations",
            "citations": [
                {{"doc_id": "doc_001", "excerpt": "Relevant quote"}}
            ],
            "confidence": 0.0-1.0
        }}
        """
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="medium"),
                response_mime_type="application/json"
            )
        )
        
        return self._parse_json_response(response.text)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def update_document_map(
        self,
        existing_map: dict,
        new_document: dict
    ) -> dict:
        """
        Update document map with new document, identifying relationships.
        
        Returns updated map with new document and cross-references.
        """
        prompt = f"""
        Update this document map with a new document.
        
        EXISTING MAP SUMMARY:
        {existing_map.get('corpus_summary', 'Empty corpus')}
        
        EXISTING DOCUMENTS (summaries):
        {self._format_existing_docs_summary(existing_map)}
        
        NEW DOCUMENT:
        ID: {new_document['id']}
        Filename: {new_document['filename']}
        Essence: {new_document['essence']}
        Topics: {new_document['topics']}
        Entities: {new_document['entities']}
        
        Tasks:
        1. Identify relationships to existing documents
        2. Update cross-references (by_entity, by_topic)
        3. Update corpus_summary to reflect new addition
        
        Response format (JSON):
        {{
            "relationships": [
                {{"doc_id": "existing_doc_id", "relation": "references|supersedes|complements", "note": "..."}}
            ],
            "new_cross_references": {{
                "by_entity": {{"EntityName": ["doc_ids"]}},
                "by_topic": {{"topic": ["doc_ids"]}}
            }},
            "updated_corpus_summary": "New summary incorporating this document"
        }}
        """
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="medium"),
                response_mime_type="application/json"
            )
        )
        
        return self._parse_json_response(response.text)
    
    def _parse_ocr_response(self, text: str) -> dict:
        """Parse OCR response separating content and metadata."""
        import json
        import re
        
        # Try to find JSON metadata block
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        
        if json_match:
            content = text[:json_match.start()].strip()
            try:
                metadata = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                metadata = {"pages": 1, "has_tables": False, "has_images": False}
        else:
            content = text
            metadata = {"pages": 1, "has_tables": False, "has_images": False}
        
        # Estimate tokens
        metadata["estimated_tokens"] = len(content) // 4
        
        return {"content": content, "metadata": metadata}
    
    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON response from Gemini."""
        import json
        import re
        
        # Clean potential markdown code blocks
        text = re.sub(r'^```json\s*', '', text.strip())
        text = re.sub(r'\s*```$', '', text)
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Could not parse JSON from response: {text[:500]}")
    
    def _format_map_for_prompt(self, document_map: dict) -> str:
        """Format document map for inclusion in prompt."""
        import json
        # Truncate large maps
        simplified = {
            "corpus_summary": document_map.get("corpus_summary", ""),
            "documents": [
                {
                    "id": d["id"],
                    "essence": d["essence"],
                    "topics": d["topics"],
                    "retrieval_hints": d.get("retrieval_hints", ""),
                    "size_class": d.get("size_class", "small"),
                    "chunks": [
                        {"chunk_id": c["chunk_id"], "topic": c.get("topic", "")}
                        for c in d.get("chunks", [])
                    ] if d.get("chunks") else None
                }
                for d in document_map.get("documents", [])
            ],
            "cross_references": document_map.get("cross_references", {})
        }
        return json.dumps(simplified, indent=2)
    
    def _format_existing_docs_summary(self, document_map: dict) -> str:
        """Format existing documents for map update prompt."""
        docs = document_map.get("documents", [])
        summaries = [
            f"- {d['id']}: {d['essence'][:100]}..."
            for d in docs[:20]  # Limit
        ]
        return "\n".join(summaries) if summaries else "No existing documents"


# Singleton instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
```

### backend/app/core/ocr_processor.py

```python
"""
PDF processing and OCR using Gemini 3 Flash multimodal capabilities.
"""
import fitz  # PyMuPDF
import io
from pathlib import Path
from typing import Optional
import tiktoken

from app.core.gemini_client import get_gemini_client
from app.config import get_settings


class OCRProcessor:
    """Process documents using Gemini 3 Flash's native multimodal OCR."""
    
    def __init__(self):
        self.gemini = get_gemini_client()
        self.settings = get_settings()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    async def process_pdf(
        self,
        file_bytes: bytes,
        filename: str
    ) -> dict:
        """
        Process PDF using Gemini 3 Flash native vision.
        
        Returns:
            {
                "content": str,
                "metadata": dict,
                "size_class": "small" | "large",
                "chunks": list[dict] | None
            }
        """
        # Get page count for logging
        pdf = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = len(pdf)
        pdf.close()
        
        # Use Gemini for OCR
        ocr_result = await self.gemini.ocr_pdf(file_bytes)
        
        content = ocr_result["content"]
        metadata = ocr_result["metadata"]
        metadata["filename"] = filename
        metadata["pages"] = page_count
        
        # Count tokens
        token_count = len(self.tokenizer.encode(content))
        metadata["token_count"] = token_count
        
        # Determine size class
        size_class = "small" if token_count < self.settings.small_doc_threshold_tokens else "large"
        
        result = {
            "content": content,
            "metadata": metadata,
            "size_class": size_class,
            "chunks": None
        }
        
        # Chunk large documents
        if size_class == "large":
            result["chunks"] = await self._create_contextual_chunks(content, filename)
        
        return result
    
    async def process_image(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str
    ) -> dict:
        """Process image files (PNG, JPG, etc.)."""
        import base64
        from google.genai import types
        
        prompt = """
        Extract ALL text and content from this image.
        
        If this is a document scan:
        - Convert to clean Markdown
        - Preserve structure and formatting
        
        If this is a diagram/chart:
        - Describe the visual elements
        - Extract any text labels
        - Explain the relationships shown
        
        Output the content in Markdown format.
        """
        
        response = await self.gemini.client.aio.models.generate_content(
            model=self.gemini.model,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                types.Part.from_text(text=prompt)
            ],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="medium")
            )
        )
        
        content = response.text
        token_count = len(self.tokenizer.encode(content))
        
        return {
            "content": content,
            "metadata": {
                "filename": filename,
                "mime_type": mime_type,
                "token_count": token_count
            },
            "size_class": "small",  # Images are typically small
            "chunks": None
        }
    
    async def _create_contextual_chunks(
        self,
        content: str,
        filename: str
    ) -> list[dict]:
        """
        Create semantically meaningful chunks with context metadata.
        Uses Gemini to identify natural boundaries.
        """
        # First, get suggested chunk boundaries from Gemini
        intelligence = await self.gemini.extract_document_intelligence(content, filename)
        
        suggested_boundaries = intelligence.get("suggested_chunk_boundaries", [])
        
        if suggested_boundaries:
            # Use AI-suggested boundaries
            chunks = self._split_by_boundaries(content, suggested_boundaries)
        else:
            # Fall back to semantic splitting
            chunks = self._semantic_split(content)
        
        # Enrich each chunk with context
        enriched_chunks = []
        for i, chunk in enumerate(chunks):
            enriched_chunks.append({
                "chunk_id": f"c{i+1}",
                "position": f"{i+1}/{len(chunks)}",
                "content": chunk["content"],
                "section": chunk.get("section", f"Section {i+1}"),
                "context": self._generate_chunk_context(chunk, chunks, i),
                "token_count": len(self.tokenizer.encode(chunk["content"]))
            })
        
        return enriched_chunks
    
    def _split_by_boundaries(
        self,
        content: str,
        boundaries: list[dict]
    ) -> list[dict]:
        """Split content using AI-suggested boundaries."""
        chunks = []
        current_pos = 0
        
        for boundary in boundaries:
            start_marker = boundary.get("start_marker", "")
            end_marker = boundary.get("end_marker", "")
            topic = boundary.get("topic", "")
            
            # Find markers in content
            start_idx = content.find(start_marker, current_pos)
            if start_idx == -1:
                continue
            
            end_idx = content.find(end_marker, start_idx + len(start_marker))
            if end_idx == -1:
                end_idx = len(content)
            
            chunk_content = content[start_idx:end_idx]
            if chunk_content.strip():
                chunks.append({
                    "content": chunk_content,
                    "section": topic
                })
            
            current_pos = end_idx
        
        # Get any remaining content
        if current_pos < len(content):
            remaining = content[current_pos:].strip()
            if remaining:
                chunks.append({
                    "content": remaining,
                    "section": "Remainder"
                })
        
        return chunks if chunks else self._semantic_split(content)
    
    def _semantic_split(self, content: str) -> list[dict]:
        """Fall back to semantic splitting by headers/sections."""
        import re
        
        # Split on major headers
        header_pattern = r'\n(#{1,3}\s+.+)\n'
        parts = re.split(header_pattern, content)
        
        chunks = []
        current_section = "Introduction"
        current_content = ""
        
        settings = get_settings()
        max_tokens = settings.chunk_size_tokens
        
        for part in parts:
            if re.match(r'^#{1,3}\s+', part):
                # This is a header
                if current_content.strip():
                    # Save previous chunk if it has content
                    chunks.append({
                        "content": current_content.strip(),
                        "section": current_section
                    })
                current_section = part.strip('# \n')
                current_content = part + "\n"
            else:
                # This is content
                test_content = current_content + part
                test_tokens = len(self.tokenizer.encode(test_content))
                
                if test_tokens > max_tokens and current_content.strip():
                    # Save current chunk and start new one
                    chunks.append({
                        "content": current_content.strip(),
                        "section": current_section
                    })
                    current_content = part
                else:
                    current_content = test_content
        
        # Don't forget the last chunk
        if current_content.strip():
            chunks.append({
                "content": current_content.strip(),
                "section": current_section
            })
        
        return chunks
    
    def _generate_chunk_context(
        self,
        chunk: dict,
        all_chunks: list[dict],
        index: int
    ) -> str:
        """Generate context string for a chunk."""
        parts = [f"This is section '{chunk.get('section', 'Unknown')}' of the document."]
        
        if index > 0:
            prev = all_chunks[index - 1]
            parts.append(f"Previous section: '{prev.get('section', 'Unknown')}'")
        
        if index < len(all_chunks) - 1:
            next_chunk = all_chunks[index + 1]
            parts.append(f"Next section: '{next_chunk.get('section', 'Unknown')}'")
        
        return " ".join(parts)


# Factory function
def get_ocr_processor() -> OCRProcessor:
    return OCRProcessor()
```

### backend/app/core/document_map.py

```python
"""
Living Document Map management.
The map is the core of one-shot retrieval - it's an LLM-maintained index.
"""
import json
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentMap as DocumentMapModel
from app.core.gemini_client import get_gemini_client


class DocumentMapManager:
    """Manages the living document map."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.gemini = get_gemini_client()
    
    async def get_map(self, workspace_id: str = "default") -> dict:
        """Get current document map for workspace."""
        result = await self.db.execute(
            select(DocumentMapModel).where(DocumentMapModel.workspace_id == workspace_id)
        )
        map_record = result.scalar_one_or_none()
        
        if map_record:
            return json.loads(map_record.map_data)
        
        # Return empty map structure
        return {
            "corpus_id": workspace_id,
            "last_updated": datetime.utcnow().isoformat(),
            "corpus_summary": "",
            "documents": [],
            "cross_references": {
                "by_entity": {},
                "by_topic": {}
            }
        }
    
    async def add_document(
        self,
        workspace_id: str,
        document_id: str,
        filename: str,
        content: str,
        size_class: str,
        chunks: Optional[list[dict]] = None
    ) -> dict:
        """
        Add document to map with full intelligence extraction.
        
        1. Extract document intelligence via Gemini
        2. Identify relationships to existing documents
        3. Update cross-references
        4. Update corpus summary
        """
        # Get current map
        current_map = await self.get_map(workspace_id)
        
        # Extract intelligence from new document
        intelligence = await self.gemini.extract_document_intelligence(content, filename)
        
        # Build document entry
        doc_entry = {
            "id": document_id,
            "filename": filename,
            "type": intelligence.get("document_type", "other"),
            "size_class": size_class,
            "essence": intelligence["essence"],
            "topics": intelligence["topics"],
            "entities": intelligence["entities"],
            "retrieval_hints": intelligence["retrieval_hints"],
            "added_at": datetime.utcnow().isoformat(),
            "relationships": []
        }
        
        # Add chunks if large document
        if chunks:
            doc_entry["chunks"] = [
                {
                    "chunk_id": f"{document_id}_{c['chunk_id']}",
                    "section": c["section"],
                    "context": c["context"],
                    "retrieval_hints": f"Part of {filename}: {c['section']}"
                }
                for c in chunks
            ]
        
        # If we have existing documents, find relationships
        if current_map["documents"]:
            map_updates = await self.gemini.update_document_map(current_map, doc_entry)
            
            # Add relationships
            doc_entry["relationships"] = map_updates.get("relationships", [])
            
            # Merge cross-references
            new_refs = map_updates.get("new_cross_references", {})
            self._merge_cross_references(current_map["cross_references"], new_refs)
            
            # Update corpus summary
            current_map["corpus_summary"] = map_updates.get(
                "updated_corpus_summary",
                current_map["corpus_summary"]
            )
        else:
            # First document - create initial summary
            current_map["corpus_summary"] = f"Corpus containing: {filename}. {intelligence['essence']}"
            
            # Initialize cross-references
            for entity_type, entities in intelligence["entities"].items():
                for entity in entities:
                    if entity not in current_map["cross_references"]["by_entity"]:
                        current_map["cross_references"]["by_entity"][entity] = []
                    current_map["cross_references"]["by_entity"][entity].append(document_id)
            
            for topic in intelligence["topics"]:
                if topic not in current_map["cross_references"]["by_topic"]:
                    current_map["cross_references"]["by_topic"][topic] = []
                current_map["cross_references"]["by_topic"][topic].append(document_id)
        
        # Add document to map
        current_map["documents"].append(doc_entry)
        current_map["last_updated"] = datetime.utcnow().isoformat()
        
        # Persist map
        await self._save_map(workspace_id, current_map)
        
        return doc_entry
    
    async def remove_document(self, workspace_id: str, document_id: str) -> bool:
        """Remove document from map and update cross-references."""
        current_map = await self.get_map(workspace_id)
        
        # Find and remove document
        doc_to_remove = None
        for i, doc in enumerate(current_map["documents"]):
            if doc["id"] == document_id:
                doc_to_remove = current_map["documents"].pop(i)
                break
        
        if not doc_to_remove:
            return False
        
        # Clean cross-references
        for entity, doc_ids in current_map["cross_references"]["by_entity"].items():
            if document_id in doc_ids:
                doc_ids.remove(document_id)
        
        for topic, doc_ids in current_map["cross_references"]["by_topic"].items():
            if document_id in doc_ids:
                doc_ids.remove(document_id)
        
        # Remove empty entries
        current_map["cross_references"]["by_entity"] = {
            k: v for k, v in current_map["cross_references"]["by_entity"].items() if v
        }
        current_map["cross_references"]["by_topic"] = {
            k: v for k, v in current_map["cross_references"]["by_topic"].items() if v
        }
        
        # Update timestamp
        current_map["last_updated"] = datetime.utcnow().isoformat()
        
        # Persist
        await self._save_map(workspace_id, current_map)
        
        return True
    
    def _merge_cross_references(self, existing: dict, new: dict) -> None:
        """Merge new cross-references into existing."""
        for ref_type in ["by_entity", "by_topic"]:
            if ref_type in new:
                for key, doc_ids in new[ref_type].items():
                    if key not in existing[ref_type]:
                        existing[ref_type][key] = []
                    existing[ref_type][key].extend(doc_ids)
                    # Deduplicate
                    existing[ref_type][key] = list(set(existing[ref_type][key]))
    
    async def _save_map(self, workspace_id: str, map_data: dict) -> None:
        """Persist document map to database."""
        result = await self.db.execute(
            select(DocumentMapModel).where(DocumentMapModel.workspace_id == workspace_id)
        )
        map_record = result.scalar_one_or_none()
        
        if map_record:
            map_record.map_data = json.dumps(map_data)
            map_record.updated_at = datetime.utcnow()
        else:
            map_record = DocumentMapModel(
                workspace_id=workspace_id,
                map_data=json.dumps(map_data)
            )
            self.db.add(map_record)
        
        await self.db.commit()
```

### backend/app/core/retriever.py

```python
"""
One-shot retrieval system using document map.
No re-ranking required - the LLM makes intelligent retrieval decisions.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.gemini_client import get_gemini_client
from app.core.document_map import DocumentMapManager
from app.db.models import Document, DocumentChunk


class IntelligentRetriever:
    """One-shot retrieval using document map consultation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.gemini = get_gemini_client()
        self.map_manager = DocumentMapManager(db)
    
    async def retrieve(
        self,
        query: str,
        workspace_id: str = "default",
        max_documents: int = 5
    ) -> list[dict]:
        """
        Retrieve relevant documents/chunks for query.
        
        1. Get document map
        2. Consult Gemini for retrieval decision (one-shot)
        3. Fetch selected documents/chunks
        4. Return with context metadata
        """
        # Get document map
        document_map = await self.map_manager.get_map(workspace_id)
        
        if not document_map["documents"]:
            return []
        
        # Consult map for retrieval decision
        retrieval_decision = await self.gemini.consult_map_for_retrieval(
            query, document_map
        )
        
        doc_ids_to_retrieve = retrieval_decision.get("retrieve", [])[:max_documents]
        
        if not doc_ids_to_retrieve:
            return []
        
        # Fetch documents and chunks
        retrieved_content = []
        
        for doc_ref in doc_ids_to_retrieve:
            if "_c" in doc_ref:
                # This is a chunk reference (e.g., "doc_123_c2")
                parts = doc_ref.rsplit("_c", 1)
                doc_id = parts[0]
                chunk_num = int(parts[1])
                
                content = await self._fetch_chunk(doc_id, chunk_num, document_map)
            else:
                # Full document
                content = await self._fetch_document(doc_ref, document_map)
            
            if content:
                retrieved_content.append(content)
        
        return retrieved_content
    
    async def _fetch_document(self, doc_id: str, document_map: dict) -> Optional[dict]:
        """Fetch full document content."""
        # Get from database
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            return None
        
        # Get map entry for context
        map_entry = next(
            (d for d in document_map["documents"] if d["id"] == doc_id),
            None
        )
        
        return {
            "id": doc_id,
            "content": doc.content,
            "context": f"Document: {doc.filename}. {map_entry['essence'] if map_entry else ''}"
        }
    
    async def _fetch_chunk(
        self,
        doc_id: str,
        chunk_num: int,
        document_map: dict
    ) -> Optional[dict]:
        """Fetch specific chunk with context."""
        chunk_id = f"{doc_id}_c{chunk_num}"
        
        result = await self.db.execute(
            select(DocumentChunk).where(DocumentChunk.chunk_id == chunk_id)
        )
        chunk = result.scalar_one_or_none()
        
        if not chunk:
            return None
        
        # Get map entry for context
        map_entry = next(
            (d for d in document_map["documents"] if d["id"] == doc_id),
            None
        )
        
        chunk_map_entry = None
        if map_entry and map_entry.get("chunks"):
            chunk_map_entry = next(
                (c for c in map_entry["chunks"] if c["chunk_id"] == chunk_id),
                None
            )
        
        context_parts = [f"From document: {map_entry['filename'] if map_entry else doc_id}"]
        if chunk_map_entry:
            context_parts.append(f"Section: {chunk_map_entry.get('section', 'Unknown')}")
            context_parts.append(chunk_map_entry.get("context", ""))
        
        return {
            "id": chunk_id,
            "content": chunk.content,
            "context": " ".join(context_parts)
        }
```

### backend/app/db/models.py

```python
"""SQLAlchemy models for PostgreSQL."""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(50), primary_key=True)
    workspace_id = Column(String(50), default="default", index=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    size_class = Column(String(20), default="small")  # small or large
    token_count = Column(Integer, default=0)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(String(100), unique=True, index=True)  # e.g., "doc_123_c1"
    document_id = Column(String(50), ForeignKey("documents.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    section = Column(String(255))
    context = Column(Text)  # Contextual metadata
    position = Column(String(20))  # e.g., "3/12"
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")


class DocumentMap(Base):
    __tablename__ = "document_maps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(50), unique=True, index=True)
    map_data = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(50), index=True)
    session_id = Column(String(50), index=True)
    role = Column(String(20))  # user or assistant
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
```

### backend/app/db/postgres.py

```python
"""PostgreSQL database connection and session management."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db.models import Base

engine = None
async_session_maker = None


async def init_db():
    """Initialize database connection and create tables."""
    global engine, async_session_maker
    
    settings = get_settings()
    
    engine = create_async_engine(
        settings.postgres_url,
        echo=settings.environment == "development",
        pool_size=10,
        max_overflow=20
    )
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
```

### backend/app/db/weaviate.py

```python
"""
Weaviate client for hybrid search (fallback/augmentation).
While the document map handles primary retrieval, Weaviate provides
vector similarity for edge cases.
"""
import weaviate
from weaviate.classes.config import Configure, Property, DataType

from app.config import get_settings

client = None


async def init_weaviate():
    """Initialize Weaviate connection and schema."""
    global client
    
    settings = get_settings()
    
    client = weaviate.connect_to_custom(
        http_host=settings.weaviate_url.replace("http://", "").split(":")[0],
        http_port=8080,
        http_secure=False,
        grpc_host=settings.weaviate_url.replace("http://", "").split(":")[0],
        grpc_port=50051,
        grpc_secure=False
    )
    
    # Create schema if not exists
    try:
        if not client.collections.exists("DocumentChunk"):
            client.collections.create(
                name="DocumentChunk",
                properties=[
                    Property(name="chunk_id", data_type=DataType.TEXT),
                    Property(name="document_id", data_type=DataType.TEXT),
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="section", data_type=DataType.TEXT),
                    Property(name="workspace_id", data_type=DataType.TEXT),
                ],
                # Using none vectorizer - we'll add vectors from Gemini embeddings if needed
                vectorizer_config=Configure.Vectorizer.none()
            )
    except Exception as e:
        print(f"Weaviate schema setup: {e}")


def get_weaviate_client():
    """Get Weaviate client instance."""
    return client


async def store_chunk_vector(
    chunk_id: str,
    document_id: str,
    content: str,
    section: str,
    workspace_id: str,
    vector: list[float]
):
    """Store chunk with vector embedding."""
    collection = client.collections.get("DocumentChunk")
    
    collection.data.insert(
        properties={
            "chunk_id": chunk_id,
            "document_id": document_id,
            "content": content,
            "section": section,
            "workspace_id": workspace_id
        },
        vector=vector
    )


async def search_similar_chunks(
    query_vector: list[float],
    workspace_id: str,
    limit: int = 5
) -> list[dict]:
    """Search for similar chunks using vector similarity."""
    collection = client.collections.get("DocumentChunk")
    
    results = collection.query.near_vector(
        near_vector=query_vector,
        limit=limit,
        filters=weaviate.classes.query.Filter.by_property("workspace_id").equal(workspace_id)
    )
    
    return [
        {
            "chunk_id": obj.properties["chunk_id"],
            "document_id": obj.properties["document_id"],
            "content": obj.properties["content"],
            "section": obj.properties["section"],
            "score": obj.metadata.certainty
        }
        for obj in results.objects
    ]
```

### backend/app/api/routes/documents.py

```python
"""Document management API routes."""
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.postgres import get_db
from app.db.models import Document, DocumentChunk
from app.core.ocr_processor import get_ocr_processor
from app.core.document_map import DocumentMapManager
from app.schemas.document import DocumentResponse, DocumentListResponse

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and process a document.
    
    1. OCR extraction using Gemini 3 Flash
    2. Intelligence extraction for document map
    3. Chunking if large document
    4. Store in PostgreSQL
    5. Update document map
    """
    # Validate file type
    allowed_types = {
        "application/pdf": "pdf",
        "image/png": "image",
        "image/jpeg": "image",
        "image/jpg": "image",
        "image/webp": "image"
    }
    
    content_type = file.content_type
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}"
        )
    
    # Read file
    file_bytes = await file.read()
    
    # Generate document ID
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    # Process document
    ocr_processor = get_ocr_processor()
    
    if allowed_types[content_type] == "pdf":
        result = await ocr_processor.process_pdf(file_bytes, file.filename)
    else:
        result = await ocr_processor.process_image(file_bytes, file.filename, content_type)
    
    # Store document
    document = Document(
        id=doc_id,
        workspace_id=workspace_id,
        filename=file.filename,
        content=result["content"],
        size_class=result["size_class"],
        token_count=result["metadata"].get("token_count", 0),
        metadata=result["metadata"]
    )
    db.add(document)
    
    # Store chunks if large document
    if result["chunks"]:
        for chunk in result["chunks"]:
            db_chunk = DocumentChunk(
                chunk_id=f"{doc_id}_{chunk['chunk_id']}",
                document_id=doc_id,
                content=chunk["content"],
                section=chunk["section"],
                context=chunk["context"],
                position=chunk["position"],
                token_count=chunk["token_count"]
            )
            db.add(db_chunk)
    
    await db.commit()
    
    # Update document map
    map_manager = DocumentMapManager(db)
    doc_entry = await map_manager.add_document(
        workspace_id=workspace_id,
        document_id=doc_id,
        filename=file.filename,
        content=result["content"],
        size_class=result["size_class"],
        chunks=result["chunks"]
    )
    
    return DocumentResponse(
        id=doc_id,
        filename=file.filename,
        size_class=result["size_class"],
        token_count=result["metadata"].get("token_count", 0),
        chunk_count=len(result["chunks"]) if result["chunks"] else 0,
        essence=doc_entry["essence"],
        topics=doc_entry["topics"]
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """List all documents in workspace."""
    result = await db.execute(
        select(Document).where(Document.workspace_id == workspace_id)
    )
    documents = result.scalars().all()
    
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                size_class=doc.size_class,
                token_count=doc.token_count,
                chunk_count=len(doc.chunks) if doc.chunks else 0,
                essence=doc.metadata.get("essence", ""),
                topics=doc.metadata.get("topics", [])
            )
            for doc in documents
        ],
        total=len(documents)
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Delete a document and update map."""
    # Check if document exists
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == workspace_id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from database (chunks cascade)
    await db.execute(
        delete(Document).where(Document.id == document_id)
    )
    await db.commit()
    
    # Update document map
    map_manager = DocumentMapManager(db)
    await map_manager.remove_document(workspace_id, document_id)
    
    return {"status": "deleted", "document_id": document_id}
```

### backend/app/api/routes/chat.py

```python
"""Chat/Query API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.postgres import get_db
from app.db.models import ChatHistory
from app.core.gemini_client import get_gemini_client
from app.core.retriever import IntelligentRetriever
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryResponse

router = APIRouter()


@router.post("/query", response_model=ChatResponse)
async def query_documents(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Query documents using intelligent retrieval.
    
    1. Retrieve relevant documents via map consultation
    2. Generate answer using Gemini 3 Flash
    3. Store in chat history
    """
    gemini = get_gemini_client()
    retriever = IntelligentRetriever(db)
    
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
    
    # Retrieve relevant content
    retrieved = await retriever.retrieve(
        query=request.query,
        workspace_id=request.workspace_id,
        max_documents=request.max_documents or 5
    )
    
    if not retrieved:
        return ChatResponse(
            answer="I couldn't find any relevant documents to answer your question. Please upload some documents first.",
            citations=[],
            confidence=0.0,
            retrieved_docs=[]
        )
    
    # Generate answer
    answer_result = await gemini.generate_answer(
        query=request.query,
        retrieved_content=retrieved,
        chat_history=chat_history
    )
    
    # Generate session ID if not provided
    session_id = request.session_id or f"session_{uuid.uuid4().hex[:12]}"
    
    # Store user message
    user_msg = ChatHistory(
        workspace_id=request.workspace_id,
        session_id=session_id,
        role="user",
        content=request.query
    )
    db.add(user_msg)
    
    # Store assistant response
    assistant_msg = ChatHistory(
        workspace_id=request.workspace_id,
        session_id=session_id,
        role="assistant",
        content=answer_result["answer"],
        citations=answer_result.get("citations", [])
    )
    db.add(assistant_msg)
    
    await db.commit()
    
    return ChatResponse(
        answer=answer_result["answer"],
        citations=answer_result.get("citations", []),
        confidence=answer_result.get("confidence", 0.5),
        retrieved_docs=[r["id"] for r in retrieved],
        session_id=session_id
    )


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for a session."""
    result = await db.execute(
        select(ChatHistory)
        .where(
            ChatHistory.session_id == session_id,
            ChatHistory.workspace_id == workspace_id
        )
        .order_by(ChatHistory.created_at.asc())
    )
    messages = result.scalars().all()
    
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            {
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "timestamp": m.created_at.isoformat()
            }
            for m in messages
        ]
    )


@router.delete("/history/{session_id}")
async def clear_chat_history(
    session_id: str,
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Clear chat history for a session."""
    from sqlalchemy import delete
    
    await db.execute(
        delete(ChatHistory).where(
            ChatHistory.session_id == session_id,
            ChatHistory.workspace_id == workspace_id
        )
    )
    await db.commit()
    
    return {"status": "cleared", "session_id": session_id}
```

### backend/app/api/routes/health.py

```python
"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """Readiness check with dependency status."""
    # Add actual checks here
    return {
        "status": "ready",
        "dependencies": {
            "postgres": "ok",
            "weaviate": "ok",
            "gemini": "ok"
        }
    }
```

### backend/app/schemas/document.py

```python
"""Pydantic schemas for documents."""
from pydantic import BaseModel
from typing import Optional


class DocumentResponse(BaseModel):
    id: str
    filename: str
    size_class: str
    token_count: int
    chunk_count: int
    essence: str = ""
    topics: list[str] = []


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
```

### backend/app/schemas/chat.py

```python
"""Pydantic schemas for chat."""
from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    query: str
    workspace_id: str = "default"
    session_id: Optional[str] = None
    max_documents: Optional[int] = 5


class Citation(BaseModel):
    doc_id: str
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict]
    confidence: float
    retrieved_docs: list[str]
    session_id: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[dict]
```

---

## Part 4: Frontend Implementation

### frontend/Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### frontend/requirements.txt

```
streamlit==1.41.1
httpx==0.28.1
python-dotenv==1.0.1
```

### frontend/app.py

```python
"""
Streamlit UI for Intelligent RAG System.
Modern dark-themed interface for document management and chat.
"""
import streamlit as st
import httpx
import os
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="Intelligent RAG",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark theme CSS
st.markdown("""
<style>
    /* Main dark theme */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1a1d24;
        border-right: 1px solid #2d3139;
    }
    
    /* Chat message styling */
    .user-message {
        background-color: #1e3a5f;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 3px solid #4a9eff;
    }
    
    .assistant-message {
        background-color: #1a1d24;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 3px solid #10b981;
    }
    
    /* Document card styling */
    .doc-card {
        background-color: #1a1d24;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 1px solid #2d3139;
        transition: border-color 0.2s;
    }
    
    .doc-card:hover {
        border-color: #4a9eff;
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        background-color: #1a1d24;
        border: 1px solid #2d3139;
        color: #fff;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #4a9eff;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        transition: background-color 0.2s;
    }
    
    .stButton > button:hover {
        background-color: #3a8eef;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #1a1d24;
        border: 2px dashed #2d3139;
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #fff;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #4a9eff;
    }
    
    /* Citation badge */
    .citation-badge {
        background-color: #2d3139;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        color: #9ca3af;
    }
    
    /* Confidence indicator */
    .confidence-high { color: #10b981; }
    .confidence-medium { color: #f59e0b; }
    .confidence-low { color: #ef4444; }
</style>
""", unsafe_allow_html=True)


# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "documents" not in st.session_state:
    st.session_state.documents = []


def api_request(method: str, endpoint: str, **kwargs):
    """Make API request to backend."""
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.request(method, f"{BACKEND_URL}{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"API Error: {str(e)}")
        return None


def load_documents():
    """Load documents from backend."""
    result = api_request("GET", "/api/documents/")
    if result:
        st.session_state.documents = result.get("documents", [])


def upload_document(file):
    """Upload document to backend."""
    files = {"file": (file.name, file.getvalue(), file.type)}
    result = api_request("POST", "/api/documents/upload", files=files)
    if result:
        st.success(f"✅ Uploaded: {result['filename']}")
        load_documents()
        return result
    return None


def delete_document(doc_id: str):
    """Delete document from backend."""
    result = api_request("DELETE", f"/api/documents/{doc_id}")
    if result:
        st.success("🗑️ Document deleted")
        load_documents()


def send_message(query: str):
    """Send query to backend."""
    payload = {
        "query": query,
        "workspace_id": "default",
        "session_id": st.session_state.session_id
    }
    result = api_request("POST", "/api/chat/query", json=payload)
    if result:
        st.session_state.session_id = result.get("session_id")
        return result
    return None


# Sidebar - Document Management
with st.sidebar:
    st.markdown("## 📁 Documents")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload Document",
        type=["pdf", "png", "jpg", "jpeg", "webp"],
        help="Supported: PDF, PNG, JPG, WEBP"
    )
    
    if uploaded_file:
        if st.button("📤 Process Document", use_container_width=True):
            with st.spinner("Processing with Gemini 3 Flash..."):
                result = upload_document(uploaded_file)
                if result:
                    st.markdown(f"""
                    **Size:** {result['size_class']}  
                    **Tokens:** {result['token_count']:,}  
                    **Chunks:** {result['chunk_count']}
                    """)
    
    st.divider()
    
    # Document list
    st.markdown("### 📚 Your Documents")
    
    if st.button("🔄 Refresh", use_container_width=True):
        load_documents()
    
    # Load documents on first run
    if not st.session_state.documents:
        load_documents()
    
    if st.session_state.documents:
        for doc in st.session_state.documents:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"""
                    <div class="doc-card">
                        <strong>{doc['filename'][:25]}{'...' if len(doc['filename']) > 25 else ''}</strong><br>
                        <small>📊 {doc['token_count']:,} tokens | 
                        {'📦 ' + str(doc['chunk_count']) + ' chunks' if doc['chunk_count'] > 0 else '📄 Full doc'}</small>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("🗑️", key=f"del_{doc['id']}", help="Delete"):
                        delete_document(doc['id'])
                        st.rerun()
    else:
        st.info("No documents uploaded yet")
    
    st.divider()
    
    # Session controls
    st.markdown("### 💬 Chat Session")
    if st.button("🆕 New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.rerun()


# Main content - Chat Interface
st.markdown("# 🧠 Intelligent RAG Chat")
st.markdown("*Powered by Gemini 3 Flash with one-shot retrieval*")

# Stats row
if st.session_state.documents:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Documents", len(st.session_state.documents))
    with col2:
        total_tokens = sum(d['token_count'] for d in st.session_state.documents)
        st.metric("Total Tokens", f"{total_tokens:,}")
    with col3:
        chunked = sum(1 for d in st.session_state.documents if d['chunk_count'] > 0)
        st.metric("Chunked Docs", chunked)

st.divider()

# Chat messages
chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="user-message">
                <strong>👤 You</strong><br>
                {msg["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:
            confidence = msg.get("confidence", 0.5)
            conf_class = "confidence-high" if confidence > 0.7 else "confidence-medium" if confidence > 0.4 else "confidence-low"
            
            citations_html = ""
            if msg.get("citations"):
                citations_html = "<br><small>📎 Sources: " + ", ".join(
                    f"<span class='citation-badge'>{c['doc_id']}</span>"
                    for c in msg["citations"]
                ) + "</small>"
            
            st.markdown(f"""
            <div class="assistant-message">
                <strong>🤖 Assistant</strong> 
                <span class="{conf_class}">({confidence:.0%} confident)</span><br>
                {msg["content"]}
                {citations_html}
            </div>
            """, unsafe_allow_html=True)

# Chat input
st.divider()

query = st.chat_input("Ask a question about your documents...")

if query:
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": query
    })
    
    # Get response
    with st.spinner("🔍 Retrieving and generating..."):
        response = send_message(query)
        
        if response:
            st.session_state.messages.append({
                "role": "assistant",
                "content": response["answer"],
                "citations": response.get("citations", []),
                "confidence": response.get("confidence", 0.5),
                "retrieved_docs": response.get("retrieved_docs", [])
            })
    
    st.rerun()

# Empty state
if not st.session_state.messages and not st.session_state.documents:
    st.markdown("""
    <div style="text-align: center; padding: 3rem; color: #6b7280;">
        <h3>👋 Welcome to Intelligent RAG</h3>
        <p>Upload documents using the sidebar to get started.</p>
        <p>Supported formats: PDF, PNG, JPG, WEBP</p>
        <br>
        <p><strong>Features:</strong></p>
        <ul style="list-style: none; padding: 0;">
            <li>🔍 One-shot retrieval (no re-ranking)</li>
            <li>📄 Small docs retrieved whole</li>
            <li>📦 Large docs contextually chunked</li>
            <li>🗺️ Living document map</li>
            <li>⚡ Powered by Gemini 3 Flash</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
elif not st.session_state.messages and st.session_state.documents:
    st.markdown("""
    <div style="text-align: center; padding: 3rem; color: #6b7280;">
        <h3>📚 Documents Ready</h3>
        <p>Ask a question about your documents below.</p>
    </div>
    """, unsafe_allow_html=True)
```

---

## Part 5: Database Initialization

### scripts/init_db.sql

```sql
-- PostgreSQL initialization script
-- Tables are created by SQLAlchemy, this handles extensions and permissions

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better query performance
-- (Applied after SQLAlchemy creates tables)

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO raguser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO raguser;
```

---

## Part 6: Running the System

### Quick Start

```bash
# 1. Clone and setup
cd intelligent-rag
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 2. Start all services
docker-compose up -d

# 3. Access the UI
# Open http://localhost:8501 in your browser

# 4. API documentation
# Open http://localhost:8000/docs for Swagger UI
```

### Development Mode

```bash
# Run with live reload
docker-compose up --build

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart specific service
docker-compose restart backend
```

### Health Checks

```bash
# Check all services
curl http://localhost:8000/health
curl http://localhost:8080/v1/.well-known/ready  # Weaviate
```

---

## Part 7: API Reference

### Documents API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload` | Upload and process document |
| GET | `/api/documents/` | List all documents |
| DELETE | `/api/documents/{id}` | Delete document |

### Chat API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/query` | Query documents |
| GET | `/api/chat/history/{session_id}` | Get chat history |
| DELETE | `/api/chat/history/{session_id}` | Clear chat history |

---

## Part 8: Key Design Decisions

### 1. Small Document Full Retrieval
Documents under 50K tokens (~35 pages) are stored whole and retrieved without chunking. This preserves context and eliminates chunking artifacts.

### 2. Contextual Chunking for Large Documents
Large documents are split using:
- AI-suggested semantic boundaries (preferred)
- Header-based splitting (fallback)
Each chunk includes metadata about its position and surrounding context.

### 3. Living Document Map
Instead of relying solely on embeddings, we maintain a structured index with:
- Document essences (summaries)
- Topics and entities
- Retrieval hints
- Cross-references

### 4. One-Shot Retrieval
The document map is consulted via a single Gemini call to select which documents/chunks to retrieve. No embedding similarity search or re-ranking required.

### 5. Unified Gemini Client
A single client handles OCR, extraction, retrieval decisions, and answer generation. This simplifies code and enables consistent thinking level control.

---

## Part 9: Future Enhancements

1. **Hybrid Search**: Add Weaviate vector fallback for edge cases
2. **Context Caching**: Implement Gemini's context caching for 90% cost savings
3. **Batch Processing**: Use Batch API for bulk document ingestion
4. **Multi-workspace**: Full workspace isolation and sharing
5. **Authentication**: Add user authentication and authorization
6. **Streaming**: Stream chat responses for better UX
7. **Export**: Export chat history and document map

---

## Part 10: Future Enhancement — Web Search Enrichment

### Concept Overview

Extend document upload with Gemini's built-in web search tool to automatically enrich documents with publicly available context. When users flag a document as "public-enrichable," the system fetches real-time web data to fill knowledge gaps, add current context, and cross-reference claims.

### Use Cases

- **Financial Reports**: Enrich with current stock prices, market news, competitor data
- **Legal Contracts**: Add context about involved parties, regulatory updates, case precedents
- **Technical Documentation**: Link to latest API versions, deprecation notices, security advisories
- **Research Papers**: Cross-reference citations, add recent publications on the topic
- **Company Profiles**: Supplement with latest news, executive changes, funding rounds

### Architecture Extension

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENRICHED DOCUMENT UPLOAD FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌─────────────┐
     │  Document   │
     │  Upload     │
     │  + flags    │◄─── User selects: ☑️ Enrich with web data
     └──────┬──────┘     └── Optional: enrichment focus/context
            │
            ▼
┌───────────────────────┐
│  1. OCR + EXTRACTION  │  (existing flow)
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  2. GAP ANALYSIS      │  Gemini identifies:
│                       │  • Entities needing context (companies, people, dates)
│                       │  • Claims that could be verified
│                       │  • References to external events/data
│                       │  • Outdated information indicators
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  3. WEB SEARCH QUERIES│  Generate targeted searches:
│     (Gemini Tool)     │  • "[Company] latest news 2025"
│                       │  • "[Person] current role"
│                       │  • "[Topic] recent developments"
│                       │  • "[Claim] fact check"
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  4. ENRICHMENT LAYER  │  Structured additions:
│                       │  • Entity profiles (current state)
│                       │  • Temporal context (what happened since)
│                       │  • Verification notes (confirmed/disputed)
│                       │  • Related developments
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  5. ENRICHED DOC MAP  │  Extended metadata:
│                       │  • enrichment_data: {...}
│                       │  • enriched_at: timestamp
│                       │  • sources: [web URLs]
│                       │  • confidence_notes: [...]
└───────────────────────┘
```

### Implementation Approach

#### 1. Upload API Extension

```python
class EnrichmentConfig(BaseModel):
    enabled: bool = False
    focus_areas: list[str] = []  # e.g., ["company_info", "market_data", "news"]
    context_hint: str = ""       # User-provided context
    max_searches: int = 5        # Rate limit searches
    freshness: str = "month"     # How recent: day, week, month, year
```

#### 2. Gap Analysis Prompt

```python
GAP_ANALYSIS_PROMPT = """
Analyze this document and identify information gaps that could be enriched 
with public web data.

Document: {content}
User context hint: {context_hint}

Identify:
1. **Entities requiring context**: Companies, people, products mentioned 
   without sufficient background
2. **Temporal gaps**: Dates/events where "what happened next" would help
3. **Verifiable claims**: Statements that could be fact-checked
4. **External references**: Mentions of reports, studies, news events
5. **Market/industry context**: Where broader context would aid understanding

Output as JSON:
{
    "search_queries": [
        {"query": "...", "purpose": "...", "priority": 1-5}
    ],
    "entities_to_enrich": [
        {"name": "...", "type": "company|person|product|event", "current_info_needed": "..."}
    ],
    "verification_targets": [
        {"claim": "...", "search_approach": "..."}
    ]
}
"""
```

#### 3. Web Search Integration

```python
async def enrich_with_web_search(
    document_content: str,
    config: EnrichmentConfig
) -> dict:
    """Use Gemini's web search tool to enrich document."""
    
    # Step 1: Analyze gaps
    gaps = await gemini.generate_content(
        model="gemini-3-flash-preview",
        contents=[GAP_ANALYSIS_PROMPT.format(
            content=document_content[:50000],
            context_hint=config.context_hint
        )],
        config=GenerateContentConfig(
            thinking_config=ThinkingConfig(thinking_level="medium")
        )
    )
    
    # Step 2: Execute searches with Gemini's web search tool
    search_queries = gaps["search_queries"][:config.max_searches]
    
    enrichments = []
    for sq in search_queries:
        result = await gemini.generate_content(
            model="gemini-3-flash-preview",
            contents=[f"Search and summarize: {sq['query']}"],
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            config=GenerateContentConfig(
                thinking_config=ThinkingConfig(thinking_level="low")
            )
        )
        enrichments.append({
            "query": sq["query"],
            "purpose": sq["purpose"],
            "result": result.text,
            "sources": extract_sources(result)
        })
    
    # Step 3: Synthesize enrichment layer
    synthesis = await gemini.generate_content(
        model="gemini-3-flash-preview",
        contents=[SYNTHESIS_PROMPT.format(
            original_doc=document_content[:30000],
            enrichments=json.dumps(enrichments)
        )]
    )
    
    return {
        "enrichment_data": synthesis,
        "searches_performed": len(enrichments),
        "sources": [e["sources"] for e in enrichments],
        "enriched_at": datetime.utcnow().isoformat()
    }
```

#### 4. Enriched Document Map Entry

```python
# Extended document map entry
{
    "id": "doc_001",
    "filename": "Q3_Earnings_2025.pdf",
    "essence": "...",
    "topics": [...],
    
    # NEW: Enrichment layer
    "enrichment": {
        "enabled": True,
        "enriched_at": "2025-12-20T15:30:00Z",
        "freshness": "month",
        
        "entity_context": {
            "Acme Corp": {
                "current_stock_price": "$142.50",
                "recent_news": "Announced AI partnership with TechGiant",
                "market_cap": "$45B",
                "source": "https://finance.example.com/acme"
            },
            "Jane Smith (CFO)": {
                "current_role": "Still CFO as of Dec 2025",
                "recent_mentions": "Spoke at FinTech Summit",
                "source": "https://news.example.com/..."
            }
        },
        
        "temporal_updates": [
            {
                "original_reference": "Q4 guidance raised",
                "update": "Q4 results exceeded raised guidance by 8%",
                "date": "2025-11-15",
                "source": "..."
            }
        ],
        
        "verification_notes": [
            {
                "claim": "12% YoY revenue growth",
                "status": "verified",
                "source": "SEC filing 10-Q"
            }
        ],
        
        "related_context": [
            "Industry-wide semiconductor shortage eased in Q4 2025",
            "APAC market grew 15% overall in 2025"
        ],
        
        "sources": [
            {"url": "...", "accessed": "...", "reliability": "high"}
        ]
    }
}
```

#### 5. Enhanced Retrieval with Enrichments

```python
async def retrieve_with_enrichment(query: str, document_map: dict) -> list[dict]:
    """Retrieve documents and include relevant enrichment data."""
    
    # Standard retrieval
    base_retrieval = await retriever.retrieve(query, document_map)
    
    # Enhance with enrichment data where relevant
    enhanced = []
    for doc in base_retrieval:
        doc_entry = get_map_entry(doc["id"], document_map)
        
        if doc_entry.get("enrichment", {}).get("enabled"):
            # Check if query relates to enriched entities
            relevant_enrichments = filter_relevant_enrichments(
                query, 
                doc_entry["enrichment"]
            )
            
            if relevant_enrichments:
                doc["enrichment_context"] = relevant_enrichments
        
        enhanced.append(doc)
    
    return enhanced
```

### UI Extension

```python
# Streamlit upload component extension
with st.expander("🌐 Web Enrichment Options"):
    enrich_enabled = st.checkbox(
        "Enrich with public web data",
        help="Search the web for additional context about entities and claims"
    )
    
    if enrich_enabled:
        focus_areas = st.multiselect(
            "Focus areas",
            ["Company information", "Market data", "Recent news", 
             "People/executives", "Technical updates", "Regulatory context"]
        )
        
        context_hint = st.text_area(
            "Context hint (optional)",
            placeholder="E.g., 'This is a competitor analysis for our Q1 planning'"
        )
        
        freshness = st.select_slider(
            "Data freshness",
            options=["day", "week", "month", "quarter", "year"],
            value="month"
        )
```

### Key Considerations

#### Privacy & Security
- Only enrich documents explicitly flagged by user
- Never send sensitive/confidential document content to web search
- Implement content classification to detect PII/confidential markers
- Log all enrichment searches for audit trail
- Option to use anonymized/redacted queries

#### Cost Management
- Rate limit searches per document (default: 5)
- Cache enrichment results (TTL based on freshness setting)
- Batch enrichment for multiple related documents
- Offer "quick enrich" (2 searches) vs "deep enrich" (10+ searches) tiers

#### Data Quality
- Track source reliability scores
- Timestamp all enrichments for staleness detection
- Allow users to mark enrichments as incorrect
- Re-enrich option for outdated data
- Distinguish between verified facts and web claims

#### Refresh Strategy
- Scheduled re-enrichment for active documents
- Event-triggered refresh (e.g., earnings announcements)
- User-requested refresh
- Staleness indicators in UI

### Benefits

| Without Enrichment | With Enrichment |
|--------------------|-----------------|
| "Revenue grew 12%" | "Revenue grew 12% (verified via SEC 10-Q), outpacing industry average of 8%" |
| "CEO John Doe announced..." | "CEO John Doe (appointed 2023, previously at TechCorp) announced..." |
| "Q4 guidance raised" | "Q4 guidance raised; actual Q4 results exceeded guidance by 8%" |
| "Competitor analysis" | "Competitor X: current market cap $20B, recent acquisition of Y" |

### Implementation Priority

1. **Phase 1**: Basic entity enrichment (companies, people)
2. **Phase 2**: Temporal updates and fact verification
3. **Phase 3**: Industry/market context
4. **Phase 4**: Automated refresh and staleness management
5. **Phase 5**: Cross-document enrichment correlation

---

*Generated for Claude Code implementation*
*December 2025*
