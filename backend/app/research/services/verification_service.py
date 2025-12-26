"""Verification service for fact-checking statements.

Uses Gemini grounded search + knowledge base lookup to verify claims.
Results are cached in verification_results table.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from ..lib.clients import GeminiResearchClient, InferenceClient

logger = logging.getLogger(__name__)

from ..db import SupabaseResearchDB
from ..schemas.verification import (
    VerifyStatementRequest,
    VerifyStatementResponse,
    VerificationVerdict,
    EvidenceItem,
    RelatedClaimSummary,
)


class VerificationService:
    """Fact-checks statements using Gemini + knowledge base."""

    def __init__(self, db: SupabaseResearchDB):
        self.db = db
        self._gemini = None
        self._inference = None

    async def _get_gemini_client(self):
        """Lazy load Gemini client."""
        if self._gemini is None:
            try:
                self._gemini = GeminiResearchClient()
            except (ImportError, ValueError) as e:
                logger.warning("Could not create GeminiResearchClient: %s", e)
                self._gemini = None
        return self._gemini

    async def _get_inference_client(self):
        """Lazy load inference client."""
        if self._inference is None:
            try:
                self._inference = InferenceClient()
            except (ImportError, ValueError) as e:
                logger.warning("Could not create InferenceClient: %s", e)
                self._inference = None
        return self._inference

    def _hash_statement(self, statement: str) -> str:
        """Create hash for statement caching."""
        normalized = statement.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    async def verify_statement(
        self,
        request: VerifyStatementRequest
    ) -> VerifyStatementResponse:
        """
        Verify/fact-check a statement.

        Steps:
        1. Check cache for existing verification
        2. Gemini grounded search for web evidence
        3. Query knowledge_claims for related facts
        4. LLM synthesizes verdict
        5. Cache result and return
        """
        start_time = datetime.utcnow()
        statement_hash = self._hash_statement(request.statement)

        # Step 1: Check cache
        if request.use_cache:
            cached = await self._get_cached_verification(
                statement_hash,
                request.workspace_id
            )
            if cached:
                # Update hit count
                await self._increment_hit_count(cached["id"])
                return self._build_response_from_cache(cached, start_time)

        # Step 2: Gemini grounded search for evidence
        gemini = await self._get_gemini_client()
        web_evidence = await self._search_web_evidence(gemini, request.statement)

        # Step 3: Query related claims from knowledge base
        related_claims = []
        related_claims_summary = None
        if request.include_related_claims:
            related_claims, related_claims_summary = await self._find_related_claims(
                request.statement,
                request.workspace_id
            )

        # Step 4: Synthesize verdict using LLM
        verdict, confidence, supporting, contradicting = await self._synthesize_verdict(
            request.statement,
            web_evidence,
            related_claims,
            gemini
        )

        # Step 5: Save to cache
        verification_id = uuid4()
        expires_at = datetime.utcnow() + timedelta(hours=request.cache_ttl_hours)

        await self._save_verification(
            verification_id=verification_id,
            statement=request.statement,
            statement_hash=statement_hash,
            verdict=verdict,
            confidence_score=confidence,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            related_claim_ids=[c.claim_id for c in related_claims],
            related_claims_summary=related_claims_summary,
            web_sources=web_evidence.get("sources", []),
            grounding_metadata=web_evidence.get("grounding_metadata"),
            expires_at=expires_at,
            workspace_id=request.workspace_id,
        )

        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return VerifyStatementResponse(
            verification_id=verification_id,
            statement=request.statement,
            verdict=verdict,
            confidence_score=confidence,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            related_claims=related_claims,
            related_claims_summary=related_claims_summary,
            sources_analyzed=len(web_evidence.get("sources", [])),
            cached=False,
            processing_time_ms=processing_time_ms,
        )

    async def _get_cached_verification(
        self,
        statement_hash: str,
        workspace_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached verification result if not expired."""
        try:
            result = self.db.client.table("verification_results").select("*").eq(
                "statement_hash", statement_hash
            ).eq(
                "workspace_id", workspace_id
            ).gte(
                "expires_at", datetime.utcnow().isoformat()
            ).single().execute()

            return result.data if result.data else None
        except Exception:
            logger.debug("Cache lookup failed for verification")
            return None

    async def _increment_hit_count(self, verification_id: str):
        """Increment cache hit count."""
        try:
            self.db.client.table("verification_results").update({
                "hit_count": self.db.client.rpc("increment_verification_hit", {"v_id": verification_id}),
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", verification_id).execute()
        except Exception:
            logger.debug("Failed to increment hit count for verification %s", verification_id)

    def _build_response_from_cache(
        self,
        cached: Dict[str, Any],
        start_time: datetime
    ) -> VerifyStatementResponse:
        """Build response from cached data."""
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        supporting = [
            EvidenceItem(**e) for e in cached.get("supporting_evidence", [])
        ]
        contradicting = [
            EvidenceItem(**e) for e in cached.get("contradicting_evidence", [])
        ]

        return VerifyStatementResponse(
            verification_id=UUID(cached["id"]),
            statement=cached["statement"],
            verdict=VerificationVerdict(cached["verdict"]),
            confidence_score=cached["confidence_score"],
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            related_claims=[],  # Not stored in cache for simplicity
            related_claims_summary=cached.get("related_claims_summary"),
            sources_analyzed=len(cached.get("web_sources", [])),
            cached=True,
            processing_time_ms=processing_time_ms,
        )

    async def _search_web_evidence(
        self,
        gemini,
        statement: str
    ) -> Dict[str, Any]:
        """Search web for evidence using Gemini grounded search."""
        search_prompt = f"""Fact-check the following statement. Find evidence that either supports or contradicts it.

Statement: {statement}

Search for reliable sources and provide specific evidence. Note any conflicting information."""

        try:
            response = await gemini.grounded_search(
                search_prompt,
                temperature=0.3
            )

            sources = []
            for source in response.sources:
                sources.append({
                    "url": source.url,
                    "title": source.title,
                    "domain": source.domain,
                    "snippet": source.snippet,
                })

            grounding_metadata = None
            if response.grounding_metadata:
                grounding_metadata = {
                    "web_search_queries": response.grounding_metadata.web_search_queries,
                    "grounding_chunks": [
                        {"uri": c.uri, "title": c.title, "domain": c.domain}
                        for c in response.grounding_metadata.grounding_chunks
                    ],
                }

            return {
                "text": response.text,
                "sources": sources,
                "grounding_metadata": grounding_metadata,
            }

        except Exception as e:
            return {
                "text": f"Error searching: {e}",
                "sources": [],
                "grounding_metadata": None,
            }

    async def _find_related_claims(
        self,
        statement: str,
        workspace_id: str
    ) -> tuple[List[RelatedClaimSummary], Optional[str]]:
        """Find related claims from knowledge base."""
        related_claims = []
        summary = None

        try:
            # Search for similar claims in knowledge_claims table
            result = self.db.client.table("knowledge_claims").select(
                "id, content, verification_status, confidence_score"
            ).eq(
                "workspace_id", workspace_id
            ).textSearch(
                "content", statement.replace(" ", " | "), config="english"
            ).limit(5).execute()

            if result.data:
                for claim in result.data:
                    # Use LLM to determine relationship
                    relationship = await self._classify_relationship(statement, claim["content"])

                    related_claims.append(RelatedClaimSummary(
                        claim_id=UUID(claim["id"]),
                        content=claim["content"][:200],
                        verification_status=claim.get("verification_status", "unverified"),
                        confidence_score=claim.get("confidence_score", 0.5),
                        relationship=relationship,
                    ))

                # Generate summary
                if related_claims:
                    supporting = sum(1 for c in related_claims if c.relationship == "supports")
                    contradicting = sum(1 for c in related_claims if c.relationship == "contradicts")
                    summary = f"Found {len(related_claims)} related claims: {supporting} supporting, {contradicting} contradicting"

        except Exception:
            logger.warning("Failed to find related claims for statement")

        return related_claims, summary

    async def _classify_relationship(self, statement: str, claim_content: str) -> str:
        """Classify relationship between statement and existing claim."""
        inference = await self._get_inference_client()
        if not inference:
            return "related"

        prompt = f"""Compare these two statements and classify their relationship:

Statement to verify: {statement}

Existing claim: {claim_content}

Classification (respond with just ONE word):
- "supports" if the existing claim supports the statement
- "contradicts" if the existing claim contradicts the statement
- "related" if they are related but neither clearly supports nor contradicts"""

        try:
            response = await inference.generate(prompt, temperature=0.1, max_tokens=10)
            text = response.text.strip().lower() if hasattr(response, 'text') else str(response).lower()
            if "support" in text:
                return "supports"
            elif "contradict" in text:
                return "contradicts"
            return "related"
        except Exception:
            logger.info("Relationship classification failed, defaulting to 'related'")
            return "related"

    async def _synthesize_verdict(
        self,
        statement: str,
        web_evidence: Dict[str, Any],
        related_claims: List[RelatedClaimSummary],
        gemini
    ) -> tuple[VerificationVerdict, float, List[EvidenceItem], List[EvidenceItem]]:
        """Use LLM to synthesize verdict from evidence."""

        # Build context from web evidence
        web_text = web_evidence.get("text", "")
        web_sources = web_evidence.get("sources", [])

        # Build context from related claims
        claims_context = ""
        if related_claims:
            claims_context = "\n".join([
                f"- [{c.relationship.upper()}] {c.content}"
                for c in related_claims
            ])

        verdict_prompt = f"""Based on the following evidence, determine if the statement is supported, contradicted, or inconclusive.

STATEMENT TO VERIFY:
{statement}

WEB SEARCH RESULTS:
{web_text}

RELATED CLAIMS FROM DATABASE:
{claims_context if claims_context else "No related claims found."}

Analyze the evidence and respond with a JSON object:
{{
    "verdict": "supported" OR "contradicted" OR "inconclusive",
    "confidence": 0.0 to 1.0,
    "supporting_excerpts": ["excerpt1", "excerpt2"],
    "contradicting_excerpts": ["excerpt1", "excerpt2"],
    "reasoning": "brief explanation"
}}"""

        try:
            parsed, response = await gemini.generate_json(verdict_prompt, temperature=0.2)

            if parsed:
                verdict_str = parsed.get("verdict", "inconclusive").lower()
                if verdict_str == "supported":
                    verdict = VerificationVerdict.SUPPORTED
                elif verdict_str == "contradicted":
                    verdict = VerificationVerdict.CONTRADICTED
                else:
                    verdict = VerificationVerdict.INCONCLUSIVE

                confidence = float(parsed.get("confidence", 0.5))

                # Build evidence items
                supporting = []
                for i, excerpt in enumerate(parsed.get("supporting_excerpts", [])[:5]):
                    source = web_sources[i] if i < len(web_sources) else {}
                    supporting.append(EvidenceItem(
                        source_url=source.get("url", ""),
                        source_title=source.get("title"),
                        source_domain=source.get("domain"),
                        excerpt=excerpt,
                        relevance_score=0.8,
                        supports_statement=True,
                    ))

                contradicting = []
                for i, excerpt in enumerate(parsed.get("contradicting_excerpts", [])[:5]):
                    source_idx = len(supporting) + i
                    source = web_sources[source_idx] if source_idx < len(web_sources) else {}
                    contradicting.append(EvidenceItem(
                        source_url=source.get("url", ""),
                        source_title=source.get("title"),
                        source_domain=source.get("domain"),
                        excerpt=excerpt,
                        relevance_score=0.8,
                        supports_statement=False,
                    ))

                return verdict, confidence, supporting, contradicting

        except Exception:
            logger.warning("Verdict synthesis failed, returning INCONCLUSIVE")

        # Fallback to inconclusive
        return VerificationVerdict.INCONCLUSIVE, 0.5, [], []

    async def _save_verification(
        self,
        verification_id: UUID,
        statement: str,
        statement_hash: str,
        verdict: VerificationVerdict,
        confidence_score: float,
        supporting_evidence: List[EvidenceItem],
        contradicting_evidence: List[EvidenceItem],
        related_claim_ids: List[UUID],
        related_claims_summary: Optional[str],
        web_sources: List[Dict],
        grounding_metadata: Optional[Dict],
        expires_at: datetime,
        workspace_id: str,
    ):
        """Save verification result to database."""
        try:
            self.db.client.table("verification_results").insert({
                "id": str(verification_id),
                "statement": statement,
                "statement_hash": statement_hash,
                "verdict": verdict.value,
                "confidence_score": confidence_score,
                "supporting_evidence": [e.model_dump() for e in supporting_evidence],
                "contradicting_evidence": [e.model_dump() for e in contradicting_evidence],
                "related_claim_ids": [str(id) for id in related_claim_ids],
                "related_claims_summary": related_claims_summary,
                "web_sources": web_sources,
                "grounding_metadata": grounding_metadata,
                "expires_at": expires_at.isoformat(),
                "hit_count": 0,
                "workspace_id": workspace_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            print(f"Warning: Failed to save verification: {e}")
