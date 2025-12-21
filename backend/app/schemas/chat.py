"""Pydantic schemas for chat."""
from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    """Request schema for chat query."""
    query: str
    workspace_id: str = "default"
    session_id: Optional[str] = None
    max_documents: Optional[int] = 5


class Citation(BaseModel):
    """Citation from a retrieved document."""
    doc_id: str
    excerpt: str


class ChatResponse(BaseModel):
    """Response schema for chat query."""
    answer: str
    citations: list[dict]
    confidence: float
    retrieved_docs: list[str]
    session_id: Optional[str] = None


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str
    content: str
    citations: list[dict] = []
    timestamp: str


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history."""
    session_id: str
    messages: list[dict]


class ChatHistoryClearResponse(BaseModel):
    """Response schema for clearing chat history."""
    status: str
    session_id: str
