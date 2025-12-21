"""Qwen VL OCR service via OpenRouter."""
import httpx

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


class QwenOCR(BaseOCRService):
    """OCR using Qwen VL model via OpenRouter."""

    engine_id = "qwen"
    engine_name = "Qwen2 VL 72B"
    category = OCRCategory.OPEN_LLM

    def __init__(self):
        settings = get_ocr_settings()
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.qwen_model

    def is_available(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(self.api_key)

    async def process(
        self,
        image: bytes,
        filename: str,
        languages: list[str] = None
    ) -> OCRResult:
        """Process image using Qwen VL via OpenRouter."""
        if not self.is_available():
            return self._create_result(
                success=False,
                error="OpenRouter API key not configured"
            )

        with TimedExecution() as timer:
            try:
                result = await self._call_qwen(image)
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

    async def _call_qwen(self, image: bytes) -> dict:
        """Call Qwen VL via OpenRouter."""
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

    def _estimate_cost(self, usage: dict) -> float:
        """Estimate cost for Qwen VL."""
        total = usage.get("total_tokens", 0)
        if not total:
            return None
        # Qwen via OpenRouter ~$0.50/1M tokens
        return (total / 1_000_000) * 0.5
