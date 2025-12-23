"""Evaluation module for research test results.

Compares test results against expected criteria and generates
detailed evaluation reports.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .test_harness import TestResult, TestFinding, TestPerspective
from .test_cases.ukraine_war import TestCase


@dataclass
class EvaluationMetric:
    """A single evaluation metric result."""

    name: str
    passed: bool
    expected: Any
    actual: Any
    score: float = 0.0
    details: str = ""


@dataclass
class EvaluationReport:
    """Complete evaluation report for a test run."""

    test_case_id: str
    query: str

    # Overall results
    passed: bool = False
    overall_score: float = 0.0

    # Individual metrics
    metrics: List[EvaluationMetric] = field(default_factory=list)

    # Coverage analysis
    actors_found: List[str] = field(default_factory=list)
    events_found: List[str] = field(default_factory=list)
    themes_found: List[str] = field(default_factory=list)

    # Quality metrics
    finding_type_distribution: Dict[str, int] = field(default_factory=dict)
    perspective_coverage: Dict[str, bool] = field(default_factory=dict)

    # Execution metrics
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    execution_time_seconds: float = 0.0

    # Issues found
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class TestEvaluator:
    """Evaluates test results against expected criteria."""

    def evaluate(
        self, test_case: TestCase, result: TestResult
    ) -> EvaluationReport:
        """Run full evaluation of test results."""
        report = EvaluationReport(
            test_case_id=test_case.id,
            query=test_case.query,
            total_tokens=result.total_tokens,
            total_cost_usd=result.total_cost_usd,
            errors=result.errors.copy(),
        )

        if result.completed_at and result.started_at:
            report.execution_time_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

        # Run all evaluations
        self._evaluate_finding_count(test_case, result, report)
        self._evaluate_finding_types(test_case, result, report)
        self._evaluate_perspectives(test_case, result, report)
        self._evaluate_actor_coverage(test_case, result, report)
        self._evaluate_event_coverage(test_case, result, report)
        self._evaluate_theme_coverage(test_case, result, report)
        self._evaluate_errors(test_case, result, report)

        # Calculate overall score
        if report.metrics:
            passed_count = sum(1 for m in report.metrics if m.passed)
            report.overall_score = passed_count / len(report.metrics)
            report.passed = report.overall_score >= 0.7  # 70% threshold

        return report

    def _evaluate_finding_count(
        self, case: TestCase, result: TestResult, report: EvaluationReport
    ):
        """Check if minimum findings were extracted."""
        actual = len(result.findings)
        passed = actual >= case.min_findings

        report.metrics.append(EvaluationMetric(
            name="Finding Count",
            passed=passed,
            expected=f">= {case.min_findings}",
            actual=actual,
            score=min(1.0, actual / case.min_findings) if case.min_findings else 1.0,
            details=f"Found {actual} findings, expected at least {case.min_findings}",
        ))

    def _evaluate_finding_types(
        self, case: TestCase, result: TestResult, report: EvaluationReport
    ):
        """Check if required finding types are present."""
        type_counts = {}
        for f in result.findings:
            type_counts[f.finding_type] = type_counts.get(f.finding_type, 0) + 1

        report.finding_type_distribution = type_counts

        found_types = set(type_counts.keys())
        required_types = set(case.required_finding_types)
        missing = required_types - found_types
        passed = len(missing) == 0

        report.metrics.append(EvaluationMetric(
            name="Finding Types",
            passed=passed,
            expected=list(required_types),
            actual=list(found_types),
            score=len(found_types & required_types) / len(required_types) if required_types else 1.0,
            details=f"Missing types: {list(missing)}" if missing else "All required types found",
        ))

    def _evaluate_perspectives(
        self, case: TestCase, result: TestResult, report: EvaluationReport
    ):
        """Check if required perspectives were analyzed."""
        analyzed = {p.perspective_type for p in result.perspectives}
        required = set(case.required_perspectives)

        for p in analyzed:
            report.perspective_coverage[p] = True

        missing = required - analyzed
        passed = len(missing) == 0

        report.metrics.append(EvaluationMetric(
            name="Perspective Coverage",
            passed=passed,
            expected=list(required),
            actual=list(analyzed),
            score=len(analyzed & required) / len(required) if required else 1.0,
            details=f"Missing: {list(missing)}" if missing else "All perspectives covered",
        ))

    def _evaluate_actor_coverage(
        self, case: TestCase, result: TestResult, report: EvaluationReport
    ):
        """Check if expected actors were identified."""
        if not case.expected_actors:
            return

        # Extract actor names from findings
        found_actors = []
        for f in result.findings:
            if f.finding_type == "actor":
                found_actors.append(f.content.lower())

        all_content = " ".join(f.content.lower() for f in result.findings)
        all_content += " " + result.synthesized_content.lower()

        matched = []
        for actor in case.expected_actors:
            if actor.lower() in all_content:
                matched.append(actor)

        report.actors_found = matched
        coverage = len(matched) / len(case.expected_actors)
        passed = coverage >= 0.5  # At least 50% of expected actors

        report.metrics.append(EvaluationMetric(
            name="Actor Coverage",
            passed=passed,
            expected=case.expected_actors,
            actual=matched,
            score=coverage,
            details=f"Found {len(matched)}/{len(case.expected_actors)} expected actors",
        ))

    def _evaluate_event_coverage(
        self, case: TestCase, result: TestResult, report: EvaluationReport
    ):
        """Check if expected events were identified."""
        if not case.expected_events:
            return

        all_content = " ".join(f.content.lower() for f in result.findings)
        all_content += " " + result.synthesized_content.lower()

        matched = []
        for event in case.expected_events:
            if event.lower() in all_content:
                matched.append(event)

        report.events_found = matched
        coverage = len(matched) / len(case.expected_events)
        passed = coverage >= 0.5

        report.metrics.append(EvaluationMetric(
            name="Event Coverage",
            passed=passed,
            expected=case.expected_events,
            actual=matched,
            score=coverage,
            details=f"Found {len(matched)}/{len(case.expected_events)} expected events",
        ))

    def _evaluate_theme_coverage(
        self, case: TestCase, result: TestResult, report: EvaluationReport
    ):
        """Check if expected themes were covered."""
        if not case.expected_themes:
            return

        all_content = " ".join(f.content.lower() for f in result.findings)
        all_content += " " + result.synthesized_content.lower()
        for p in result.perspectives:
            all_content += " " + p.analysis_text.lower()

        matched = []
        for theme in case.expected_themes:
            if theme.lower() in all_content:
                matched.append(theme)

        report.themes_found = matched
        coverage = len(matched) / len(case.expected_themes)
        passed = coverage >= 0.4  # Lower threshold for themes

        report.metrics.append(EvaluationMetric(
            name="Theme Coverage",
            passed=passed,
            expected=case.expected_themes,
            actual=matched,
            score=coverage,
            details=f"Found {len(matched)}/{len(case.expected_themes)} expected themes",
        ))

    def _evaluate_errors(
        self, case: TestCase, result: TestResult, report: EvaluationReport
    ):
        """Check error count."""
        error_count = len(result.errors)
        passed = error_count <= case.max_errors

        report.metrics.append(EvaluationMetric(
            name="Error Count",
            passed=passed,
            expected=f"<= {case.max_errors}",
            actual=error_count,
            score=1.0 if passed else 0.0,
            details=f"{error_count} errors occurred" if error_count else "No errors",
        ))
