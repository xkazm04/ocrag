"""Pydantic schemas for documents."""
from pydantic import BaseModel
from typing import Optional


class DocumentResponse(BaseModel):
    """Response schema for document upload and retrieval."""
    id: str
    filename: str
    size_class: str
    token_count: int
    chunk_count: int
    essence: str = ""
    topics: list[str] = []


class DocumentListResponse(BaseModel):
    """Response schema for listing documents."""
    documents: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """Response schema for successful document upload."""
    id: str
    filename: str
    size_class: str
    token_count: int
    chunk_count: int
    essence: str
    topics: list[str]
    message: str = "Document processed successfully"


class DocumentDeleteResponse(BaseModel):
    """Response schema for document deletion."""
    status: str
    document_id: str
