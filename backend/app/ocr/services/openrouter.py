"""OpenRouter OCR service for GPT and Gemini models."""
import httpx
from typing import Optional

from app.ocr.services.base import BaseOCRService, TimedExecution
from app.ocr.schemas import OCRResult, OCRCategory
from app.ocr.config import get_ocr_settings

OCR_PROMPT = """Extract all text from this document image.
Preserve the original structure including:
- Paragraphs and line breaks
- Tables (use markdown table format)
- Lists (numbered and bulleted)
- Headers and sections

Output the extracted text in clean Markdown format.
Only output the extracted content, no explanations."""


class OpenRouterOCR(BaseOCRService):
    """OCR using OpenRouter API (GPT, Gemini)."""

    category = OCRCategory.LLM

    def __init__(self, model_type: str = "gpt"):
        """Initialize with model type: 'gpt' or 'gemini'."""
        self.model_type = model_type
        settings = get_ocr_settings()

        if model_type == "gpt":
            self.engine_id = "gpt"
            self.engine_name = "GPT-4o"
            self.model = settings.gpt_model
        else:
            self.engine_id = "gemini"
            self.engine_name = "Gemini 2.0 Flash"
            self.model = settings.gemini_model

        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url

    def is_available(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(self.api_key)

    async def process(
        self,
        image: bytes,
        filename: str,
        languages: list[str] = None
    ) -> OCRResult:
        """Process image using OpenRouter API."""
        if not self.is_available():
            return self._create_result(
                success=False,
                error="OpenRouter API key not configured"
            )

        with TimedExecution() as timer:
            try:
                result = await self._call_openrouter(image)
            except Exception as e:
                return self._create_result(
                    success=False,
                    error=str(e),
                    processing_time_ms=timer.elapsed_ms
                )

        return self._create_result(
            text=result.get("text", ""),
            tokens_used=result.get("tokens"),
            cost_usd=result.get("cost"),
            processing_time_ms=timer.elapsed_ms
        )

    async def _call_openrouter(self, image: bytes) -> dict:
        """Call OpenRouter API with image."""
        mime_type = self.get_image_mime_type(image)
        base64_image = self.image_to_base64(image)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ocr-benchmark.app",
            "X-Title": "OCR Benchmark Arena"
        }

        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }],
            "max_tokens": 4096
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return {
            "text": text,
            "tokens": usage.get("total_tokens"),
            "cost": self._estimate_cost(usage)
        }

    def _estimate_cost(self, usage: dict) -> Optional[float]:
        """Estimate cost based on token usage."""
        total = usage.get("total_tokens", 0)
        if not total:
            return None
        # Rough estimates per 1M tokens
        rates = {"gpt": 5.0, "gemini": 0.5}
        rate = rates.get(self.model_type, 1.0)
        return (total / 1_000_000) * rate
