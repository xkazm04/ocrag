"""OpenRouter LLM client for research testing.

Uses Gemini 2.0 Flash via OpenRouter API for testing research templates
without requiring direct Gemini API access.
"""

import json
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class LLMResponse:
    """Response from LLM call."""
    text: str
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    model: str = ""
    raw_response: Optional[Dict] = None


class OpenRouterClient:
    """OpenRouter client for Gemini Flash."""

    DEFAULT_MODEL = "google/gemini-2.0-flash-001"
    BASE_URL = "https://openrouter.ai/api/v1"

    # Cost per 1M tokens (approximate)
    COST_RATES = {
        "google/gemini-2.0-flash-001": {"input": 0.1, "output": 0.4},
        "google/gemini-2.5-flash-preview": {"input": 0.15, "output": 0.6},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL

        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY env var."
            )

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate completion from the model."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://research-test.local",
            "X-Title": "Research Template Test",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            text=text,
            tokens_used=usage.get("total_tokens"),
            cost_usd=self._calculate_cost(usage),
            model=self.model,
            raw_response=data,
        )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> tuple[Any, LLMResponse]:
        """Generate JSON response from the model.

        Returns:
            Tuple of (parsed_json, full_response)
        """
        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            json_mode=True,
        )

        # Parse JSON from response
        parsed = self._parse_json(response.text)
        return parsed, response

    def _parse_json(self, text: str) -> Any:
        """Parse JSON from response text."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            # Look for array
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass

            # Look for object
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass

            return None

    def _calculate_cost(self, usage: Dict) -> Optional[float]:
        """Calculate cost based on token usage."""
        if not usage:
            return None

        rates = self.COST_RATES.get(self.model, {"input": 0.1, "output": 0.4})

        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]

        return input_cost + output_cost


class WebSearchSimulator:
    """Simulates web search results for testing.

    In production, this would call the actual web search service.
    For testing, we can use mock data or call a search API.
    """

    def __init__(self, llm_client: OpenRouterClient):
        self.llm = llm_client

    async def search_with_grounding(
        self,
        query: str,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Simulate grounded web search using LLM.

        For testing, we ask the LLM to provide information as if
        it had access to current web sources.
        """
        prompt = f"""You are a research assistant with access to current web information.

Research Query: {query}

Provide a comprehensive research response as if you had just searched the web.
Include:
1. Key facts and information discovered
2. Multiple perspectives on the topic
3. Recent developments (if applicable)
4. References to credible sources (simulate realistic URLs)

Format your response as JSON:
{{
    "synthesized_content": "Comprehensive research findings...",
    "sources": [
        {{
            "url": "https://example.com/article",
            "title": "Article Title",
            "domain": "example.com",
            "snippet": "Brief excerpt from the source...",
            "source_type": "news|academic|government|wiki"
        }}
    ],
    "search_queries": ["related query 1", "related query 2"]
}}

Provide at least {max_results} realistic sources with varied domains.
"""

        result, response = await self.llm.generate_json(prompt)

        if result:
            return {
                "synthesized_content": result.get("synthesized_content", ""),
                "sources": result.get("sources", []),
                "search_queries": result.get("search_queries", []),
                "tokens_used": response.tokens_used,
                "cost_usd": response.cost_usd,
            }

        return {
            "synthesized_content": response.text,
            "sources": [],
            "search_queries": [],
            "tokens_used": response.tokens_used,
            "cost_usd": response.cost_usd,
        }


@lru_cache()
def get_llm_client() -> OpenRouterClient:
    """Get cached LLM client instance."""
    return OpenRouterClient()
