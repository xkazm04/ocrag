"""Deduplication service for post-processing findings.

Compares new findings against existing knowledge base and decides
whether to POST (new), PUT (update), or DISCARD (duplicate).
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
import json

from ..db import SupabaseResearchDB
from ..schemas import Finding
from ..schemas.jobs import (
    DeduplicationDecision,
    DeduplicationAction,
    MergeStrategy,
    DedupStats,
)

logger = logging.getLogger(__name__)


class FindingDeduplicator:
    """Deduplicates new findings against existing knowledge base."""

    def __init__(
        self,
        db: SupabaseResearchDB,
        inference_client,  # InferenceClient from tests/research
    ):
        self.db = db
        self.client = inference_client

    async def deduplicate_findings(
        self,
        new_findings: List[Finding],
        topic_id: Optional[UUID],
        session_id: Optional[UUID] = None,
    ) -> List[DeduplicationDecision]:
        """
        Compare new findings with existing and return decisions.

        Args:
            new_findings: List of newly extracted findings
            topic_id: Matched topic ID (if any)
            session_id: Current research session ID

        Returns:
            List of DeduplicationDecision for each finding
        """
        if not new_findings:
            return []

        if not topic_id:
            # No topic match - all findings are new
            return [
                DeduplicationDecision(
                    finding_id=str(f.id) if hasattr(f, 'id') and f.id else f"new_{i}",
                    action=DeduplicationAction.POST,
                    reasoning="No existing topic to deduplicate against"
                )
                for i, f in enumerate(new_findings)
            ]

        # Get existing findings for the topic
        try:
            existing_findings = await self._get_existing_findings(topic_id)
        except Exception as e:
            # On error, treat all as new
            return [
                DeduplicationDecision(
                    finding_id=str(f.id) if hasattr(f, 'id') and f.id else f"new_{i}",
                    action=DeduplicationAction.POST,
                    reasoning=f"Failed to fetch existing findings: {e}"
                )
                for i, f in enumerate(new_findings)
            ]

        if not existing_findings:
            return [
                DeduplicationDecision(
                    finding_id=str(f.id) if hasattr(f, 'id') and f.id else f"new_{i}",
                    action=DeduplicationAction.POST,
                    reasoning="No existing findings in topic"
                )
                for i, f in enumerate(new_findings)
            ]

        # Compare in batches using LLM
        decisions = []
        batch_size = 5

        for i in range(0, len(new_findings), batch_size):
            batch = new_findings[i:i + batch_size]
            batch_decisions = await self._compare_batch(
                batch,
                existing_findings,
                start_index=i
            )
            decisions.extend(batch_decisions)

        return decisions

    async def _get_existing_findings(
        self,
        topic_id: UUID,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get existing findings for a topic."""
        # Try to get claims by topic
        try:
            claims = await self.db.get_claims_by_topic(topic_id, limit=limit)
            return [
                {
                    "id": str(c.id),
                    "content": c.content,
                    "summary": c.summary,
                    "event_date": str(c.event_date) if c.event_date else None,
                }
                for c in claims
            ]
        except Exception:
            logger.warning("Failed to get existing claims for topic_id=%s", topic_id)
            return []

    async def _compare_batch(
        self,
        new_findings: List[Finding],
        existing_findings: List[Dict[str, Any]],
        start_index: int = 0,
    ) -> List[DeduplicationDecision]:
        """Compare a batch of new findings against existing using LLM."""
        # Build comparison text
        new_text = "\n".join([
            f"[NEW-{start_index + i}] Type: {getattr(f, 'finding_type', 'unknown')}, "
            f"Date: {getattr(f, 'event_date', 'N/A')}, "
            f"Content: {(f.content if hasattr(f, 'content') else str(f))[:300]}"
            for i, f in enumerate(new_findings)
        ])

        existing_text = "\n".join([
            f"[EXIST-{f['id'][:8]}] Date: {f.get('event_date', 'N/A')}, "
            f"Content: {f.get('content', '')[:300]}"
            for f in existing_findings[:25]  # Limit to prevent token overflow
        ])

        prompt = f"""Compare these NEW findings against EXISTING findings and decide what to do with each new finding.

NEW FINDINGS (to be processed):
{new_text}

EXISTING FINDINGS (already in database):
{existing_text}

For each NEW finding, decide:
- POST: New unique information not in existing findings - should be added
- PUT: Updates or expands an existing finding - specify which one and how to merge
- DISCARD: Duplicate or redundant - already covered by existing findings

Merge strategies for PUT:
- "replace": New finding is more accurate/complete than existing
- "append": Add new details to existing finding
- "merge": Combine complementary information

Return ONLY a JSON array (no markdown):
[
    {{
        "finding_id": "NEW-0",
        "action": "POST" | "PUT" | "DISCARD",
        "existing_finding_id": "full-uuid-if-PUT" | null,
        "merge_strategy": "replace" | "append" | "merge" | null,
        "reasoning": "Brief explanation"
    }},
    ...
]

Be conservative - prefer POST for genuinely new information.
Only DISCARD if it's clearly a duplicate of existing content.
"""

        try:
            result, _ = await self.client.generate_json(
                prompt,
                system_prompt="You are a knowledge curator ensuring data quality through deduplication. Be precise and conservative.",
                temperature=0.2,
            )

            decisions = []
            if result and isinstance(result, list):
                for i, decision in enumerate(result):
                    if i < len(new_findings):
                        finding = new_findings[i]
                        finding_id = str(finding.id) if hasattr(finding, 'id') and finding.id else f"new_{start_index + i}"

                        # Parse action
                        action_str = decision.get("action", "POST").upper()
                        try:
                            action = DeduplicationAction(action_str)
                        except ValueError:
                            action = DeduplicationAction.POST

                        # Parse merge strategy
                        merge_str = decision.get("merge_strategy")
                        merge_strategy = None
                        if merge_str and action == DeduplicationAction.PUT:
                            try:
                                merge_strategy = MergeStrategy(merge_str.lower())
                            except ValueError:
                                merge_strategy = MergeStrategy.APPEND

                        # Parse existing finding ID
                        existing_id = None
                        if decision.get("existing_finding_id") and action == DeduplicationAction.PUT:
                            try:
                                existing_id = UUID(decision["existing_finding_id"])
                            except (ValueError, TypeError):
                                pass

                        decisions.append(DeduplicationDecision(
                            finding_id=finding_id,
                            action=action,
                            existing_finding_id=existing_id,
                            merge_strategy=merge_strategy,
                            reasoning=decision.get("reasoning", ""),
                        ))

            # Ensure we have decisions for all findings
            while len(decisions) < len(new_findings):
                idx = len(decisions)
                finding = new_findings[idx]
                decisions.append(DeduplicationDecision(
                    finding_id=str(finding.id) if hasattr(finding, 'id') and finding.id else f"new_{start_index + idx}",
                    action=DeduplicationAction.POST,
                    reasoning="Fallback decision - treating as new"
                ))

            return decisions

        except Exception as e:
            # On LLM error, treat all as new
            return [
                DeduplicationDecision(
                    finding_id=str(f.id) if hasattr(f, 'id') and f.id else f"new_{start_index + i}",
                    action=DeduplicationAction.POST,
                    reasoning=f"LLM comparison failed: {e}"
                )
                for i, f in enumerate(new_findings)
            ]

    async def execute_decisions(
        self,
        decisions: List[DeduplicationDecision],
        findings: List[Finding],
        session_id: UUID,
    ) -> DedupStats:
        """
        Execute deduplication decisions and return stats.

        Args:
            decisions: List of decisions from deduplicate_findings
            findings: Original findings list
            session_id: Research session ID for linking

        Returns:
            DedupStats with counts of new, updated, discarded
        """
        stats = DedupStats(new=0, updated=0, discarded=0)

        # Create a mapping from finding_id to finding
        findings_map = {}
        for i, f in enumerate(findings):
            fid = str(f.id) if hasattr(f, 'id') and f.id else f"new_{i}"
            findings_map[fid] = f

        for decision in decisions:
            finding = findings_map.get(decision.finding_id)
            if not finding:
                continue

            try:
                if decision.action == DeduplicationAction.POST:
                    # Finding should already be saved during research
                    # Just count it as new
                    stats.new += 1

                elif decision.action == DeduplicationAction.PUT:
                    if decision.existing_finding_id:
                        await self._merge_findings(
                            finding,
                            decision.existing_finding_id,
                            decision.merge_strategy or MergeStrategy.APPEND
                        )
                        stats.updated += 1
                    else:
                        # No existing ID specified, treat as new
                        stats.new += 1

                elif decision.action == DeduplicationAction.DISCARD:
                    # Optionally: mark finding as duplicate in DB
                    # For now, just count it
                    stats.discarded += 1

            except Exception:
                logger.warning("Error applying dedup decision, treating as new")
                stats.new += 1

        return stats

    async def _merge_findings(
        self,
        new_finding: Finding,
        existing_id: UUID,
        strategy: MergeStrategy,
    ) -> None:
        """Merge new finding into existing."""
        try:
            existing = await self.db.get_finding(existing_id)
            if not existing:
                return

            updates: Dict[str, Any] = {}
            new_content = new_finding.content if hasattr(new_finding, 'content') else str(new_finding)
            new_summary = getattr(new_finding, 'summary', None)

            if strategy == MergeStrategy.REPLACE:
                updates["content"] = new_content
                if new_summary:
                    updates["summary"] = new_summary

            elif strategy == MergeStrategy.APPEND:
                updates["content"] = f"{existing.content}\n\n[Additional info] {new_content}"

            elif strategy == MergeStrategy.MERGE:
                # More sophisticated merge
                updates["content"] = f"{existing.content}\n\n{new_content}"
                # Keep higher confidence if available
                new_conf = getattr(new_finding, 'confidence_score', 0)
                if new_conf and new_conf > (existing.confidence_score or 0):
                    updates["confidence_score"] = new_conf

            if updates:
                # Update the finding in DB
                # Note: This assumes update_finding method exists
                try:
                    await self.db._findings.update_finding(existing_id, updates)
                except AttributeError:
                    # If method doesn't exist, use direct client
                    self.db.client.table("research_findings").update(updates).eq(
                        "id", str(existing_id)
                    ).execute()

        except Exception:
            # Merge is best effort - log and continue
            logger.info("Finding merge failed for existing_id=%s, strategy=%s", existing_id, strategy)
