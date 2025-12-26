"""Topic matching service using LLM.

Matches research queries to existing knowledge topics before decomposition
to provide context about what's already known.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from ..db import SupabaseResearchDB
from ..schemas import KnowledgeTopic
from ..schemas.jobs import TopicMatchResult, TopicContext

logger = logging.getLogger(__name__)


class TopicMatcher:
    """Matches queries to existing knowledge topics using LLM."""

    def __init__(
        self,
        db: SupabaseResearchDB,
        inference_client,  # InferenceClient from tests/research
    ):
        self.db = db
        self.client = inference_client

    async def match_topic(
        self,
        query: str,
        workspace_id: str = "default",
    ) -> TopicMatchResult:
        """
        Match query against existing topics using LLM.

        Args:
            query: The research query
            workspace_id: Workspace to search in

        Returns:
            TopicMatchResult with topic_id (if matched), confidence, reasoning
        """
        # Fetch existing topics
        try:
            topics = await self.db.list_topics()
        except Exception as e:
            logger.error("Failed to fetch topics for matching: %s", e, exc_info=True)
            return TopicMatchResult(
                topic_id=None,
                confidence=0.0,
                reasoning=f"Failed to fetch topics: {e}"
            )

        if not topics:
            return TopicMatchResult(
                topic_id=None,
                confidence=0.0,
                reasoning="No existing topics in database"
            )

        # Build topic list for LLM (limit to prevent token overflow)
        topics_list = topics[:50]
        topics_text = "\n".join([
            f"- ID: {t.id}, Name: {t.name}, Description: {t.description or 'N/A'}, Type: {t.topic_type or 'N/A'}"
            for t in topics_list
        ])

        prompt = f"""Analyze this research query and determine if it matches any existing topics.

QUERY: "{query}"

EXISTING TOPICS:
{topics_text}

Your task:
1. Determine if the query is semantically related to any existing topic
2. Consider: same subject matter, related entities, same time period, subtopic relationships
3. A match should indicate we already have research on this topic

Return ONLY a JSON object (no markdown, no explanation):
{{
    "topic_id": "uuid-string-if-match-found-or-null",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation of why this matches or doesn't match"
}}

Rules:
- Only match if confidence >= 0.7
- Return null for topic_id if no good match exists
- Consider partial matches (e.g., query about specific event matching broader topic)
- Don't match if the query is only tangentially related
"""

        try:
            result, _ = await self.client.generate_json(
                prompt,
                system_prompt="You are a knowledge base curator matching queries to existing topics. Be precise and only match when confident.",
                temperature=0.2,
            )

            if result and result.get("topic_id") and result.get("confidence", 0) >= 0.7:
                return TopicMatchResult(
                    topic_id=UUID(result["topic_id"]),
                    confidence=float(result.get("confidence", 0.0)),
                    reasoning=result.get("reasoning", "")
                )

            return TopicMatchResult(
                topic_id=None,
                confidence=float(result.get("confidence", 0.0)) if result else 0.0,
                reasoning=result.get("reasoning", "No matching topic found") if result else "LLM returned no result"
            )

        except Exception as e:
            logger.warning("Topic matching LLM call failed: %s", e)
            return TopicMatchResult(
                topic_id=None,
                confidence=0.0,
                reasoning=f"Topic matching failed: {e}"
            )

    async def get_topic_context(
        self,
        topic_id: UUID,
    ) -> TopicContext:
        """
        Get existing knowledge context for a topic.

        This context will be provided to the query decomposer so it knows
        what information already exists and can focus on gaps.

        Args:
            topic_id: The matched topic ID

        Returns:
            TopicContext with existing claims, entities, date range
        """
        try:
            # Get topic info
            topic = await self.db.get_topic(topic_id)
            if not topic:
                return TopicContext(
                    topic_id=topic_id,
                    topic_name="Unknown",
                    existing_claims_count=0,
                )

            # Get existing claims/findings for the topic
            claims = await self.db.get_claims_by_topic(topic_id, limit=20)

            # Build context
            existing_summaries = [
                c.summary or c.content[:150]
                for c in claims[:15]
            ]

            # Get known entities (if available)
            known_entities = []
            # Could expand to fetch entities linked to claims

            # Determine date range from claims
            date_range = None
            dates = []
            for c in claims:
                if c.event_date:
                    dates.append(str(c.event_date))
            if dates:
                dates.sort()
                date_range = f"{dates[0]} to {dates[-1]}"

            return TopicContext(
                topic_id=topic_id,
                topic_name=topic.name,
                existing_claims_count=len(claims),
                existing_summaries=existing_summaries,
                known_entities=known_entities,
                date_range=date_range,
            )

        except Exception as e:
            logger.warning("Failed to get topic context for topic_id=%s: %s", topic_id, e)
            return TopicContext(
                topic_id=topic_id,
                topic_name="Unknown",
                existing_claims_count=0,
            )

    def build_context_prompt(self, context: TopicContext) -> str:
        """
        Build a prompt section describing existing knowledge.

        Args:
            context: The topic context

        Returns:
            Formatted string for inclusion in decomposition prompt
        """
        if context.existing_claims_count == 0:
            return ""

        lines = [
            f"\n## EXISTING KNOWLEDGE for topic '{context.topic_name}'",
            f"We already have {context.existing_claims_count} findings on this topic.",
        ]

        if context.existing_summaries:
            lines.append("\nKnown information includes:")
            for summary in context.existing_summaries[:10]:
                lines.append(f"- {summary}")

        if context.date_range:
            lines.append(f"\nCovered time period: {context.date_range}")

        lines.append("\nFocus your queries on NEW information not covered above.")

        return "\n".join(lines)
