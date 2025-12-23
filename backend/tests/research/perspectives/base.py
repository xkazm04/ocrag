"""Base Perspective Agent.

Provides the foundation for specialized perspective agents that
analyze research findings from different viewpoints.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Handle both relative and direct imports
try:
    from ..inference_client import InferenceClient
    from ..schemas.perspective import PerspectiveType, PerspectiveAnalysis
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from inference_client import InferenceClient
    from schemas.perspective import PerspectiveType, PerspectiveAnalysis


@dataclass
class PerspectiveContext:
    """Context provided to perspective agents for analysis."""

    # The overall research topic/query
    topic: str

    # Summary of all findings gathered
    topic_summary: str

    # List of finding summaries for reference
    finding_summaries: List[str] = field(default_factory=list)

    # Key actors identified
    actors: List[str] = field(default_factory=list)

    # Key events/dates identified
    events: List[str] = field(default_factory=list)

    # The specific finding being analyzed (for finding-level analysis)
    current_finding: Optional[str] = None
    current_finding_type: Optional[str] = None

    # Allow use of training data for judgment
    allow_training_data: bool = True


class BasePerspectiveAgent(ABC):
    """Base class for perspective analysis agents.

    Each perspective agent specializes in analyzing findings from
    a specific viewpoint, using domain expertise and training data
    to provide unique insights.
    """

    perspective_type: PerspectiveType
    name: str
    description: str

    # System prompt template for this perspective
    system_prompt: str

    def __init__(self, client: Optional[InferenceClient] = None):
        self.client = client or InferenceClient()

    @abstractmethod
    async def analyze_finding(
        self,
        finding_content: str,
        finding_type: str,
        context: PerspectiveContext,
    ) -> Dict[str, Any]:
        """Analyze a single finding from this perspective.

        Args:
            finding_content: The finding text to analyze
            finding_type: Type of finding (event, actor, etc.)
            context: Broader research context

        Returns:
            Dict with perspective-specific analysis fields
        """
        pass

    @abstractmethod
    async def analyze_topic(
        self,
        context: PerspectiveContext,
    ) -> PerspectiveAnalysis:
        """Provide overall perspective analysis of the topic.

        Args:
            context: Full research context

        Returns:
            PerspectiveAnalysis subclass for this perspective
        """
        pass

    def _build_context_prompt(self, context: PerspectiveContext) -> str:
        """Build context section for prompts."""
        parts = [f"RESEARCH TOPIC: {context.topic}"]

        if context.topic_summary:
            parts.append(f"\nTOPIC SUMMARY:\n{context.topic_summary}")

        if context.actors:
            parts.append(f"\nKEY ACTORS: {', '.join(context.actors[:10])}")

        if context.events:
            parts.append(f"\nKEY EVENTS: {', '.join(context.events[:10])}")

        if context.allow_training_data:
            parts.append(
                "\nNOTE: You may use your training data and domain knowledge "
                "to supplement the provided information."
            )

        return "\n".join(parts)

    async def _generate_analysis(
        self,
        prompt: str,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
        """Generate JSON analysis using the inference client."""
        result, _ = await self.client.generate_json(
            prompt,
            system_prompt=self.system_prompt,
            temperature=temperature,
        )
        return result or {}
