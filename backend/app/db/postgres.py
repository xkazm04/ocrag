"""PostgreSQL database connection and session management."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db.models import Base

# Import agentic SQL models to register them with Base
from app.core.agentic_sql.schemas import (
    SQLDocument, SQLClaim, SQLMetric, SQLEntity,
    SQLTopic, SQLRelationship, SQLDocumentChunk
)

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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
