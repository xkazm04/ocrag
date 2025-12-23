"""Base expert persona for multi-perspective analysis."""

from abc import ABC, abstractmethod
from typing import List

from google import genai
from google.genai import types

from app.config import get_settings
from ..schemas import Finding, Source, Perspective


class BasePersona(ABC):
    """
    Abstract base class for expert personas.

    Each persona provides a specialized analytical lens:
    - Unique system prompt defining expertise
    - Domain-specific analysis framework
    - Specialized insights and recommendations
    """

    persona_id: str = "base"
    persona_name: str = "Base Expert"
    description: str = "Base expert persona"

    # The expertise areas this persona covers
    expertise_areas: List[str] = []

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_research_model

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The system prompt defining this persona's expertise and approach."""
        pass

    @abstractmethod
    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        """Get the analysis prompt for this perspective."""
        pass

    async def analyze(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> Perspective:
        """
        Analyze the research from this persona's perspective.

        Args:
            query: Original research question
            findings: Extracted findings to analyze
            sources: Sources to reference

        Returns:
            Perspective with analysis, insights, and recommendations
        """
        analysis_prompt = self.get_analysis_prompt(query, findings, sources)

        full_prompt = f"""
{self.system_prompt}

{analysis_prompt}

Provide your analysis as JSON with this structure:
{{
    "analysis_text": "Your detailed analysis from your expert perspective...",
    "key_insights": ["insight 1", "insight 2", "insight 3"],
    "confidence": 0.0-1.0,
    "recommendations": ["recommendation 1", "recommendation 2"],
    "warnings": ["warning 1 if any"]
}}
"""

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[full_prompt],
            config=config,
        )

        import json
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            result = {
                "analysis_text": response.text,
                "key_insights": [],
                "confidence": 0.5,
                "recommendations": [],
                "warnings": [],
            }

        return Perspective(
            perspective_type=self.persona_id,
            analysis_text=result.get("analysis_text", ""),
            key_insights=result.get("key_insights", []),
            confidence=result.get("confidence", 0.5),
            findings_analyzed=[f.id for f in findings if f.id],
            sources_cited=[s.id for s in sources if s.id],
            recommendations=result.get("recommendations", []),
            warnings=result.get("warnings", []),
        )

    def _format_findings(self, findings: List[Finding]) -> str:
        """Format findings for the analysis prompt."""
        return "\n\n".join([
            f"[{f.finding_type.upper()}] {f.content}\n"
            f"  Confidence: {f.confidence_score:.1%}\n"
            f"  Temporal: {f.temporal_context or 'unknown'}"
            for f in findings
        ])

    def _format_sources(self, sources: List[Source]) -> str:
        """Format sources for the analysis prompt."""
        return "\n".join([
            f"- {s.title or s.url} (credibility: {s.credibility_score:.1%})"
            for s in sources[:10]
            if s.credibility_score
        ])
