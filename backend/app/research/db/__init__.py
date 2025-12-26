"""Database module for research data persistence.

Provides a unified SupabaseResearchDB class that combines all operations.
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from supabase import Client

from .client import BaseSupabaseDB, get_supabase_client, get_workspace_client
from .sessions import SessionOperations
from .queries import QueryOperations
from .sources import SourceOperations
from .findings import FindingOperations
from .perspectives import PerspectiveOperations
from .cache import CacheOperations
from .topics import TopicOperations
from .entities import EntityOperations
from .claims import ClaimOperations
from .relationships import (
    RelationshipOperations,
    ClaimEntityOperations,
    ClaimSourceOperations,
)
from .similarity import SimilarityOperations, FindingClaimOperations
from .jobs import JobOperations

from ..schemas import (
    ResearchSession,
    ResearchQuery,
    Source,
    Finding,
    Perspective,
    KnowledgeTopic,
    KnowledgeTopicCreate,
    KnowledgeEntity,
    KnowledgeEntityCreate,
    KnowledgeClaim,
    KnowledgeClaimCreate,
    ClaimRelationship,
    ClaimRelationshipCreate,
    ClaimEntity,
    ClaimSource,
    FindingClaim,
    SimilarityCandidate,
    JobStatus,
    ResearchJob,
)


class SupabaseResearchDB:
    """Unified database interface for research data."""

    def __init__(self, client: Client, workspace_id: str = "default"):
        self.client = client
        self.workspace_id = workspace_id

        # Initialize operation handlers
        self._sessions = SessionOperations(client, workspace_id)
        self._queries = QueryOperations(client, workspace_id)
        self._sources = SourceOperations(client, workspace_id)
        self._findings = FindingOperations(client, workspace_id)
        self._perspectives = PerspectiveOperations(client, workspace_id)
        self._cache = CacheOperations(client, workspace_id)
        self._topics = TopicOperations(client, workspace_id)
        self._entities = EntityOperations(client, workspace_id)
        self._claims = ClaimOperations(client, workspace_id)
        self._relationships = RelationshipOperations(client, workspace_id)
        self._claim_entities = ClaimEntityOperations(client, workspace_id)
        self._claim_sources = ClaimSourceOperations(client, workspace_id)
        self._similarity = SimilarityOperations(client, workspace_id)
        self._finding_claims = FindingClaimOperations(client, workspace_id)
        self._jobs = JobOperations(client, workspace_id)

    # Session Operations
    async def create_session(self, *args, **kwargs) -> ResearchSession:
        return await self._sessions.create_session(*args, **kwargs)

    async def get_session(self, session_id: UUID) -> Optional[ResearchSession]:
        return await self._sessions.get_session(session_id)

    async def update_session_status(self, session_id: UUID, status: str) -> None:
        return await self._sessions.update_session_status(session_id, status)

    async def complete_session(self, session_id: UUID) -> None:
        return await self._sessions.complete_session(session_id)

    async def list_sessions(self, *args, **kwargs) -> List[ResearchSession]:
        return await self._sessions.list_sessions(*args, **kwargs)

    async def delete_session(self, session_id: UUID) -> None:
        return await self._sessions.delete_session(session_id)

    # Query Operations
    async def save_query(self, *args, **kwargs) -> ResearchQuery:
        return await self._queries.save_query(*args, **kwargs)

    # Source Operations
    async def save_sources(self, *args, **kwargs) -> List[Source]:
        return await self._sources.save_sources(*args, **kwargs)

    async def get_sources(self, *args, **kwargs) -> List[Source]:
        return await self._sources.get_sources(*args, **kwargs)

    # Finding Operations
    async def save_findings(self, *args, **kwargs) -> List[Finding]:
        return await self._findings.save_findings(*args, **kwargs)

    async def get_findings(self, *args, **kwargs) -> List[Finding]:
        return await self._findings.get_findings(*args, **kwargs)

    async def get_finding(self, finding_id: UUID) -> Optional[Finding]:
        return await self._findings.get_finding(finding_id)

    # Perspective Operations
    async def save_perspective(self, *args, **kwargs) -> Perspective:
        return await self._perspectives.save_perspective(*args, **kwargs)

    async def get_perspectives(self, session_id: UUID) -> List[Perspective]:
        return await self._perspectives.get_perspectives(session_id)

    # Cache Operations
    async def get_cached_session(self, *args, **kwargs) -> Optional[ResearchSession]:
        return await self._cache.get_cached_session(*args, **kwargs)

    async def cache_session(self, *args, **kwargs) -> None:
        return await self._cache.cache_session(*args, **kwargs)

    async def clear_cache(self, *args, **kwargs) -> None:
        return await self._cache.clear_cache(*args, **kwargs)

    async def get_cache_stats(self, workspace_id: str) -> Dict[str, Any]:
        return await self._cache.get_cache_stats(workspace_id)

    # Topic Operations
    async def create_topic(self, topic: KnowledgeTopicCreate) -> KnowledgeTopic:
        return await self._topics.create_topic(topic)

    async def get_topic(self, topic_id: UUID) -> Optional[KnowledgeTopic]:
        return await self._topics.get_topic(topic_id)

    async def get_topic_by_slug(self, slug: str) -> Optional[KnowledgeTopic]:
        return await self._topics.get_topic_by_slug(slug)

    async def list_topics(self, *args, **kwargs) -> List[KnowledgeTopic]:
        return await self._topics.list_topics(*args, **kwargs)

    async def get_topic_tree(self, *args, **kwargs) -> List[KnowledgeTopic]:
        return await self._topics.get_topic_tree(*args, **kwargs)

    async def get_topic_path(self, topic_id: UUID) -> List[KnowledgeTopic]:
        return await self._topics.get_topic_path(topic_id)

    async def update_topic(self, *args, **kwargs) -> KnowledgeTopic:
        return await self._topics.update_topic(*args, **kwargs)

    async def delete_topic(self, topic_id: UUID) -> None:
        return await self._topics.delete_topic(topic_id)

    # Entity Operations
    async def create_entity(self, entity: KnowledgeEntityCreate) -> KnowledgeEntity:
        return await self._entities.create_entity(entity)

    async def get_entity(self, entity_id: UUID) -> Optional[KnowledgeEntity]:
        return await self._entities.get_entity(entity_id)

    async def find_entity_by_name(self, *args, **kwargs) -> Optional[KnowledgeEntity]:
        return await self._entities.find_entity_by_name(*args, **kwargs)

    async def search_entities(self, *args, **kwargs) -> List[KnowledgeEntity]:
        return await self._entities.search_entities(*args, **kwargs)

    async def get_or_create_entity(self, *args, **kwargs) -> Tuple[KnowledgeEntity, bool]:
        return await self._entities.get_or_create_entity(*args, **kwargs)

    async def update_entity(self, *args, **kwargs) -> KnowledgeEntity:
        return await self._entities.update_entity(*args, **kwargs)

    # Claim Operations
    async def create_claim(self, *args, **kwargs) -> KnowledgeClaim:
        return await self._claims.create_claim(*args, **kwargs)

    async def get_claim(self, claim_id: UUID) -> Optional[KnowledgeClaim]:
        return await self._claims.get_claim(claim_id)

    async def search_claims(self, *args, **kwargs) -> Tuple[List[KnowledgeClaim], int]:
        return await self._claims.search_claims(*args, **kwargs)

    async def get_claims_by_topic(self, *args, **kwargs) -> List[KnowledgeClaim]:
        return await self._claims.get_claims_by_topic(*args, **kwargs)

    async def update_claim(self, *args, **kwargs) -> KnowledgeClaim:
        return await self._claims.update_claim(*args, **kwargs)

    async def update_claim_embedding(self, *args, **kwargs) -> None:
        return await self._claims.update_claim_embedding(*args, **kwargs)

    async def verify_claim(self, *args, **kwargs) -> KnowledgeClaim:
        return await self._claims.verify_claim(*args, **kwargs)

    # Relationship Operations
    async def create_claim_relationship(
        self, relationship: ClaimRelationshipCreate, user_id: Optional[str] = None
    ) -> ClaimRelationship:
        return await self._relationships.create_relationship(relationship, user_id)

    async def get_claim_relationships(self, *args, **kwargs) -> List[ClaimRelationship]:
        return await self._relationships.get_relationships(*args, **kwargs)

    async def get_related_claims(self, claim_id: UUID) -> Dict[str, List[Dict[str, Any]]]:
        return await self._relationships.get_related_claims(claim_id)

    async def get_causal_chain(self, *args, **kwargs) -> List[Dict[str, Any]]:
        return await self._relationships.get_causal_chain(*args, **kwargs)

    async def get_consequences(self, *args, **kwargs) -> List[Dict[str, Any]]:
        return await self._relationships.get_consequences(*args, **kwargs)

    # Claim-Entity Operations
    async def link_claim_entity(self, *args, **kwargs) -> ClaimEntity:
        return await self._claim_entities.link_claim_entity(*args, **kwargs)

    async def get_claim_entities(self, claim_id: UUID) -> List[KnowledgeEntity]:
        return await self._claim_entities.get_claim_entities(
            claim_id, self._entities._row_to_entity
        )

    # Claim Source Operations
    async def add_claim_source(self, *args, **kwargs) -> ClaimSource:
        return await self._claim_sources.add_source(*args, **kwargs)

    async def get_claim_sources(self, claim_id: UUID) -> List[ClaimSource]:
        return await self._claim_sources.get_sources(claim_id)

    # Similarity Operations
    async def find_similar_claims(self, *args, **kwargs) -> List[Dict[str, Any]]:
        return await self._similarity.find_similar_claims(*args, **kwargs)

    async def create_similarity_candidate(self, *args, **kwargs) -> SimilarityCandidate:
        return await self._similarity.create_candidate(*args, **kwargs)

    async def get_pending_similarity_candidates(self, *args, **kwargs) -> List[SimilarityCandidate]:
        return await self._similarity.get_pending_candidates(*args, **kwargs)

    async def resolve_similarity(self, *args, **kwargs) -> None:
        return await self._similarity.resolve_candidate(*args, **kwargs)

    # Finding-Claim Operations
    async def link_finding_to_claim(self, *args, **kwargs) -> FindingClaim:
        return await self._finding_claims.link_finding_to_claim(*args, **kwargs)

    # Job Operations
    async def create_job(self, *args, **kwargs) -> ResearchJob:
        return await self._jobs.create_job(*args, **kwargs)

    async def get_job(self, job_id: UUID) -> Optional[ResearchJob]:
        return await self._jobs.get_job(job_id)

    async def update_job_status(self, *args, **kwargs) -> None:
        return await self._jobs.update_job_status(*args, **kwargs)

    async def update_job_progress(self, *args, **kwargs) -> None:
        return await self._jobs.update_job_progress(*args, **kwargs)

    async def complete_job(self, *args, **kwargs) -> None:
        return await self._jobs.complete_job(*args, **kwargs)

    async def fail_job(self, *args, **kwargs) -> None:
        return await self._jobs.fail_job(*args, **kwargs)

    async def cancel_job(self, job_id: UUID) -> None:
        return await self._jobs.cancel_job(job_id)

    async def list_jobs(self, *args, **kwargs) -> List[ResearchJob]:
        return await self._jobs.list_jobs(*args, **kwargs)


def get_supabase_db(workspace_id: str = "default") -> SupabaseResearchDB:
    """Get Supabase research database instance."""
    client = get_supabase_client()
    return SupabaseResearchDB(client, workspace_id)


__all__ = [
    "SupabaseResearchDB",
    "get_supabase_client",
    "get_supabase_db",
    "JobOperations",
]
