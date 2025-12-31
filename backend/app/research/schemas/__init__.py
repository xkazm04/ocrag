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

# Job schemas (async API)
from .jobs import (
    JobStatus,
    JobStage,
    SubmitResearchRequest,
    SubmitResearchResponse,
    JobStats,
    DedupStats,
    JobStatusResponse,
    TopicMatchResult,
    DeduplicationAction,
    MergeStrategy,
    DeduplicationDecision,
    TopicContext,
    ResearchJob,
    STAGE_PROGRESS,
)

# Verification schemas
from .verification import (
    VerificationVerdict,
    EvidenceItem,
    RelatedClaimSummary,
    VerifyStatementRequest,
    VerifyStatementResponse,
    FindingQuality,
    ExtractedFinding,
    ExtractionStats,
    ExtractEvidenceRequest,
    ExtractEvidenceResponse,
    VerificationResultDB,
    DocumentExtractionDB,
)

# Deep Research schemas - Recursive
from .recursive import (
    FollowUpType,
    NodeStatus,
    TreeStatus,
    SkipReason,
    RecursiveResearchConfig,
    StartRecursiveResearchRequest,
    FollowUpQuestion,
    NodeFinding,
    ResearchNodeStatus,
    ResearchTreeStatus,
    ResearchTreeResult,
    ReasoningChain,
)

# Deep Research schemas - Financial
from .financial import (
    FinancialEntityType,
    TransactionType,
    EvidenceStrength,
    FinancialEntity,
    FinancialTransaction,
    TransactionChain,
    CorporateStructure,
    BeneficialOwner,
    PropertyRecord,
    TraceMoneyRequest,
    TraceMoneyResponse,
    CorporateStructureRequest,
    CorporateStructureResponse,
    PropertySearchRequest,
    PropertySearchResponse,
)

# Deep Research schemas - Causality
from .causality import (
    CausalityType,
    CausalMechanism,
    PatternType as CausalPatternType,
    CausalLink,
    CausalChain,
    CausalPattern,
    CausalGraph,
    ExtractCausalityRequest,
    FindCausesRequest,
    FindCausesResponse,
    FindConsequencesRequest,
    FindConsequencesResponse,
    BuildCausalGraphRequest,
)

# Knowledge Explorer schemas
from .knowledge_explorer import (
    # Graph
    GraphNode,
    GraphEdge,
    GraphData,
    NetworkGraphRequest,
    NetworkGraphResponse,
    # Timeline
    TimelineEvent,
    TimelineRequest,
    TimelineResponse,
    # Corroboration
    SourceEvidence,
    CorroborationResult,
    CorroborationRequest,
    CorroborationResponse,
    # Pattern Mining
    PatternType,
    DetectedPattern,
    PatternMiningRequest,
    PatternMiningResponse,
    # Q&A
    Citation,
    InvestigativeQuestion,
    InvestigativeAnswer,
    # Entity Profile
    EntityProfile,
    EntityProfileRequest,
)

# Build namespace for forward reference resolution
# All types must be available for Pydantic to resolve string annotations
_types_namespace = {
    "KnowledgeTopic": KnowledgeTopic,
    "KnowledgeEntity": KnowledgeEntity,
    "KnowledgeClaim": KnowledgeClaim,
    "ClaimRelationship": ClaimRelationship,
    "ClaimEntity": ClaimEntity,
    "ClaimSource": ClaimSource,
    "Source": Source,
    "SimilarityCandidate": SimilarityCandidate,
}

# Rebuild models with forward references using the complete namespace
KnowledgeTopic.model_rebuild(_types_namespace=_types_namespace)
KnowledgeClaim.model_rebuild(_types_namespace=_types_namespace)
ClaimRelationship.model_rebuild(_types_namespace=_types_namespace)
ClaimEntity.model_rebuild(_types_namespace=_types_namespace)
ClaimSource.model_rebuild(_types_namespace=_types_namespace)
SimilarityCandidate.model_rebuild(_types_namespace=_types_namespace)

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
    # Jobs (async API)
    "JobStatus",
    "JobStage",
    "SubmitResearchRequest",
    "SubmitResearchResponse",
    "JobStats",
    "DedupStats",
    "JobStatusResponse",
    "TopicMatchResult",
    "DeduplicationAction",
    "MergeStrategy",
    "DeduplicationDecision",
    "TopicContext",
    "ResearchJob",
    "STAGE_PROGRESS",
    # Verification
    "VerificationVerdict",
    "EvidenceItem",
    "RelatedClaimSummary",
    "VerifyStatementRequest",
    "VerifyStatementResponse",
    "FindingQuality",
    "ExtractedFinding",
    "ExtractionStats",
    "ExtractEvidenceRequest",
    "ExtractEvidenceResponse",
    "VerificationResultDB",
    "DocumentExtractionDB",
    # Knowledge Explorer
    "GraphNode",
    "GraphEdge",
    "GraphData",
    "NetworkGraphRequest",
    "NetworkGraphResponse",
    "TimelineEvent",
    "TimelineRequest",
    "TimelineResponse",
    "SourceEvidence",
    "CorroborationResult",
    "CorroborationRequest",
    "CorroborationResponse",
    "PatternType",
    "DetectedPattern",
    "PatternMiningRequest",
    "PatternMiningResponse",
    "Citation",
    "InvestigativeQuestion",
    "InvestigativeAnswer",
    "EntityProfile",
    "EntityProfileRequest",
    # Deep Research - Recursive
    "FollowUpType",
    "NodeStatus",
    "TreeStatus",
    "SkipReason",
    "RecursiveResearchConfig",
    "StartRecursiveResearchRequest",
    "FollowUpQuestion",
    "NodeFinding",
    "ResearchNodeStatus",
    "ResearchTreeStatus",
    "ResearchTreeResult",
    "ReasoningChain",
    # Deep Research - Financial
    "FinancialEntityType",
    "TransactionType",
    "EvidenceStrength",
    "FinancialEntity",
    "FinancialTransaction",
    "TransactionChain",
    "CorporateStructure",
    "BeneficialOwner",
    "PropertyRecord",
    "TraceMoneyRequest",
    "TraceMoneyResponse",
    "CorporateStructureRequest",
    "CorporateStructureResponse",
    "PropertySearchRequest",
    "PropertySearchResponse",
    # Deep Research - Causality
    "CausalityType",
    "CausalMechanism",
    "CausalPatternType",
    "CausalLink",
    "CausalChain",
    "CausalPattern",
    "CausalGraph",
    "ExtractCausalityRequest",
    "FindCausesRequest",
    "FindCausesResponse",
    "FindConsequencesRequest",
    "FindConsequencesResponse",
    "BuildCausalGraphRequest",
]
