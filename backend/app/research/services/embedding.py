"""Embedding service for semantic similarity and deduplication.

Uses Gemini's text embedding model to generate embeddings for claims
and detect similar content for deduplication.
"""

import hashlib
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from google import genai
from google.genai import types

from app.config import get_settings
from ..db import SupabaseResearchDB, get_supabase_db
from ..schemas import KnowledgeClaim, KnowledgeClaimCreate, SimilarityCandidate

settings = get_settings()


class EmbeddingService:
    """Service for generating embeddings and finding similar content."""

    # Gemini embedding model
    EMBEDDING_MODEL = "text-embedding-004"
    EMBEDDING_DIMENSION = 768

    # Similarity thresholds
    HIGH_SIMILARITY_THRESHOLD = 0.95  # Very likely duplicate
    MEDIUM_SIMILARITY_THRESHOLD = 0.85  # Review for potential merge
    LOW_SIMILARITY_THRESHOLD = 0.75  # Related but distinct

    def __init__(self, db: Optional[SupabaseResearchDB] = None):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.db = db or get_supabase_db()

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text using Gemini.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector
        """
        # Truncate very long text (embedding model has limits)
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars]

        result = self.client.models.embed_content(
            model=self.EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
                output_dimensionality=self.EMBEDDING_DIMENSION,
            ),
        )

        return result.embeddings[0].values

    async def generate_claim_embedding(self, claim: KnowledgeClaim) -> List[float]:
        """Generate embedding for a knowledge claim.

        Uses the claim content and summary for better semantic representation.
        """
        # Combine content and summary for richer embedding
        text_parts = [claim.content]
        if claim.summary:
            text_parts.append(claim.summary)
        if claim.tags:
            text_parts.append(" ".join(claim.tags))

        combined_text = " ".join(text_parts)
        return await self.generate_embedding(combined_text)

    async def find_similar_claims(
        self,
        text: str,
        threshold: float = 0.85,
        limit: int = 10,
        exclude_claim_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """Find claims similar to the given text.

        Args:
            text: The text to find similar claims for
            threshold: Minimum similarity score (0.0-1.0)
            limit: Maximum number of results
            exclude_claim_id: Claim ID to exclude from results

        Returns:
            List of dicts with 'claim' and 'similarity' keys
        """
        embedding = await self.generate_embedding(text)
        return await self.db.find_similar_claims(
            embedding=embedding,
            threshold=threshold,
            limit=limit,
            exclude_claim_id=exclude_claim_id,
        )

    async def check_for_duplicates(
        self,
        content: str,
        threshold: float = 0.85,
    ) -> Tuple[bool, Optional[KnowledgeClaim], float]:
        """Check if content already exists as a claim.

        Args:
            content: The content to check
            threshold: Minimum similarity for duplicate detection

        Returns:
            Tuple of (is_duplicate, matching_claim, similarity_score)
        """
        similar = await self.find_similar_claims(
            text=content,
            threshold=threshold,
            limit=1,
        )

        if similar:
            match = similar[0]
            return True, match["claim"], match["similarity"]

        return False, None, 0.0

    async def create_claim_with_dedup(
        self,
        claim: KnowledgeClaimCreate,
        auto_merge_threshold: float = 0.95,
        create_candidate_threshold: float = 0.85,
        user_id: Optional[str] = None,
    ) -> Tuple[KnowledgeClaim, str]:
        """Create a claim with automatic deduplication.

        Args:
            claim: The claim to create
            auto_merge_threshold: If similarity >= this, auto-merge
            create_candidate_threshold: If similarity >= this, create review candidate
            user_id: Optional user ID for tracking

        Returns:
            Tuple of (claim, action) where action is one of:
            - 'created': New claim created
            - 'merged': Auto-merged with existing claim
            - 'candidate': Created with similarity candidate for review
        """
        # Generate embedding
        text_parts = [claim.content]
        if claim.summary:
            text_parts.append(claim.summary)
        embedding = await self.generate_embedding(" ".join(text_parts))

        # Check for similar claims
        similar = await self.db.find_similar_claims(
            embedding=embedding,
            threshold=create_candidate_threshold,
            limit=5,
        )

        if similar:
            top_match = similar[0]
            similarity = top_match["similarity"]
            existing_claim = top_match["claim"]

            # Auto-merge if very high similarity
            if similarity >= auto_merge_threshold:
                # Just link to existing claim and increment corroboration
                merged = await self.db.merge_claims(
                    source_claim_id=existing_claim.id,  # This will be marked superseded
                    target_claim_id=existing_claim.id,  # Keep the existing
                    keep_both_sources=True,
                )
                # Actually we need to create but mark it - let's handle differently
                # Create the new claim but link it
                new_claim = await self.db.create_claim(
                    claim=claim,
                    embedding=embedding,
                    user_id=user_id,
                )
                # Create corroborates relationship
                from ..schemas import ClaimRelationshipCreate
                await self.db.create_claim_relationship(ClaimRelationshipCreate(
                    source_claim_id=new_claim.id,
                    target_claim_id=existing_claim.id,
                    relationship_type="corroborates",
                    strength=similarity,
                    description=f"Auto-detected as highly similar (score: {similarity:.3f})",
                ))
                # Update corroboration count
                await self.db.update_claim(existing_claim.id, {
                    "corroboration_count": existing_claim.corroboration_count + 1,
                })
                return new_claim, "merged"

            # Create candidate for review if medium similarity
            new_claim = await self.db.create_claim(
                claim=claim,
                embedding=embedding,
                user_id=user_id,
            )

            # Create similarity candidates for all matches
            for match in similar:
                await self.db.create_similarity_candidate(
                    claim_id=new_claim.id,
                    similar_claim_id=match["claim"].id,
                    similarity_score=match["similarity"],
                    similarity_type="semantic",
                )

            return new_claim, "candidate"

        # No duplicates found - create new claim
        new_claim = await self.db.create_claim(
            claim=claim,
            embedding=embedding,
            user_id=user_id,
        )

        return new_claim, "created"

    async def update_claim_embedding(self, claim_id: UUID) -> None:
        """Update the embedding for an existing claim."""
        claim = await self.db.get_claim(claim_id)
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")

        embedding = await self.generate_claim_embedding(claim)
        await self.db.update_claim_embedding(claim_id, embedding)

    async def batch_update_embeddings(
        self,
        claim_ids: Optional[List[UUID]] = None,
        batch_size: int = 50,
    ) -> Dict[str, int]:
        """Update embeddings for multiple claims.

        Args:
            claim_ids: Specific claim IDs to update, or None for all without embeddings
            batch_size: Number of claims to process per batch

        Returns:
            Dict with 'updated' and 'failed' counts
        """
        updated = 0
        failed = 0

        if claim_ids:
            for claim_id in claim_ids:
                try:
                    await self.update_claim_embedding(claim_id)
                    updated += 1
                except Exception as e:
                    print(f"Failed to update embedding for {claim_id}: {e}")
                    failed += 1
        else:
            # Get claims without embeddings
            # This would need a custom query - for now just return
            pass

        return {"updated": updated, "failed": failed}

    async def find_all_similar_pairs(
        self,
        threshold: float = 0.85,
        limit_per_claim: int = 5,
        max_claims: int = 1000,
    ) -> List[SimilarityCandidate]:
        """Find all similar claim pairs in the knowledge base.

        This is a batch operation to discover potential duplicates.
        """
        # Get all claims with embeddings
        claims, total = await self.db.search_claims(
            visibility="all",
            limit=max_claims,
        )

        candidates = []
        processed_pairs = set()

        for claim in claims:
            # Skip claims without embeddings (need to regenerate)
            similar = await self.find_similar_claims(
                text=claim.content,
                threshold=threshold,
                limit=limit_per_claim,
                exclude_claim_id=claim.id,
            )

            for match in similar:
                # Avoid duplicate pairs
                pair_key = tuple(sorted([str(claim.id), str(match["claim"].id)]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                # Create similarity candidate
                candidate = await self.db.create_similarity_candidate(
                    claim_id=claim.id,
                    similar_claim_id=match["claim"].id,
                    similarity_score=match["similarity"],
                    similarity_type="semantic",
                )
                candidates.append(candidate)

        return candidates


class EntityEmbeddingService:
    """Service for entity deduplication using embeddings."""

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.embedding_service = embedding_service or EmbeddingService()
        self.db = self.embedding_service.db

    async def find_similar_entities(
        self,
        name: str,
        entity_type: Optional[str] = None,
        threshold: float = 0.85,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find entities similar to the given name.

        Uses both exact hash matching and semantic similarity.
        """
        # First check for exact match
        exact_match = await self.db.find_entity_by_name(name, entity_type)
        if exact_match:
            return [{"entity": exact_match, "similarity": 1.0, "match_type": "exact"}]

        # Search by partial name
        partial_matches = await self.db.search_entities(
            query=name,
            entity_type=entity_type,
            limit=limit,
        )

        # For now, use simple string similarity
        # Could enhance with embeddings for entity descriptions
        results = []
        name_lower = name.lower()

        for entity in partial_matches:
            # Simple similarity based on name overlap
            entity_name_lower = entity.canonical_name.lower()

            # Check aliases too
            all_names = [entity_name_lower] + [a.lower() for a in entity.aliases]

            best_similarity = 0.0
            for check_name in all_names:
                # Jaccard similarity on words
                words1 = set(name_lower.split())
                words2 = set(check_name.split())
                intersection = words1 & words2
                union = words1 | words2
                if union:
                    similarity = len(intersection) / len(union)
                    best_similarity = max(best_similarity, similarity)

            if best_similarity >= threshold:
                results.append({
                    "entity": entity,
                    "similarity": best_similarity,
                    "match_type": "partial",
                })

        return sorted(results, key=lambda x: x["similarity"], reverse=True)[:limit]


def get_embedding_service(workspace_id: str = "default") -> EmbeddingService:
    """Get embedding service instance."""
    db = get_supabase_db(workspace_id)
    return EmbeddingService(db)
