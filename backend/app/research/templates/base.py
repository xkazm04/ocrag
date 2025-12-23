"""Base research template defining the common interface."""

from abc import ABC, abstractmethod
from typing import List, Optional

from google import genai
from google.genai import types

from app.config import get_settings
from ..schemas import Source, Finding, ResearchParameters


class BaseResearchTemplate(ABC):
    """
    Abstract base class for research templates.

    Each template defines:
    - How to generate search queries
    - How to extract findings from sources
    - What perspectives to apply
    - How to structure the final report
    """

    template_id: str = "base"
    template_name: str = "Base Research"
    description: str = "Base research template"

    # Default perspectives for this template
    default_perspectives: List[str] = ["historical", "economic", "political"]

    # Resource limits
    default_max_searches: int = 5
    default_max_sources_per_search: int = 10

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_research_model

    @abstractmethod
    async def generate_search_queries(
        self,
        query: str,
        parameters: ResearchParameters,
    ) -> List[str]:
        """
        Generate search queries based on the user's research question.

        Args:
            query: The user's research question
            parameters: Research parameters (depth, scope, etc.)

        Returns:
            List of search queries to execute
        """
        pass

    @abstractmethod
    async def extract_findings(
        self,
        query: str,
        sources: List[Source],
        synthesized_content: str,
        parameters: ResearchParameters,
    ) -> List[Finding]:
        """
        Extract structured findings from sources.

        Args:
            query: Original research question
            sources: Assessed sources with credibility scores
            synthesized_content: Combined synthesized content from searches
            parameters: Research parameters

        Returns:
            List of extracted findings
        """
        pass

    async def _call_gemini_json(self, prompt: str) -> dict:
        """Call Gemini with JSON response format."""
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=config,
        )

        import json
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            text = response.text
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
            return {}

    def get_query_generation_prompt(self, query: str, max_searches: int) -> str:
        """Get the prompt for generating search queries."""
        return f"""
You are a research strategist. Given the following research question,
generate {max_searches} search queries that would help gather comprehensive information.

Research Question: {query}

Guidelines:
1. Start with broad queries to understand the landscape
2. Include specific queries for key entities/events mentioned
3. Include queries for different perspectives (if applicable)
4. Include queries for recent news/developments
5. Include queries for authoritative/academic sources

Return a JSON array of search query strings. Example:
["query 1", "query 2", "query 3"]
"""

    def get_finding_extraction_prompt(
        self,
        query: str,
        source_content: str,
    ) -> str:
        """Get the prompt for extracting findings."""
        return f"""
Extract key findings from the following content that are relevant to the research question.

Research Question: {query}

Content:
{source_content}

For each finding, provide:
1. finding_type: One of 'fact', 'claim', 'event', 'actor', 'relationship', 'pattern', 'gap', 'evidence'
2. content: The full finding text with specific details
3. summary: One-sentence summary
4. confidence_score: 0.0-1.0 based on source quality and specificity
5. temporal_context: One of 'past', 'present', 'ongoing', 'prediction'

Return as JSON array. Example:
[
  {{
    "finding_type": "fact",
    "content": "Detailed finding...",
    "summary": "Brief summary",
    "confidence_score": 0.85,
    "temporal_context": "present"
  }}
]
"""
