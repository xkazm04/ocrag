"""OpenRouter inference client for perspective analysis and query decomposition.

Uses Gemini 3 Flash Preview via OpenRouter for fast, cheap inference
without web search capabilities.
"""

import json
import httpx
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import os

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
from dotenv import load_dotenv
load_dotenv(_project_root / ".env")


@dataclass
class TokenUsage:
    """Token usage from API response."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class InferenceResponse:
    """Response from inference call."""
    text: str
    token_usage: Optional[TokenUsage] = None
    cost_usd: Optional[float] = None
    model: str = ""
    raw_response: Optional[Dict] = None


class InferenceClient:
    """OpenRouter client for inference-only tasks (no web search).

    Used for:
    - Query decomposition
    - Perspective analysis
    - Relationship building
    - Gap analysis

    Uses Gemini 3 Flash Preview for fast, affordable inference.
    """

    DEFAULT_MODEL = "google/gemini-3-flash-preview"
    BASE_URL = "https://openrouter.ai/api/v1"

    # Cost per 1M tokens (approximate for Gemini 3 Flash)
    COST_RATES = {
        "google/gemini-3-flash-preview": {"input": 0.10, "output": 0.40},
        "google/gemini-2.0-flash-001": {"input": 0.10, "output": 0.40},
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
        """Check if client is properly configured."""
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> InferenceResponse:
        """Generate text response."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/research-system",
            "X-Title": "Research System",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Extract response text
        text = ""
        if data.get("choices"):
            text = data["choices"][0].get("message", {}).get("content", "")

        # Extract token usage
        token_usage = None
        usage_data = data.get("usage", {})
        if usage_data:
            token_usage = TokenUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

        # Estimate cost
        cost_usd = self._estimate_cost(token_usage)

        return InferenceResponse(
            text=text,
            token_usage=token_usage,
            cost_usd=cost_usd,
            model=self.model,
            raw_response=data,
        )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Tuple[Any, InferenceResponse]:
        """Generate and parse JSON response.

        Returns:
            Tuple of (parsed_json, response)
        """
        # Add JSON instruction to prompt if not already there
        if "json" not in prompt.lower():
            prompt = f"{prompt}\n\nRespond with valid JSON only."

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )

        # Parse JSON from response
        parsed = self._parse_json(response.text)

        return parsed, response

    def _estimate_cost(self, token_usage: Optional[TokenUsage]) -> Optional[float]:
        """Estimate cost based on token usage."""
        if not token_usage:
            return None

        rates = self.COST_RATES.get(
            self.model,
            {"input": 0.10, "output": 0.40}
        )

        input_cost = (token_usage.input_tokens / 1_000_000) * rates["input"]
        output_cost = (token_usage.output_tokens / 1_000_000) * rates["output"]

        return input_cost + output_cost

    def _parse_json(self, text: str) -> Any:
        """Parse JSON from text, handling markdown code blocks."""
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            for start_char, end_char in [('[', ']'), ('{', '}')]:
                start = text.find(start_char)
                end = text.rfind(end_char) + 1
                if start != -1 and end > start:
                    try:
                        return json.loads(text[start:end])
                    except json.JSONDecodeError:
                        continue
            return None


def get_inference_client(model: Optional[str] = None) -> Optional[InferenceClient]:
    """Get inference client instance."""
    try:
        return InferenceClient(model=model)
    except ValueError as e:
        print(f"Warning: Could not initialize inference client: {e}")
        return None


def check_availability() -> Dict[str, Any]:
    """Check client availability."""
    return {
        "api_key_set": bool(os.getenv("OPENROUTER_API_KEY")),
    }
