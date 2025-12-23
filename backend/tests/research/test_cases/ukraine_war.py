"""Ukraine war test cases for research template evaluation.

These test cases are designed to evaluate how well the research
template handles complex geopolitical topics with multiple perspectives.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class TestCase:
    """A single test case for evaluation."""

    id: str
    query: str
    description: str

    # Expected coverage
    expected_actors: List[str] = field(default_factory=list)
    expected_events: List[str] = field(default_factory=list)
    expected_themes: List[str] = field(default_factory=list)

    # Evaluation criteria
    min_findings: int = 5
    required_finding_types: List[str] = field(default_factory=list)
    required_perspectives: List[str] = field(default_factory=list)

    # Quality thresholds
    max_errors: int = 0

    # Template settings
    template_type: str = "investigative"
    granularity: str = "standard"
    max_searches: int = 5


# Ukraine War Test Cases
UKRAINE_WAR_TEST_CASES = [
    TestCase(
        id="ukraine_war_origins",
        query="Why did the Russia-Ukraine war start? What were the root causes and key events leading to the 2022 invasion?",
        description="Tests comprehensive coverage of war origins and causation",
        expected_actors=[
            "Vladimir Putin",
            "Volodymyr Zelenskyy",
            "NATO",
            "European Union",
            "United States",
        ],
        expected_events=[
            "2014 Crimea annexation",
            "Maidan Revolution",
            "Minsk agreements",
            "2022 invasion",
        ],
        expected_themes=[
            "NATO expansion",
            "Russian security concerns",
            "Ukrainian sovereignty",
            "Historical ties",
        ],
        min_findings=8,
        required_finding_types=["actor", "event", "relationship"],
        required_perspectives=["political", "historical"],
        granularity="standard",
        max_searches=5,
    ),

    TestCase(
        id="ukraine_war_actors",
        query="Who are the key political and military figures in the Russia-Ukraine conflict and what are their roles?",
        description="Tests actor identification and relationship mapping",
        expected_actors=[
            "Vladimir Putin",
            "Volodymyr Zelenskyy",
            "Sergei Shoigu",
            "Valery Gerasimov",
        ],
        expected_themes=[
            "Military leadership",
            "Political decision-making",
            "International alliances",
        ],
        min_findings=6,
        required_finding_types=["actor", "relationship"],
        required_perspectives=["political", "military"],
        granularity="standard",
        max_searches=4,
    ),

    TestCase(
        id="ukraine_war_economic",
        query="What are the economic impacts of the Russia-Ukraine war on global markets, energy, and food security?",
        description="Tests economic analysis capabilities",
        expected_themes=[
            "Energy prices",
            "Sanctions",
            "Food security",
            "Global inflation",
            "Supply chains",
        ],
        min_findings=6,
        required_finding_types=["pattern", "evidence"],
        required_perspectives=["economic"],
        granularity="standard",
        max_searches=4,
    ),

    TestCase(
        id="ukraine_war_timeline",
        query="Create a timeline of major events in the Russia-Ukraine conflict from 2014 to present",
        description="Tests temporal event extraction and ordering",
        expected_events=[
            "Crimea annexation",
            "Donbas conflict",
            "Minsk agreements",
            "2022 invasion",
            "Kherson liberation",
            "Bakhmut battle",
        ],
        min_findings=10,
        required_finding_types=["event"],
        required_perspectives=["historical"],
        granularity="deep",
        max_searches=6,
    ),
]


def get_test_case(case_id: str) -> TestCase:
    """Get a specific test case by ID."""
    for case in UKRAINE_WAR_TEST_CASES:
        if case.id == case_id:
            return case
    raise ValueError(f"Test case not found: {case_id}")


def list_test_cases() -> List[Dict[str, str]]:
    """List all available test cases."""
    return [
        {"id": tc.id, "description": tc.description, "query": tc.query[:50] + "..."}
        for tc in UKRAINE_WAR_TEST_CASES
    ]
