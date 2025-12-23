"""Research schemas module - re-exports all schema classes."""

# Enums
from .enums import (
    ResearchStatus,
    TemplateType,
    FindingType,
    SourceType,
    PerspectiveType,
    TemporalContext,
    TopicType,
    EntityType,
    ClaimType,
    RelationshipType,
    VerificationStatus,
    Visibility,
    ClaimSourceType,
    SimilarityStatus,
)

# Research schemas
from .research import (
    ResearchParameters,
    ResearchRequest,
    ContinueResearchRequest,
    ResearchProgress,
    ResearchQuery,
    ResearchSession,
    ResearchSessionList,
)

# Source schemas
from .sources import (
    GroundingChunk,
    GroundingSupport,
    GroundingMetadata,
    Source,
    SearchResult,
)

# Finding schemas
from .findings import (
    Finding,
    Perspective,
)

# Knowledge base schemas
from .knowledge import (
    KnowledgeTopicBase,
    KnowledgeTopicCreate,
    KnowledgeTopic,
    KnowledgeEntityBase,
    KnowledgeEntityCreate,
    KnowledgeEntity,
    KnowledgeClaimBase,
    KnowledgeClaimCreate,
    KnowledgeClaim,
)

# Relationship schemas
from .relationships import (
    ClaimRelationshipBase,
    ClaimRelationshipCreate,
    ClaimRelationship,
    ClaimEntityBase,
    ClaimEntityCreate,
    ClaimEntity,
    ClaimSourceBase,
    ClaimSourceCreate,
    ClaimSource,
    FindingClaimBase,
    FindingClaimCreate,
    FindingClaim,
    SimilarityCandidate,
)

# Response schemas
from .responses import (
    TopicTreeResponse,
    ClaimSearchRequest,
    ClaimSearchResponse,
    CausalChainResponse,
    RelatedClaimsResponse,
    EntityClaimsResponse,
    SimilarClaimsRequest,
    SimilarClaimsResponse,
    PromoteToKnowledgeBaseRequest,
    MergeClaimsRequest,
    TemplateInfo,
    CacheStats,
)

__all__ = [
    # Enums
    "ResearchStatus",
    "TemplateType",
    "FindingType",
    "SourceType",
    "PerspectiveType",
    "TemporalContext",
    "TopicType",
    "EntityType",
    "ClaimType",
    "RelationshipType",
    "VerificationStatus",
    "Visibility",
    "ClaimSourceType",
    "SimilarityStatus",
    # Research
    "ResearchParameters",
    "ResearchRequest",
    "ContinueResearchRequest",
    "ResearchProgress",
    "ResearchQuery",
    "ResearchSession",
    "ResearchSessionList",
    # Sources
    "GroundingChunk",
    "GroundingSupport",
    "GroundingMetadata",
    "Source",
    "SearchResult",
    # Findings
    "Finding",
    "Perspective",
    # Knowledge base
    "KnowledgeTopicBase",
    "KnowledgeTopicCreate",
    "KnowledgeTopic",
    "KnowledgeEntityBase",
    "KnowledgeEntityCreate",
    "KnowledgeEntity",
    "KnowledgeClaimBase",
    "KnowledgeClaimCreate",
    "KnowledgeClaim",
    # Relationships
    "ClaimRelationshipBase",
    "ClaimRelationshipCreate",
    "ClaimRelationship",
    "ClaimEntityBase",
    "ClaimEntityCreate",
    "ClaimEntity",
    "ClaimSourceBase",
    "ClaimSourceCreate",
    "ClaimSource",
    "FindingClaimBase",
    "FindingClaimCreate",
    "FindingClaim",
    "SimilarityCandidate",
    # Responses
    "TopicTreeResponse",
    "ClaimSearchRequest",
    "ClaimSearchResponse",
    "CausalChainResponse",
    "RelatedClaimsResponse",
    "EntityClaimsResponse",
    "SimilarClaimsRequest",
    "SimilarClaimsResponse",
    "PromoteToKnowledgeBaseRequest",
    "MergeClaimsRequest",
    "TemplateInfo",
    "CacheStats",
]
