"""Data aggregator for report generation."""

from typing import Optional, List, Dict, Any
from uuid import UUID

from ...db import SupabaseResearchDB
from ..schemas import ReportData


class ReportDataAggregator:
    """Aggregates research data for report generation."""

    def __init__(self, db: SupabaseResearchDB):
        self.db = db

    async def aggregate(self, session_id: UUID) -> ReportData:
        """
        Aggregate all data needed for report generation.

        Fetches:
        - Session metadata
        - All findings
        - All perspectives
        - All sources
        - Related knowledge claims (if any)
        """
        # Fetch session
        session = await self.db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Fetch findings
        findings = await self._fetch_findings(session_id)

        # Fetch perspectives
        perspectives = await self._fetch_perspectives(session_id)

        # Fetch sources
        sources = await self._fetch_sources(session_id)

        # Fetch related claims (if promoted to knowledge base)
        claims = await self._fetch_claims(session_id)

        return ReportData(
            session_id=session.id,
            session_title=session.title or session.query[:50],
            session_query=session.query,
            template_type=session.template_type or "investigative",
            status=session.status,
            parameters=session.parameters or {},
            created_at=session.created_at,
            completed_at=session.completed_at,
            findings=findings,
            perspectives=perspectives,
            sources=sources,
            claims=claims,
        )

    async def _fetch_findings(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Fetch all findings for a session."""
        try:
            result = self.db.client.table("research_findings").select(
                "id, finding_type, content, summary, confidence_score, "
                "temporal_context, event_date, supporting_sources, extracted_data, created_at"
            ).eq("session_id", str(session_id)).order(
                "confidence_score", desc=True
            ).execute()
            return result.data or []
        except Exception:
            return []

    async def _fetch_perspectives(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Fetch all perspectives for a session."""
        try:
            result = self.db.client.table("research_perspectives").select(
                "id, perspective_type, analysis_text, key_insights, confidence, "
                "recommendations, warnings, created_at"
            ).eq("session_id", str(session_id)).execute()
            return result.data or []
        except Exception:
            return []

    async def _fetch_sources(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Fetch all sources for a session."""
        try:
            result = self.db.client.table("research_sources").select(
                "id, url, title, domain, snippet, credibility_score, "
                "credibility_factors, source_type, content_date, created_at"
            ).eq("session_id", str(session_id)).order(
                "credibility_score", desc=True
            ).execute()
            return result.data or []
        except Exception:
            return []

    async def _fetch_claims(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Fetch knowledge claims linked to this session's findings."""
        try:
            # First get finding IDs for this session
            findings_result = self.db.client.table("research_findings").select(
                "id"
            ).eq("session_id", str(session_id)).execute()

            if not findings_result.data:
                return []

            finding_ids = [f["id"] for f in findings_result.data]

            # Then get claims linked to these findings
            claims_result = self.db.client.table("finding_claims").select(
                "claim_id"
            ).in_("finding_id", finding_ids).execute()

            if not claims_result.data:
                return []

            claim_ids = list(set(c["claim_id"] for c in claims_result.data))

            # Finally fetch the claims
            result = self.db.client.table("knowledge_claims").select(
                "id, claim_type, content, summary, confidence_score, "
                "verification_status, tags, temporal_context, created_at"
            ).in_("id", claim_ids).execute()

            return result.data or []
        except Exception:
            return []
