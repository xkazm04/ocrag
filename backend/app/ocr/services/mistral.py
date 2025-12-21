"""Mistral OCR service using dedicated OCR endpoint."""
import httpx
from typing import Optional

from app.ocr.services.base import BaseOCRService, TimedExecution
from app.ocr.schemas import OCRResult, OCRCategory
from app.ocr.config import get_ocr_settings


class MistralOCR(BaseOCRService):
    """OCR using Mistral's dedicated OCR API."""

    engine_id = "mistral"
    engine_name = "Mistral OCR"
    category = OCRCategory.LLM

    def __init__(self):
        settings = get_ocr_settings()
        self.api_key = settings.mistral_api_key
        self.model = settings.mistral_ocr_model
        self.base_url = "https://api.mistral.ai/v1"

    def is_available(self) -> bool:
        """Check if Mistral API key is configured."""
        return bool(self.api_key)

    async def process(
        self,
        image: bytes,
        filename: str,
        languages: list[str] = None
    ) -> OCRResult:
        """Process image using Mistral OCR API."""
        if not self.is_available():
            return self._create_result(
                success=False,
                error="Mistral API key not configured"
            )

        with TimedExecution() as timer:
            try:
                result = await self._call_mistral_ocr(image, filename)
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

    async def _call_mistral_ocr(self, image: bytes, filename: str) -> dict:
        """Call Mistral OCR API."""
        mime_type = self.get_image_mime_type(image)
        base64_image = self.image_to_base64(image)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Mistral OCR uses chat completions with vision
        payload = {
            "model": "pixtral-12b-2409",  # Mistral's vision model
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text from this image. Preserve structure, tables, and formatting. Output in Markdown."
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:{mime_type};base64,{base64_image}"
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
        """Estimate cost: ~$1 per 1000 pages."""
        total = usage.get("total_tokens", 0)
        if not total:
            return None
        # Mistral OCR ~$1/1000 pages, ~1000 tokens per page
        return (total / 1_000_000) * 1.0
