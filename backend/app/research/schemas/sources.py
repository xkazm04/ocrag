"""Source and grounding schemas."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class GroundingChunk(BaseModel):
    """A grounding chunk from Gemini search."""
    uri: str
    title: Optional[str] = None


class GroundingSupport(BaseModel):
    """Support evidence from grounding."""
    segment: Dict[str, Any]
    chunk_indices: List[int] = []
    confidence_scores: List[float] = []


class GroundingMetadata(BaseModel):
    """Metadata from Gemini grounding."""
    web_search_queries: List[str] = []
    grounding_chunks: List[GroundingChunk] = []
    grounding_supports: List[GroundingSupport] = []


class Source(BaseModel):
    """A web source discovered during research."""
    id: Optional[UUID] = None
    url: str
    title: Optional[str] = None
    domain: Optional[str] = None
    snippet: Optional[str] = None
    credibility_score: Optional[float] = None
    credibility_factors: Optional[Dict[str, float]] = None
    source_type: Optional[str] = None
    content_date: Optional[date] = None
    discovered_at: Optional[datetime] = None


class SearchResult(BaseModel):
    """Result from a grounded web search."""
    query: str
    synthesized_content: str
    sources: List[Source] = []
    grounding_metadata: Optional[GroundingMetadata] = None
    search_queries: List[str] = []
