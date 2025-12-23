"""Multi-perspective analysis service."""

from typing import List, Optional

from ..schemas import Finding, Source, Perspective
from ..personas import get_persona, PERSONA_REGISTRY


class MultiPerspectiveAnalyzer:
    """
    Runs analysis through multiple expert persona lenses.

    Coordinates the analysis across different perspectives and
    synthesizes insights from each.
    """

    def __init__(self):
        self.available_perspectives = list(PERSONA_REGISTRY.keys())

    async def analyze(
        self,
        perspective_type: str,
        findings: List[Finding],
        sources: List[Source],
        original_query: str,
    ) -> Perspective:
        """
        Analyze from a single perspective.

        Args:
            perspective_type: The type of perspective to apply
            findings: Extracted findings to analyze
            sources: Sources to reference
            original_query: The original research question

        Returns:
            Perspective with analysis and insights
        """
        persona = get_persona(perspective_type)
        return await persona.analyze(
            query=original_query,
            findings=findings,
            sources=sources,
        )

    async def analyze_all(
        self,
        findings: List[Finding],
        sources: List[Source],
        original_query: str,
        perspectives: Optional[List[str]] = None,
    ) -> List[Perspective]:
        """
        Analyze from multiple perspectives.

        Args:
            findings: Extracted findings to analyze
            sources: Sources to reference
            original_query: The original research question
            perspectives: List of perspectives to apply (default: all)

        Returns:
            List of Perspectives from each analysis
        """
        perspectives_to_run = perspectives or self.available_perspectives

        results = []
        for perspective_type in perspectives_to_run:
            if perspective_type in PERSONA_REGISTRY:
                perspective = await self.analyze(
                    perspective_type=perspective_type,
                    findings=findings,
                    sources=sources,
                    original_query=original_query,
                )
                results.append(perspective)

        return results

    def get_available_perspectives(self) -> List[dict]:
        """Get information about available perspectives."""
        return [
            {
                "id": persona_id,
                "name": persona.persona_name,
                "description": persona.description,
                "expertise_areas": persona.expertise_areas,
            }
            for persona_id, persona in PERSONA_REGISTRY.items()
        ]

    async def synthesize_perspectives(
        self,
        perspectives: List[Perspective],
        original_query: str,
    ) -> dict:
        """
        Synthesize insights from multiple perspectives into a unified view.

        Args:
            perspectives: List of perspective analyses
            original_query: The original research question

        Returns:
            Synthesized summary with cross-cutting themes
        """
        # Collect all insights
        all_insights = []
        all_recommendations = []
        all_warnings = []

        for p in perspectives:
            all_insights.extend([
                {"perspective": p.perspective_type, "insight": i}
                for i in p.key_insights
            ])
            all_recommendations.extend([
                {"perspective": p.perspective_type, "recommendation": r}
                for r in p.recommendations
            ])
            all_warnings.extend([
                {"perspective": p.perspective_type, "warning": w}
                for w in p.warnings
            ])

        # Calculate average confidence
        avg_confidence = sum(p.confidence for p in perspectives) / len(perspectives) if perspectives else 0.5

        return {
            "query": original_query,
            "perspectives_analyzed": [p.perspective_type for p in perspectives],
            "total_insights": len(all_insights),
            "cross_cutting_themes": self._identify_themes(all_insights),
            "consolidated_recommendations": all_recommendations,
            "consolidated_warnings": all_warnings,
            "overall_confidence": avg_confidence,
        }

    def _identify_themes(self, insights: List[dict]) -> List[str]:
        """Identify cross-cutting themes from insights (basic implementation)."""
        # This is a simple implementation - could be enhanced with LLM
        themes = []

        # Count perspective mentions per insight keyword
        keywords_by_perspective = {}
        for item in insights:
            perspective = item["perspective"]
            insight = item["insight"].lower()

            # Extract simple keywords (words > 5 chars)
            words = [w for w in insight.split() if len(w) > 5]
            for word in words:
                if word not in keywords_by_perspective:
                    keywords_by_perspective[word] = set()
                keywords_by_perspective[word].add(perspective)

        # Find words mentioned by multiple perspectives
        for word, perspectives in keywords_by_perspective.items():
            if len(perspectives) >= 2:
                themes.append(f"Cross-perspective theme: {word}")

        return themes[:5]  # Return top 5 themes
