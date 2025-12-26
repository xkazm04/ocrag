"""Research services module."""

# Core services
from .web_search import WebSearchService
from .orchestrator import ResearchOrchestrator
from .credibility import CredibilityAssessor
from .analysis import MultiPerspectiveAnalyzer
from .embedding import EmbeddingService, EntityEmbeddingService, get_embedding_service

# Query services
from .query_normalizer import QueryNormalizer
from .time_scope_analyzer import TimeScopeAnalyzer, TimeScopeDecision
from .topic_matcher import TopicMatcher

# Extraction services
from .extraction import QualityFilter, EvidenceExtractionService

# Processing services
from .job_processor import process_research_job
from .deduplicator import FindingDeduplicator

__all__ = [
    # Core services
    "WebSearchService",
    "ResearchOrchestrator",
    "CredibilityAssessor",
    "MultiPerspectiveAnalyzer",
    "EmbeddingService",
    "EntityEmbeddingService",
    "get_embedding_service",
    # Query services
    "QueryNormalizer",
    "TimeScopeAnalyzer",
    "TimeScopeDecision",
    "TopicMatcher",
    # Extraction services
    "QualityFilter",
    "EvidenceExtractionService",
    # Processing services
    "process_research_job",
    "FindingDeduplicator",
]
