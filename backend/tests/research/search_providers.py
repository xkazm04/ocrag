"""External search API providers.

Supports multiple search APIs for the Search Tool mode.
"""

import os
import hashlib
import json
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import httpx

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
from dotenv import load_dotenv
load_dotenv(_project_root / ".env")


@dataclass
class SearchResult:
    """A single search result."""
    url: str
    title: str
    snippet: str
    domain: str = ""
    published_date: Optional[str] = None
    source_type: str = "web"

    def __post_init__(self):
        if not self.domain and self.url:
            try:
                from urllib.parse import urlparse
                self.domain = urlparse(self.url).netloc
            except Exception:
                pass


@dataclass
class SearchResponse:
    """Response from a search query."""
    query: str
    results: List[SearchResult] = field(default_factory=list)
    total_results: Optional[int] = None
    search_time_ms: Optional[float] = None
    provider: str = ""
    cached: bool = False


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> SearchResponse:
        """Execute a search query."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured."""
        pass


class BraveSearchProvider(SearchProvider):
    """Brave Search API provider.

    Get API key from: https://brave.com/search/api/
    """

    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> SearchResponse:
        if not self.is_available():
            raise ValueError("Brave API key not configured")

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }

        params = {
            "q": query,
            "count": min(max_results, 20),
            "text_decorations": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.BASE_URL,
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("web", {}).get("results", []):
            results.append(SearchResult(
                url=item.get("url", ""),
                title=item.get("title", ""),
                snippet=item.get("description", ""),
                published_date=item.get("age"),
            ))

        return SearchResponse(
            query=query,
            results=results[:max_results],
            total_results=data.get("web", {}).get("totalResults"),
            provider="brave",
        )


class SerperSearchProvider(SearchProvider):
    """Serper.dev API provider (Google results).

    Get API key from: https://serper.dev/
    """

    BASE_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> SearchResponse:
        if not self.is_available():
            raise ValueError("Serper API key not configured")

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "q": query,
            "num": min(max_results, 100),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("organic", []):
            results.append(SearchResult(
                url=item.get("link", ""),
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                published_date=item.get("date"),
            ))

        return SearchResponse(
            query=query,
            results=results[:max_results],
            search_time_ms=data.get("searchParameters", {}).get("timeTaken"),
            provider="serper",
        )


class SearchCache:
    """Simple file-based cache for search results."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_hours: int = 24,
    ):
        self.cache_dir = cache_dir or Path(__file__).parent / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)

    def _get_cache_key(self, query: str, provider: str) -> str:
        """Generate cache key from query."""
        normalized = query.lower().strip()
        hash_val = hashlib.md5(f"{provider}:{normalized}".encode()).hexdigest()
        return hash_val[:16]

    def _get_cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, query: str, provider: str) -> Optional[SearchResponse]:
        """Get cached search results if valid."""
        key = self._get_cache_key(query, provider)
        path = self._get_cache_path(key)

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check TTL
            cached_at = datetime.fromisoformat(data["cached_at"])
            if datetime.now() - cached_at > self.ttl:
                path.unlink()  # Expired
                return None

            # Reconstruct response
            results = [SearchResult(**r) for r in data["results"]]
            return SearchResponse(
                query=data["query"],
                results=results,
                total_results=data.get("total_results"),
                provider=data["provider"],
                cached=True,
            )

        except Exception:
            return None

    def set(self, response: SearchResponse) -> None:
        """Cache search results."""
        key = self._get_cache_key(response.query, response.provider)
        path = self._get_cache_path(key)

        data = {
            "query": response.query,
            "results": [
                {
                    "url": r.url,
                    "title": r.title,
                    "snippet": r.snippet,
                    "domain": r.domain,
                    "published_date": r.published_date,
                    "source_type": r.source_type,
                }
                for r in response.results
            ],
            "total_results": response.total_results,
            "provider": response.provider,
            "cached_at": datetime.now().isoformat(),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def clear(self) -> int:
        """Clear all cached results. Returns count of deleted files."""
        count = 0
        for path in self.cache_dir.glob("*.json"):
            path.unlink()
            count += 1
        return count


class SearchManager:
    """Manages multiple search providers with fallback and caching."""

    def __init__(
        self,
        providers: Optional[List[SearchProvider]] = None,
        use_cache: bool = True,
        cache_ttl_hours: int = 24,
    ):
        # Initialize default providers
        if providers is None:
            providers = []
            # Try each provider
            brave = BraveSearchProvider()
            if brave.is_available():
                providers.append(brave)

            serper = SerperSearchProvider()
            if serper.is_available():
                providers.append(serper)

        self.providers = providers
        self.cache = SearchCache(ttl_hours=cache_ttl_hours) if use_cache else None

    def is_available(self) -> bool:
        """Check if any provider is available."""
        return len(self.providers) > 0

    def get_available_providers(self) -> List[str]:
        """List available provider names."""
        return [type(p).__name__ for p in self.providers]

    async def search(
        self,
        query: str,
        max_results: int = 10,
        provider_index: int = 0,
    ) -> SearchResponse:
        """Execute search with fallback to other providers."""
        if not self.providers:
            raise ValueError("No search providers configured")

        # Check cache first
        if self.cache:
            provider_name = type(self.providers[provider_index]).__name__
            cached = self.cache.get(query, provider_name)
            if cached:
                return cached

        # Try providers in order
        last_error = None
        for i, provider in enumerate(self.providers[provider_index:], provider_index):
            try:
                response = await provider.search(query, max_results)

                # Cache result
                if self.cache:
                    self.cache.set(response)

                return response

            except Exception as e:
                last_error = e
                continue

        raise ValueError(f"All search providers failed: {last_error}")

    async def multi_search(
        self,
        queries: List[str],
        max_results_per_query: int = 10,
    ) -> List[SearchResponse]:
        """Execute multiple searches."""
        results = []
        for query in queries:
            try:
                response = await self.search(query, max_results_per_query)
                results.append(response)
            except Exception as e:
                # Return partial results
                results.append(SearchResponse(
                    query=query,
                    results=[],
                    provider="error",
                ))
        return results


def get_search_manager(use_cache: bool = True) -> SearchManager:
    """Get a configured search manager."""
    return SearchManager(use_cache=use_cache)
