"""Comparative OCR evaluation service."""
import json
import httpx
from typing import Dict

from app.ocr.schemas import ComparativeEvaluation, EngineScore, OCRResult
from app.ocr.config import get_ocr_settings

ENGINE_NAMES = {
    "gpt": "GPT-5.2",
    "gemini": "Gemini 3 Flash",
    "mistral": "Mistral OCR",
    "qwen": "Qwen2 VL 72B",
    "paddle": "PaddleOCR",
    "easy": "EasyOCR",
    "surya": "Surya OCR",
}

COMPARATIVE_SYSTEM_PROMPT = """You are an expert OCR quality analyst. You will compare multiple OCR outputs from different engines processing the SAME document.

Your task is to evaluate each engine's output and assign percentage scores (0-100) based on:

1. ACCURACY (40% weight): Correctness of extracted text
   - Spelling accuracy
   - Character recognition (no substitutions like 0/O, 1/l)
   - Word integrity (no merged/split words)

2. COMPLETENESS (30% weight): How much content was captured
   - All text regions detected
   - No missing paragraphs/sections
   - Tables and lists fully captured

3. FORMATTING (30% weight): Structure preservation
   - Paragraph breaks maintained
   - Table structure preserved
   - Lists properly formatted
   - Headers/sections identified

Compare ALL outputs against each other to determine relative quality.
The engine with the most complete and accurate text should score highest.

You MUST respond with this exact JSON structure:
{
    "engines": [
        {
            "engine_id": "engine_id_here",
            "accuracy_score": 85,
            "completeness_score": 90,
            "formatting_score": 80,
            "overall_score": 85,
            "strengths": ["strength1", "strength2"],
            "weaknesses": ["weakness1"]
        }
    ],
    "best_overall": "engine_id",
    "best_accuracy": "engine_id",
    "best_formatting": "engine_id",
    "summary": "Brief comparison summary"
}"""

COMPARATIVE_USER_PROMPT = """Compare these OCR outputs from different engines processing the same document:

{engine_outputs}

Evaluate each engine and provide percentage scores. Be critical and identify differences between outputs."""


class ComparativeEvaluator:
    """Compare and evaluate multiple OCR outputs."""

    def __init__(self):
        settings = get_ocr_settings()
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.eval_model
        self.temperature = settings.eval_temperature

    def is_available(self) -> bool:
        """Check if evaluator is available."""
        return bool(self.api_key)

    async def evaluate(
        self,
        results: Dict[str, OCRResult],
        language: str = "en"
    ) -> ComparativeEvaluation:
        """Evaluate and compare all successful OCR results."""
        if not self.is_available():
            return ComparativeEvaluation(
                summary="Evaluator not configured",
                methodology="OpenRouter API key required"
            )

        # Filter successful results with text
        successful = {
            eid: r for eid, r in results.items()
            if r.success and r.text and len(r.text.strip()) > 10
        }

        if len(successful) < 1:
            return ComparativeEvaluation(
                summary="No successful OCR results to evaluate",
                methodology="At least one successful result required"
            )

        try:
            result = await self._call_evaluator(successful)
            return self._parse_result(result, successful)
        except Exception as e:
            return ComparativeEvaluation(
                summary=f"Evaluation failed: {str(e)}",
                methodology="Error during LLM evaluation"
            )

    async def _call_evaluator(self, results: Dict[str, OCRResult]) -> dict:
        """Call LLM for comparative evaluation."""
        # Format engine outputs for comparison
        engine_outputs = []
        for engine_id, result in results.items():
            text = result.text
            # Truncate long texts
            if len(text) > 3000:
                text = text[:3000] + "\n...[truncated]..."

            engine_outputs.append(
                f"=== {ENGINE_NAMES.get(engine_id, engine_id)} (id: {engine_id}) ===\n{text}\n"
            )

        combined = "\n".join(engine_outputs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": COMPARATIVE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": COMPARATIVE_USER_PROMPT.format(engine_outputs=combined)
                }
            ],
            "temperature": self.temperature,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        return json.loads(content)

    def _parse_result(
        self,
        data: dict,
        results: Dict[str, OCRResult]
    ) -> ComparativeEvaluation:
        """Parse LLM response into ComparativeEvaluation."""
        engines = []
        engine_data = data.get("engines", [])

        # Sort by overall score and assign ranks
        engine_data.sort(key=lambda x: x.get("overall_score", 0), reverse=True)

        for rank, eng in enumerate(engine_data, 1):
            engine_id = eng.get("engine_id", "")
            if engine_id not in results:
                continue

            category = results[engine_id].category.value if results[engine_id].category else "traditional"

            engines.append(EngineScore(
                engine_id=engine_id,
                engine_name=ENGINE_NAMES.get(engine_id, engine_id),
                category=category,
                accuracy_score=eng.get("accuracy_score", 0),
                completeness_score=eng.get("completeness_score", 0),
                formatting_score=eng.get("formatting_score", 0),
                overall_score=eng.get("overall_score", 0),
                rank=rank,
                strengths=eng.get("strengths", []),
                weaknesses=eng.get("weaknesses", [])
            ))

        return ComparativeEvaluation(
            engines=engines,
            best_overall=data.get("best_overall"),
            best_accuracy=data.get("best_accuracy"),
            best_formatting=data.get("best_formatting"),
            summary=data.get("summary", ""),
            methodology="LLM-based comparative analysis: Accuracy (40%), Completeness (30%), Formatting (30%)"
        )
