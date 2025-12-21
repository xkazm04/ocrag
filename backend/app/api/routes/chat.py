"""Chat/Query API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import uuid

from app.db.postgres import get_db
from app.db.models import ChatHistory
from app.core.gemini_client import get_gemini_client
from app.core.retriever import IntelligentRetriever
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatHistoryClearResponse
)

router = APIRouter()


@router.post("/query", response_model=ChatResponse)
async def query_documents(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Query documents using intelligent retrieval.

    1. Retrieve relevant documents via map consultation
    2. Generate answer using Gemini
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


@router.delete("/history/{session_id}", response_model=ChatHistoryClearResponse)
async def clear_chat_history(
    session_id: str,
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Clear chat history for a session."""
    await db.execute(
        delete(ChatHistory).where(
            ChatHistory.session_id == session_id,
            ChatHistory.workspace_id == workspace_id
        )
    )
    await db.commit()

    return ChatHistoryClearResponse(status="cleared", session_id=session_id)


@router.get("/sessions")
async def list_sessions(
    workspace_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """List all chat sessions in workspace."""
    result = await db.execute(
        select(ChatHistory.session_id)
        .where(ChatHistory.workspace_id == workspace_id)
        .distinct()
    )
    sessions = result.scalars().all()

    return {"sessions": list(sessions), "total": len(sessions)}
