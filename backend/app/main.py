"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.api.routes import health, documents, chat, agentic_chat
from app.ocr import ocr_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    settings = get_settings()

    # Import here to avoid circular imports
    from app.db.postgres import init_db
    from app.db.weaviate import init_weaviate

    # Initialize databases if configured (optional)
    if settings.postgres_url:
        try:
            await init_db()
            print("[OK] PostgreSQL connected")
        except Exception as e:
            print(f"[WARN] PostgreSQL unavailable: {e}")
    else:
        print("[WARN] PostgreSQL not configured (POSTGRES_URL not set)")

    if settings.weaviate_url:
        try:
            await init_weaviate()
            print("[OK] Weaviate connected")
        except Exception as e:
            print(f"[WARN] Weaviate unavailable: {e}")
    else:
        print("[WARN] Weaviate not configured")

    yield

    # Shutdown
    pass


app = FastAPI(
    title="Intelligent RAG API",
    description="""
    Document intelligence with two RAG modes:

    1. **Document Map RAG** (/api/chat): Uses living document map for one-shot retrieval
    2. **Agentic SQL RAG** (/api/agentic): Uses iterative SQL queries with LLM reasoning

    Both powered by Gemini.
    """,
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["Document Map RAG"])
app.include_router(agentic_chat.router, prefix="/api/agentic", tags=["Agentic SQL RAG"])
app.include_router(ocr_router, prefix="/api", tags=["OCR Benchmark"])
