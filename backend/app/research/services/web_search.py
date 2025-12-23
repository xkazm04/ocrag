"""Web search service using Gemini 2.0 Flash with Google Search grounding."""

import time
from typing import Optional, List
from urllib.parse import urlparse
from uuid import UUID

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from ..schemas import (
    SearchResult,
    Source,
    GroundingMetadata,
    GroundingChunk,
    GroundingSupport,
)


class WebSearchService:
    """
    Performs web searches using Gemini's Google Search grounding.

    This service wraps Gemini 2.0 Flash with google_search tool enabled,
    extracting both the model's synthesized response and the underlying
    web sources for credibility assessment.
    """

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_research_model

        # Configure search grounding tool
        self.grounding_tool = types.Tool(google_search=types.GoogleSearch())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def search_with_grounding(
        self,
        query: str,
        purpose: Optional[str] = None,
        max_sources: int = 10,
    ) -> SearchResult:
        """
        Execute a grounded web search.

        Args:
            query: The search query
            purpose: Why this query was generated (for context)
            max_sources: Maximum sources to return

        Returns:
            SearchResult with synthesized content and extracted sources
        """
        # Craft the search prompt
        context = f"\nContext: {purpose}" if purpose else ""
        search_prompt = f"""
Research the following query and provide comprehensive, factual information:

Query: {query}{context}

Instructions:
1. Search for recent, authoritative sources
2. Prioritize primary sources and official reports
3. Include multiple perspectives when relevant
4. Note any conflicting information between sources
5. Provide specific facts, dates, names, and figures where available
6. Clearly distinguish between verified facts and claims/opinions
"""

        config = types.GenerateContentConfig(tools=[self.grounding_tool])

        start_time = time.time()

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=search_prompt,
            config=config,
        )

        execution_time_ms = int((time.time() - start_time) * 1000)

        # Extract grounding metadata
        grounding_metadata = self._extract_grounding_metadata(response)
        sources = self._extract_sources(response, max_sources)

        return SearchResult(
            query=query,
            synthesized_content=response.text or "",
            sources=sources,
            grounding_metadata=grounding_metadata,
            search_queries=grounding_metadata.web_search_queries if grounding_metadata else [],
        )

    def _extract_grounding_metadata(self, response) -> Optional[GroundingMetadata]:
        """Extract grounding metadata from Gemini response."""
        try:
            if not response.candidates:
                return None

            metadata = response.candidates[0].grounding_metadata
            if not metadata:
                return None

            grounding_chunks = []
            if metadata.grounding_chunks:
                for chunk in metadata.grounding_chunks:
                    if hasattr(chunk, "web") and chunk.web:
                        grounding_chunks.append(
                            GroundingChunk(
                                uri=chunk.web.uri,
                                title=getattr(chunk.web, "title", None),
                            )
                        )

            grounding_supports = []
            if metadata.grounding_supports:
                for support in metadata.grounding_supports:
                    segment_data = {}
                    if hasattr(support, "segment") and support.segment:
                        segment_data = {
                            "start": getattr(support.segment, "start_index", 0),
                            "end": getattr(support.segment, "end_index", 0),
                            "text": getattr(support.segment, "text", ""),
                        }
                    grounding_supports.append(
                        GroundingSupport(
                            segment=segment_data,
                            chunk_indices=list(support.grounding_chunk_indices or []),
                            confidence_scores=list(support.confidence_scores or []),
                        )
                    )

            return GroundingMetadata(
                web_search_queries=list(metadata.web_search_queries or []),
                grounding_chunks=grounding_chunks,
                grounding_supports=grounding_supports,
            )
        except Exception:
            return None

    def _extract_sources(self, response, max_sources: int) -> List[Source]:
        """Extract unique sources from grounding chunks."""
        try:
            if not response.candidates:
                return []

            metadata = response.candidates[0].grounding_metadata
            if not metadata or not metadata.grounding_chunks:
                return []

            seen_urls = set()
            sources = []

            for chunk in metadata.grounding_chunks:
                if not hasattr(chunk, "web") or not chunk.web:
                    continue

                url = chunk.web.uri
                if url in seen_urls:
                    continue

                seen_urls.add(url)
                sources.append(
                    Source(
                        url=url,
                        title=getattr(chunk.web, "title", None),
                        domain=self._extract_domain(url),
                        snippet=None,  # Will be filled by credibility service
                    )
                )

                if len(sources) >= max_sources:
                    break

            return sources
        except Exception:
            return []

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    async def search_batch(
        self,
        queries: List[str],
        purposes: Optional[List[str]] = None,
        max_sources_per_query: int = 10,
    ) -> List[SearchResult]:
        """
        Execute multiple grounded web searches.

        Args:
            queries: List of search queries
            purposes: Optional list of purposes for each query
            max_sources_per_query: Maximum sources per query

        Returns:
            List of SearchResults
        """
        results = []
        for i, query in enumerate(queries):
            purpose = purposes[i] if purposes and i < len(purposes) else None
            result = await self.search_with_grounding(
                query=query,
                purpose=purpose,
                max_sources=max_sources_per_query,
            )
            results.append(result)
        return results


# Singleton instance
_web_search_service: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    """Get or create the WebSearchService singleton."""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
