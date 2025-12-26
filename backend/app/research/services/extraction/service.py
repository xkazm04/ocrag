"""Evidence extraction service for documents.

Extracts findings from text or PDF documents with quality filtering,
web context search, and deduplication against existing claims.
"""

import hashlib
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4

from ...db import SupabaseResearchDB
from ...lib.clients import GeminiResearchClient
from ...schemas.verification import (
    ExtractEvidenceRequest,
    ExtractEvidenceResponse,
    ExtractedFinding,
    ExtractionStats,
    FindingQuality,
)
from .quality_filter import QualityFilter

logger = logging.getLogger(__name__)


class EvidenceExtractionService:
    """Extracts findings from documents with quality filtering."""

    def __init__(self, db: SupabaseResearchDB):
        self.db = db
        self._gemini_research = None
        self._gemini_core = None

    async def _get_gemini_research(self):
        """Lazy load Gemini research client for web search."""
        if self._gemini_research is None:
            try:
                self._gemini_research = GeminiResearchClient()
            except (ImportError, ValueError) as e:
                logger.warning("Could not create GeminiResearchClient: %s", e)
        return self._gemini_research

    async def _get_gemini_core(self):
        """Lazy load Gemini core client for PDF processing."""
        if self._gemini_core is None:
            try:
                from app.core.gemini_client import get_gemini_client
                self._gemini_core = get_gemini_client()
            except ImportError as e:
                logger.warning("Could not load core Gemini client: %s", e)
        return self._gemini_core

    def _hash_document(self, content: str) -> str:
        """Create hash for document tracking."""
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    async def extract_evidence(
        self,
        topic_id: UUID,
        document_text: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        options: Optional[ExtractEvidenceRequest] = None,
    ) -> ExtractEvidenceResponse:
        """
        Extract evidence from a document.

        Steps:
        1. Process document (text or PDF via ocr_pdf)
        2. Gemini extracts structured findings
        3. Quality filter (confidence, length, vagueness)
        4. Web context search for high-quality findings (optional)
        5. Compare against existing claims (deduplication)
        6. Run perspective analysis on valuable findings (optional)
        7. Return JSON with POST/PUT/SKIP decisions
        """
        start_time = datetime.utcnow()
        options = options or ExtractEvidenceRequest(topic_id=topic_id)
        errors = []
        warnings = []

        # Get topic info
        topic_name = await self._get_topic_name(topic_id)
        if not topic_name:
            warnings.append(f"Topic {topic_id} not found, using generic extraction")

        # Step 1: Get document content
        if pdf_bytes:
            try:
                gemini_core = await self._get_gemini_core()
                if gemini_core:
                    result = await gemini_core.ocr_pdf(pdf_bytes)
                    document_text = result.get("content", "")
                else:
                    errors.append("PDF processing not available")
                    return self._error_response(topic_id, topic_name, errors, start_time)
            except Exception as e:
                errors.append(f"PDF processing failed: {e}")
                return self._error_response(topic_id, topic_name, errors, start_time)

        if not document_text or len(document_text.strip()) < 50:
            errors.append("Document content is empty or too short")
            return self._error_response(topic_id, topic_name, errors, start_time)

        document_hash = self._hash_document(document_text)
        document_preview = document_text[:500]

        # Step 2: Extract findings using Gemini
        gemini = await self._get_gemini_research()
        if not gemini:
            errors.append("Gemini client not available")
            return self._error_response(topic_id, topic_name, errors, start_time)

        raw_findings = await self._extract_findings(gemini, document_text, topic_name, options.max_findings)

        if not raw_findings:
            warnings.append("No findings extracted from document")

        # Step 3: Quality filter
        quality_filter = QualityFilter(min_confidence=options.min_confidence_threshold)
        filtered_findings = []
        filtered_out_count = 0

        for finding in raw_findings:
            quality, reasons = quality_filter.evaluate(finding)
            finding["quality"] = quality
            finding["quality_reasons"] = reasons

            if quality != FindingQuality.FILTERED:
                filtered_findings.append(finding)
            else:
                filtered_out_count += 1

        # Step 4: Web context search (optional)
        if options.run_web_context_search:
            for finding in filtered_findings:
                if finding["quality"] in (FindingQuality.HIGH, FindingQuality.MEDIUM):
                    context, sources = await self._search_web_context(gemini, finding)
                    finding["web_context"] = context
                    finding["web_sources"] = sources

        # Step 5: Deduplication against existing claims
        existing_claims = []
        if options.check_existing_claims:
            existing_claims = await self._get_existing_claims(topic_id)

        decisions = await self._generate_dedup_decisions(
            filtered_findings,
            existing_claims,
            gemini
        )

        # Step 6: Perspective analysis (optional)
        perspectives_count = 0
        if options.run_perspective_analysis:
            for finding in decisions:
                if finding["quality"] == FindingQuality.HIGH and finding["action"] != "SKIP":
                    perspectives = await self._run_perspective_analysis(finding, topic_name)
                    finding["perspectives"] = perspectives
                    if perspectives:
                        perspectives_count += 1

        # Build response
        extraction_id = uuid4()
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Convert to ExtractedFinding objects
        extracted_findings = [
            ExtractedFinding(
                finding_id=f["finding_id"],
                content=f["content"],
                summary=f.get("summary"),
                finding_type=f.get("finding_type", "fact"),
                confidence_score=f.get("confidence_score", 0.7),
                quality=f["quality"],
                quality_reasons=f.get("quality_reasons", []),
                action=f["action"],
                existing_claim_id=f.get("existing_claim_id"),
                merge_strategy=f.get("merge_strategy"),
                dedup_reasoning=f.get("dedup_reasoning"),
                web_context=f.get("web_context"),
                web_sources=f.get("web_sources", []),
                perspectives=f.get("perspectives", []),
            )
            for f in decisions
        ]

        stats = ExtractionStats(
            total_extracted=len(raw_findings),
            passed_quality_filter=len(filtered_findings),
            filtered_out=filtered_out_count,
            new_findings=sum(1 for f in decisions if f["action"] == "POST"),
            update_findings=sum(1 for f in decisions if f["action"] == "PUT"),
            skip_findings=sum(1 for f in decisions if f["action"] == "SKIP"),
            perspectives_generated=perspectives_count,
            processing_time_ms=processing_time_ms,
        )

        # Save extraction record
        await self._save_extraction_record(
            extraction_id=extraction_id,
            topic_id=topic_id,
            document_type="pdf" if pdf_bytes else "text",
            document_hash=document_hash,
            document_preview=document_preview,
            stats=stats,
            workspace_id=options.workspace_id,
        )

        return ExtractEvidenceResponse(
            extraction_id=extraction_id,
            topic_id=topic_id,
            topic_name=topic_name,
            status="completed",
            findings=extracted_findings,
            stats=stats,
            errors=errors,
            warnings=warnings,
        )

    def _error_response(
        self,
        topic_id: UUID,
        topic_name: Optional[str],
        errors: List[str],
        start_time: datetime
    ) -> ExtractEvidenceResponse:
        """Build error response."""
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return ExtractEvidenceResponse(
            extraction_id=uuid4(),
            topic_id=topic_id,
            topic_name=topic_name,
            status="failed",
            findings=[],
            stats=ExtractionStats(processing_time_ms=processing_time_ms),
            errors=errors,
            warnings=[],
        )

    async def _get_topic_name(self, topic_id: UUID) -> Optional[str]:
        """Get topic name from database."""
        try:
            result = self.db.client.table("knowledge_topics").select(
                "name"
            ).eq("id", str(topic_id)).single().execute()
            return result.data.get("name") if result.data else None
        except Exception:
            return None

    async def _extract_findings(
        self,
        gemini,
        document_text: str,
        topic_name: Optional[str],
        max_findings: int
    ) -> List[Dict[str, Any]]:
        """Extract structured findings from document."""
        topic_context = f" related to '{topic_name}'" if topic_name else ""

        prompt = f"""Extract factual findings from this document{topic_context}.

DOCUMENT:
{document_text[:15000]}

For each finding, provide:
- content: The specific factual claim or finding (detailed, specific)
- summary: Brief one-line summary
- finding_type: "fact", "claim", "statistic", "quote", "event", "relationship"
- confidence_score: 0.0-1.0 based on how well-supported the finding is
- event_date: Date when the event/fact occurred in YYYY-MM-DD format, or null if not mentioned or unclear
- temporal_context: "past", "present", "ongoing", or "prediction"

IMPORTANT: Extract dates mentioned in the document. Look for:
- Explicit dates (e.g., "on March 15, 2005", "in 2008")
- Relative dates that can be resolved (e.g., "last year" if document date is known)
- Time ranges (use the start date for event_date)

Return as JSON array of objects. Extract up to {max_findings} most significant findings.
Focus on specific, verifiable claims with dates, names, numbers when available.
Avoid vague or general statements."""

        try:
            parsed, response = await gemini.generate_json(prompt, temperature=0.3)

            if parsed and isinstance(parsed, list):
                findings = []
                for i, f in enumerate(parsed[:max_findings]):
                    findings.append({
                        "finding_id": f"f_{i+1}",
                        "content": f.get("content", ""),
                        "summary": f.get("summary"),
                        "finding_type": f.get("finding_type", "fact"),
                        "confidence_score": float(f.get("confidence_score", 0.7)),
                        "event_date": f.get("event_date"),
                        "temporal_context": f.get("temporal_context"),
                    })
                return findings
        except Exception:
            pass

        return []

    async def _search_web_context(
        self,
        gemini,
        finding: Dict[str, Any]
    ) -> Tuple[Optional[str], List[Dict[str, str]]]:
        """Search web for context on a finding."""
        content = finding.get("content", "")
        if len(content) < 30:
            return None, []

        search_query = f"Verify: {content[:200]}"

        try:
            response = await gemini.grounded_search(search_query, temperature=0.3)

            context = response.text[:500] if response.text else None
            sources = [
                {"url": s.url, "title": s.title, "domain": s.domain}
                for s in response.sources[:3]
            ]
            return context, sources

        except Exception:
            return None, []

    async def _get_existing_claims(self, topic_id: UUID) -> List[Dict[str, Any]]:
        """Get existing claims for the topic."""
        try:
            result = self.db.client.table("knowledge_claims").select(
                "id, content, verification_status, confidence_score"
            ).eq("topic_id", str(topic_id)).limit(50).execute()

            return result.data or []
        except Exception:
            return []

    async def _generate_dedup_decisions(
        self,
        findings: List[Dict[str, Any]],
        existing_claims: List[Dict[str, Any]],
        gemini
    ) -> List[Dict[str, Any]]:
        """Generate deduplication decisions for each finding."""
        if not existing_claims:
            for f in findings:
                f["action"] = "POST"
                f["dedup_reasoning"] = "No existing claims to compare against"
            return findings

        claims_context = "\n".join([
            f"ID:{c['id']} - {c['content'][:150]}"
            for c in existing_claims[:30]
        ])

        for finding in findings:
            prompt = f"""Compare this new finding against existing claims and decide action.

NEW FINDING:
{finding['content']}

EXISTING CLAIMS:
{claims_context}

Decide:
- POST: New unique information, not covered by existing claims
- PUT: Updates/enhances an existing claim (specify which one and merge strategy)
- SKIP: Duplicate of existing claim, no new value

Respond with JSON:
{{
    "action": "POST" or "PUT" or "SKIP",
    "existing_claim_id": "uuid if PUT, null otherwise",
    "merge_strategy": "replace" or "append" or "merge" if PUT,
    "reasoning": "brief explanation"
}}"""

            try:
                parsed, _ = await gemini.generate_json(prompt, temperature=0.2)
                if parsed:
                    finding["action"] = parsed.get("action", "POST")
                    if finding["action"] == "PUT":
                        existing_id = parsed.get("existing_claim_id")
                        if existing_id:
                            finding["existing_claim_id"] = UUID(existing_id)
                        finding["merge_strategy"] = parsed.get("merge_strategy", "merge")
                    finding["dedup_reasoning"] = parsed.get("reasoning", "")
                else:
                    finding["action"] = "POST"
                    finding["dedup_reasoning"] = "Could not parse deduplication response"
            except Exception:
                finding["action"] = "POST"
                finding["dedup_reasoning"] = "Deduplication failed, defaulting to POST"

        return findings

    async def _run_perspective_analysis(
        self,
        finding: Dict[str, Any],
        topic_name: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Run perspective analysis on a finding."""
        gemini = await self._get_gemini_research()
        if not gemini:
            return []

        content = finding.get("content", "")
        topic_context = f" in the context of {topic_name}" if topic_name else ""

        prompt = f"""Analyze this finding from multiple perspectives{topic_context}:

FINDING:
{content}

Provide 2-3 different perspectives on this finding. For each perspective:
- perspective_type: "historical", "political", "economic", "social", "technical", "ethical"
- analysis: Brief analysis from this perspective
- key_insight: Main insight from this viewpoint
- implications: What this means

Return as JSON array."""

        try:
            parsed, _ = await gemini.generate_json(prompt, temperature=0.4)
            if parsed and isinstance(parsed, list):
                return [
                    {
                        "perspective_type": p.get("perspective_type", "unknown"),
                        "analysis": p.get("analysis", ""),
                        "key_insight": p.get("key_insight", ""),
                        "implications": p.get("implications", ""),
                    }
                    for p in parsed[:3]
                ]
        except Exception:
            pass

        return []

    async def _save_extraction_record(
        self,
        extraction_id: UUID,
        topic_id: UUID,
        document_type: str,
        document_hash: str,
        document_preview: str,
        stats: ExtractionStats,
        workspace_id: str,
    ):
        """Save extraction record to database."""
        try:
            self.db.client.table("document_extractions").insert({
                "id": str(extraction_id),
                "topic_id": str(topic_id),
                "document_type": document_type,
                "document_hash": document_hash,
                "document_preview": document_preview[:500],
                "status": "completed",
                "findings_count": stats.total_extracted,
                "quality_filtered_count": stats.filtered_out,
                "new_findings": stats.new_findings,
                "updated_findings": stats.update_findings,
                "skipped_findings": stats.skip_findings,
                "processing_time_ms": stats.processing_time_ms,
                "workspace_id": workspace_id,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            print(f"Warning: Failed to save extraction record: {e}")
