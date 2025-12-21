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
from sqlalchemy import select

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
    confidence: float
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
        citations=[{"sources": result["sources"], "queries": result["queries_executed"]}]
    )
    db.add(assistant_msg)

    await db.commit()

    return AgenticQueryResponse(
        answer=result["answer"],
        queries_executed=result["queries_executed"],
        sources=result["sources"],
        reasoning_steps=result["reasoning_steps"],
        iterations=result["iterations"],
        confidence=result.get("confidence", 0.5),
        session_id=session_id
    )


@router.get("/schema")
async def get_schema():
    """Return the SQL schema description for reference."""
    from app.core.agentic_sql.schemas import SQL_SCHEMA_DESCRIPTION
    return {"schema": SQL_SCHEMA_DESCRIPTION}


@router.get("/stats")
async def get_extraction_stats(
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about extracted data in the SQL tables."""
    from sqlalchemy import func
    from app.core.agentic_sql.schemas import (
        SQLDocument, SQLClaim, SQLMetric, SQLEntity, SQLTopic
    )

    doc_count = await db.scalar(
        select(func.count()).select_from(SQLDocument).where(SQLDocument.workspace_id == workspace_id)
    )
    claim_count = await db.scalar(
        select(func.count()).select_from(SQLClaim)
        .join(SQLDocument)
        .where(SQLDocument.workspace_id == workspace_id)
    )
    metric_count = await db.scalar(
        select(func.count()).select_from(SQLMetric)
        .join(SQLDocument)
        .where(SQLDocument.workspace_id == workspace_id)
    )
    entity_count = await db.scalar(
        select(func.count()).select_from(SQLEntity)
        .join(SQLDocument)
        .where(SQLDocument.workspace_id == workspace_id)
    )
    topic_count = await db.scalar(
        select(func.count()).select_from(SQLTopic)
        .join(SQLDocument)
        .where(SQLDocument.workspace_id == workspace_id)
    )

    return {
        "workspace_id": workspace_id,
        "documents": doc_count or 0,
        "claims": claim_count or 0,
        "metrics": metric_count or 0,
        "entities": entity_count or 0,
        "topics": topic_count or 0
    }
