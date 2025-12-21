"""LLM-based OCR output evaluator."""
import json
import httpx
from typing import Optional

from app.ocr.schemas import EvaluationResult, EvaluationIssue
from app.ocr.config import get_ocr_settings

EVALUATION_SYSTEM_PROMPT = """You are an expert document quality analyst specializing in OCR output evaluation.
Analyze the text for quality issues that may indicate OCR errors or document problems.

Evaluate these aspects (score 0-100):
1. GRAMMAR & SPELLING: Misspellings, broken/merged words, character substitutions (0/O, 1/l)
2. STRUCTURE: Paragraph preservation, table integrity, list formatting, heading hierarchy
3. STYLE: Consistent formatting, encoding issues, reading order, repeated/missing content

Respond ONLY with this JSON format:
{
    "grammar": {"score": 85, "issues": ["issue1", "issue2"]},
    "structure": {"score": 90, "issues": []},
    "style": {"score": 88, "issues": ["issue1"]},
    "composite_score": 87,
    "confidence": 0.9,
    "recommendations": ["recommendation1"],
    "summary": "Brief assessment"
}"""

EVALUATION_USER_PROMPT = """Analyze this OCR-extracted text for quality:

--- TEXT START ---
{text}
--- TEXT END ---

OCR Engine: {engine}
Expected language: {language}"""


class OCREvaluator:
    """Evaluate OCR output quality using LLM."""

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
        text: str,
        engine: str,
        language: str = "en"
    ) -> EvaluationResult:
        """Evaluate OCR output quality."""
        if not self.is_available():
            return EvaluationResult(summary="Evaluator not configured")

        if not text or len(text.strip()) < 10:
            return EvaluationResult(
                summary="Text too short to evaluate",
                composite_score=0
            )

        try:
            result = await self._call_evaluator(text, engine, language)
            return self._parse_result(result)
        except Exception as e:
            return EvaluationResult(summary=f"Evaluation failed: {str(e)}")

    async def _call_evaluator(
        self,
        text: str,
        engine: str,
        language: str
    ) -> dict:
        """Call LLM for evaluation."""
        # Truncate very long texts
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]..."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": EVALUATION_USER_PROMPT.format(
                        text=text,
                        engine=engine,
                        language=language
                    )
                }
            ],
            "temperature": self.temperature,
            "max_tokens": 1000
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        return json.loads(content)

    def _parse_result(self, data: dict) -> EvaluationResult:
        """Parse LLM response into EvaluationResult."""
        grammar = data.get("grammar", {})
        structure = data.get("structure", {})
        style = data.get("style", {})

        issues = []
        for category, cat_data in [
            ("grammar", grammar),
            ("structure", structure),
            ("style", style)
        ]:
            for issue_text in cat_data.get("issues", []):
                issues.append(EvaluationIssue(
                    issue_type=category,
                    description=issue_text,
                    severity="minor"
                ))

        return EvaluationResult(
            grammar_score=grammar.get("score", 0),
            structure_score=structure.get("score", 0),
            style_score=style.get("score", 0),
            composite_score=data.get("composite_score", 0),
            confidence=data.get("confidence", 0),
            issues=issues,
            recommendations=data.get("recommendations", []),
            summary=data.get("summary", "")
        )
