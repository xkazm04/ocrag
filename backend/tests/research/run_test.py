#!/usr/bin/env python
"""Run research template tests with evaluation.

Usage:
    python -m tests.research.run_test [test_case_id]
    python -m tests.research.run_test ukraine_war_origins
    python -m tests.research.run_test --list
    python -m tests.research.run_test --all
"""

import asyncio
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

# Try relative imports first, fall back to absolute
try:
    from .test_harness import ResearchTestHarness, TestResult, TestFinding
    from .test_cases.ukraine_war import (
        UKRAINE_WAR_TEST_CASES,
        get_test_case,
        list_test_cases,
        TestCase,
    )
    from .evaluation import TestEvaluator, EvaluationReport
except ImportError:
    from test_harness import ResearchTestHarness, TestResult, TestFinding
    from test_cases.ukraine_war import (
        UKRAINE_WAR_TEST_CASES,
        get_test_case,
        list_test_cases,
        TestCase,
    )
    from evaluation import TestEvaluator, EvaluationReport

# Results directory
RESULTS_DIR = Path(__file__).parent / "results"


def ensure_results_dir():
    """Ensure results directory exists."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def print_header(text: str, char: str = "="):
    """Print formatted header."""
    width = 70
    print(f"\n{char * width}")
    print(f" {text}")
    print(f"{char * width}")


def print_section(title: str):
    """Print section header."""
    print(f"\n--- {title} ---")


def format_findings(result: TestResult, max_per_type: int = 3):
    """Format findings for display."""
    by_type = {}
    for f in result.findings:
        by_type.setdefault(f.finding_type, []).append(f)

    output = []
    for ftype, findings in sorted(by_type.items()):
        output.append(f"\n  [{ftype.upper()}] ({len(findings)} found)")
        for f in findings[:max_per_type]:
            summary = f.summary or f.content[:80]
            output.append(f"    - {summary}")
        if len(findings) > max_per_type:
            output.append(f"    ... and {len(findings) - max_per_type} more")

    return "\n".join(output)


def format_timeline(result: TestResult) -> str:
    """Format timeline for display."""
    if not result.timeline:
        return "  No timeline events found"

    output = []
    for event in result.timeline:
        date_str = event.extracted_date.display_text
        summary = event.summary[:70] if event.summary else event.content[:70]

        if event.extracted_date.date_start:
            output.append(f"  {date_str:20} | {summary}")
        else:
            output.append(f"  {'(undated)':20} | {summary}")

    return "\n".join(output)


def format_perspectives(result: TestResult):
    """Format perspective analyses for display."""
    output = []
    for p in result.perspectives:
        output.append(f"\n  [{p.perspective_type.upper()}]")
        if p.key_insights:
            output.append("    Key Insights:")
            for insight in p.key_insights[:3]:
                output.append(f"      - {insight[:100]}")
        if p.warnings:
            output.append("    Warnings:")
            for warning in p.warnings[:2]:
                output.append(f"      ! {warning[:100]}")

    return "\n".join(output)


def format_evaluation(report: EvaluationReport):
    """Format evaluation report for display."""
    status = "PASSED" if report.passed else "FAILED"
    status_color = "32" if report.passed else "31"  # Green/Red ANSI

    output = [f"\n  Overall: \033[{status_color}m{status}\033[0m ({report.overall_score:.0%})"]

    output.append("\n  Metrics:")
    for m in report.metrics:
        icon = "+" if m.passed else "x"
        color = "32" if m.passed else "31"
        output.append(f"    \033[{color}m[{icon}]\033[0m {m.name}: {m.details}")

    if report.actors_found:
        output.append(f"\n  Actors Found: {', '.join(report.actors_found)}")
    if report.events_found:
        output.append(f"  Events Found: {', '.join(report.events_found)}")
    if report.themes_found:
        output.append(f"  Themes Found: {', '.join(report.themes_found)}")

    output.append(f"\n  Finding Distribution: {report.finding_type_distribution}")

    return "\n".join(output)


async def run_single_test(
    test_case: TestCase,
    harness: ResearchTestHarness,
    evaluator: TestEvaluator,
    verbose: bool = True,
) -> Tuple[TestResult, EvaluationReport]:
    """Run a single test case and evaluate results."""
    print_header(f"TEST: {test_case.id}")
    print(f"Query: {test_case.query}")
    print(f"Description: {test_case.description}")

    # Determine which perspectives to use
    perspectives = test_case.required_perspectives or ["political", "historical"]

    # Run the test
    result = await harness.run_test(
        query=test_case.query,
        template_type=test_case.template_type,
        max_searches=test_case.max_searches,
        perspectives=perspectives,
        granularity=test_case.granularity,
    )

    # Evaluate
    report = evaluator.evaluate(test_case, result)

    if verbose:
        print_section("SEARCH QUERIES")
        for i, q in enumerate(result.search_queries, 1):
            print(f"  {i}. {q}")

        print_section("SOURCES")
        print(f"  Found {len(result.sources)} sources")
        for s in result.sources[:5]:
            print(f"    - {s.title[:50]} ({s.domain})")
        if len(result.sources) > 5:
            print(f"    ... and {len(result.sources) - 5} more")

        print_section("FINDINGS")
        print(format_findings(result))

        print_section("TIMELINE")
        print(format_timeline(result))

        print_section("PERSPECTIVES")
        print(format_perspectives(result))

        print_section("EVALUATION")
        print(format_evaluation(report))

        print_section("METRICS")
        ts = result.token_stats
        print(f"  Total Tokens: {ts.total_tokens:,} (input: {ts.input_tokens:,}, output: {ts.output_tokens:,})")
        print(f"  Total Cost: ${result.total_cost_usd:.4f}")
        print(f"  Execution Time: {report.execution_time_seconds:.1f}s")

    return result, report


async def run_all_tests(
    verbose: bool = False,
    save: bool = True,
) -> List[Tuple[str, Optional[EvaluationReport], Optional[TestResult]]]:
    """Run all test cases and summarize results."""
    harness = ResearchTestHarness()  # Uses native Gemini client with Google Search
    evaluator = TestEvaluator()

    results = []
    print_header("RUNNING ALL TEST CASES", "=")
    print(f"Total cases: {len(UKRAINE_WAR_TEST_CASES)}")

    for test_case in UKRAINE_WAR_TEST_CASES:
        try:
            result, report = await run_single_test(
                test_case, harness, evaluator, verbose=verbose
            )
            results.append((test_case.id, report, result))

            # Save each result
            if save:
                save_result(result, report)

        except Exception as e:
            print(f"\nERROR in {test_case.id}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_case.id, None, None))

    # Summary
    print_header("TEST SUMMARY", "=")
    passed = sum(1 for _, r, _ in results if r and r.passed)
    total = len(results)

    print(f"\nResults: {passed}/{total} passed")
    print("\nIndividual Results:")
    for case_id, report, _ in results:
        if report:
            status = "PASSED" if report.passed else "FAILED"
            color = "32" if report.passed else "31"
            print(f"  \033[{color}m[{status}]\033[0m {case_id} ({report.overall_score:.0%})")
        else:
            print(f"  \033[31m[ERROR]\033[0m {case_id}")

    total_input = sum(r.token_stats.input_tokens for _, _, r in results if r)
    total_output = sum(r.token_stats.output_tokens for _, _, r in results if r)
    total_tokens = sum(r.token_stats.total_tokens for _, _, r in results if r)
    total_cost = sum(r.total_cost_usd for _, _, r in results if r)
    print(f"\nTotal Tokens Used: {total_tokens:,} (input: {total_input:,}, output: {total_output:,})")
    print(f"Total Cost: ${total_cost:.4f}")

    if save:
        print(f"\nResults saved to: {RESULTS_DIR}")

    return results


def save_result(
    result: TestResult,
    report: EvaluationReport,
    output_path: Optional[str] = None,
):
    """Save test result to JSON file in results directory."""
    ensure_results_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output_path:
        output_path = RESULTS_DIR / f"{report.test_case_id}_{timestamp}.json"
    else:
        output_path = Path(output_path)

    # Build timeline data
    timeline_data = []
    for event in result.timeline:
        timeline_data.append({
            "date": event.extracted_date.display_text,
            "date_sortable": (
                event.extracted_date.date_start.isoformat()
                if event.extracted_date.date_start else None
            ),
            "precision": event.extracted_date.precision.value,
            "summary": event.summary,
            "content": event.content,
        })

    data = {
        "test_case_id": report.test_case_id,
        "query": report.query,
        "timestamp": timestamp,
        "evaluation": {
            "passed": report.passed,
            "overall_score": report.overall_score,
            "metrics": [
                {
                    "name": m.name,
                    "passed": m.passed,
                    "score": m.score,
                    "details": m.details,
                }
                for m in report.metrics
            ],
            "actors_found": report.actors_found,
            "events_found": report.events_found,
            "themes_found": report.themes_found,
        },
        "results": {
            "search_queries": result.search_queries,
            "source_count": len(result.sources),
            "sources": [
                {
                    "title": s.title,
                    "url": s.url,
                    "domain": s.domain,
                    "snippet": s.snippet[:200],
                }
                for s in result.sources[:20]
            ],
            "finding_count": len(result.findings),
            "findings": [
                {
                    "type": f.finding_type,
                    "content": f.content,
                    "summary": f.summary,
                    "date_text": f.date_text,
                    "date": (
                        f.event_date.isoformat() if f.event_date else None
                    ),
                }
                for f in result.findings
            ],
            "timeline": timeline_data,
            "perspectives": [
                {
                    "type": p.perspective_type,
                    "analysis": p.analysis_text,
                    "insights": p.key_insights,
                    "recommendations": p.recommendations,
                    "warnings": p.warnings,
                }
                for p in result.perspectives
            ],
        },
        "metrics": {
            "token_usage": {
                "input_tokens": result.token_stats.input_tokens,
                "output_tokens": result.token_stats.output_tokens,
                "total_tokens": result.token_stats.total_tokens,
            },
            "total_cost_usd": result.total_cost_usd,
            "execution_time_seconds": report.execution_time_seconds,
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  Result saved: {output_path.name}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run research template tests")
    parser.add_argument(
        "test_case",
        nargs="?",
        default="ukraine_war_origins",
        help="Test case ID to run (default: ukraine_war_origins)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available test cases",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all test cases",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output for all tests",
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable Test Cases:")
        for tc in list_test_cases():
            print(f"  {tc['id']}: {tc['description']}")
            print(f"    Query: {tc['query']}")
        return

    if args.all:
        await run_all_tests(verbose=args.verbose, save=not args.no_save)
        return

    # Run single test
    try:
        test_case = get_test_case(args.test_case)
    except ValueError as e:
        print(f"Error: {e}")
        print("Use --list to see available test cases")
        return

    harness = ResearchTestHarness()  # Uses native Gemini client with Google Search
    evaluator = TestEvaluator()

    result, report = await run_single_test(test_case, harness, evaluator)

    if not args.no_save:
        save_result(result, report)


if __name__ == "__main__":
    asyncio.run(main())
