"""Native Google Generative AI client with web search grounding.

Uses Google's official genai SDK for Gemini models with built-in
web search capabilities.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from functools import lru_cache
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent  # rag/
load_dotenv(_project_root / ".env")

# Import Google's genai SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None


@dataclass
class GroundedSource:
    """A source from grounded web search."""
    url: str
    title: str
    domain: str
    snippet: str
    source_type: str = "web"


@dataclass
class GroundedResponse:
    """Response from grounded LLM call."""
    text: str
    sources: List[GroundedSource] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)
    tokens_used: Optional[int] = None
    model: str = ""
    raw_response: Optional[Any] = None


class GeminiGroundedClient:
    """Native Gemini client with web search grounding."""

    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package not installed. "
                "Install with: pip install google-genai"
            )

        # Check multiple env var names for API key
        self.api_key = (
            api_key
            or os.getenv("GOOGLE_API_KEY", "")
            or os.getenv("GEMINI_API_KEY", "")
        )
        self.model = model or self.DEFAULT_MODEL

        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY or GEMINI_API_KEY env var."
            )

        # Initialize the client
        self.client = genai.Client(api_key=self.api_key)

    def is_available(self) -> bool:
        """Check if client is properly configured."""
        return bool(self.api_key) and GENAI_AVAILABLE

    async def generate_with_search(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GroundedResponse:
        """Generate response with web search grounding."""
        # Build the full prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        # Configure with Google Search tool
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )

        # Generate response (synchronous API, but we wrap it)
        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt,
            config=config,
        )

        # Extract sources from grounding metadata
        sources = []
        search_queries = []

        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]

            # Get grounding metadata
            if hasattr(candidate, 'grounding_metadata'):
                metadata = candidate.grounding_metadata

                # Extract search queries used
                if hasattr(metadata, 'web_search_queries'):
                    search_queries = list(metadata.web_search_queries or [])

                # Extract grounding chunks (sources)
                if hasattr(metadata, 'grounding_chunks'):
                    for chunk in (metadata.grounding_chunks or []):
                        if hasattr(chunk, 'web'):
                            web = chunk.web
                            url = getattr(web, 'uri', '') or ''
                            title = getattr(web, 'title', '') or ''

                            # Extract domain from URL
                            domain = ""
                            if url:
                                try:
                                    from urllib.parse import urlparse
                                    domain = urlparse(url).netloc
                                except Exception:
                                    pass

                            sources.append(GroundedSource(
                                url=url,
                                title=title,
                                domain=domain,
                                snippet="",  # Not always available in metadata
                            ))

        # Get token usage if available
        tokens_used = None
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            tokens_used = getattr(usage, 'total_token_count', None)

        return GroundedResponse(
            text=response.text,
            sources=sources,
            search_queries=search_queries,
            tokens_used=tokens_used,
            model=self.model,
            raw_response=response,
        )

    async def search_and_synthesize(
        self,
        query: str,
        max_sources: int = 10,
    ) -> Dict[str, Any]:
        """Search web and return synthesized content with sources.

        This is the replacement for WebSearchSimulator.
        """
        prompt = f"""
Research the following topic using web search and provide a comprehensive response:

Topic: {query}

Please provide:
1. A detailed synthesis of the information found
2. Key facts and findings
3. Multiple perspectives if applicable
4. Recent developments

Base your response on current web sources.
"""

        response = await self.generate_with_search(
            prompt=prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        return {
            "synthesized_content": response.text,
            "sources": [
                {
                    "url": s.url,
                    "title": s.title,
                    "domain": s.domain,
                    "snippet": s.snippet,
                    "source_type": s.source_type,
                }
                for s in response.sources[:max_sources]
            ],
            "search_queries": response.search_queries,
            "tokens_used": response.tokens_used,
            "cost_usd": self._estimate_cost(response.tokens_used),
        }

    def _estimate_cost(self, tokens: Optional[int]) -> Optional[float]:
        """Estimate cost based on tokens (Gemini Flash pricing)."""
        if not tokens:
            return None
        # Gemini Flash: ~$0.075 per 1M input, $0.30 per 1M output
        # Rough estimate assuming 50/50 split
        return (tokens / 1_000_000) * 0.20


@lru_cache()
def get_gemini_client() -> Optional[GeminiGroundedClient]:
    """Get cached Gemini client instance."""
    try:
        return GeminiGroundedClient()
    except (ImportError, ValueError) as e:
        print(f"Warning: Could not initialize Gemini client: {e}")
        return None


def check_genai_available() -> bool:
    """Check if google-genai package is available."""
    return GENAI_AVAILABLE
