"""Pydantic schemas for document map."""
from pydantic import BaseModel
from typing import Optional


class DocumentMapEntry(BaseModel):
    """Schema for a document entry in the map."""
    id: str
    filename: str
    type: str
    size_class: str
    essence: str
    topics: list[str]
    retrieval_hints: str
    added_at: str
    chunk_count: Optional[int] = 0


class CrossReferences(BaseModel):
    """Schema for cross-references in the map."""
    by_entity: dict[str, list[str]] = {}
    by_topic: dict[str, list[str]] = {}


class DocumentMapResponse(BaseModel):
    """Response schema for document map."""
    corpus_id: str
    last_updated: str
    corpus_summary: str
    document_count: int
    documents: list[DocumentMapEntry]
    cross_references: CrossReferences


class MapStatistics(BaseModel):
    """Statistics about the document map."""
    total_documents: int
    small_documents: int
    large_documents: int
    total_chunks: int
    unique_topics: int
    unique_entities: int
