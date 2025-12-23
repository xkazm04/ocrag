"""Research module tests.

This package provides a feedback loop for testing and evaluating
research templates without database persistence.

Usage:
    # From backend directory:
    python -m tests.research.run_test ukraine_war_origins
    python -m tests.research.run_test --list
    python -m tests.research.run_test --all

Results are saved to: tests/research/results/
"""

from .llm_client import OpenRouterClient, WebSearchSimulator, get_llm_client
from .test_harness import ResearchTestHarness, TestResult, TestFinding
from .evaluation import TestEvaluator, EvaluationReport
from .date_utils import (
    DateExtractor, TimelineBuilder, TimelineEvent,
    ExtractedDate, DatePrecision,
    extract_date, build_timeline, format_timeline,
)

__all__ = [
    # LLM Client
    "OpenRouterClient",
    "WebSearchSimulator",
    "get_llm_client",
    # Test Harness
    "ResearchTestHarness",
    "TestResult",
    "TestFinding",
    # Evaluation
    "TestEvaluator",
    "EvaluationReport",
    # Date/Timeline
    "DateExtractor",
    "TimelineBuilder",
    "TimelineEvent",
    "ExtractedDate",
    "DatePrecision",
    "extract_date",
    "build_timeline",
    "format_timeline",
]
