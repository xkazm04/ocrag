"""Tests for verification and evidence extraction services.

Tests the system's ability to:
1. Fact-check statements using web search + knowledge base
2. Extract quality-filtered findings from documents
3. Cache verification results
4. Apply quality filtering criteria

Run with: python -m tests.research.test_verification_service
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from uuid import uuid4

# Setup paths
try:
    _script_dir = Path(__file__).parent
except NameError:
    _script_dir = Path(os.getcwd()) / "tests" / "research"

_backend_dir = _script_dir.parent.parent

if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")


# =============================================================================
# QUALITY FILTER TESTS (Unit tests - no API calls)
# =============================================================================


def test_quality_filter_high():
    """Test quality filter assigns HIGH to good findings."""
    from app.research.services.evidence_extraction_service import QualityFilter, FindingQuality

    filter = QualityFilter(min_confidence=0.6)

    finding = {
        "content": "Russia invaded Ukraine on February 24, 2022, marking the beginning of a full-scale military conflict. This date has been confirmed by multiple international sources.",
        "confidence_score": 0.85,
    }

    quality, reasons = filter.evaluate(finding)
    print(f"HIGH test: quality={quality.value}, reasons={reasons}")
    assert quality == FindingQuality.HIGH, f"Expected HIGH, got {quality}"


def test_quality_filter_medium():
    """Test quality filter assigns MEDIUM to moderate findings."""
    from app.research.services.evidence_extraction_service import QualityFilter, FindingQuality

    filter = QualityFilter(min_confidence=0.6)

    finding = {
        "content": "NATO countries significantly increased military aid to Ukraine following the invasion.",
        "confidence_score": 0.7,
    }

    quality, reasons = filter.evaluate(finding)
    print(f"MEDIUM test: quality={quality.value}, reasons={reasons}")
    assert quality == FindingQuality.MEDIUM, f"Expected MEDIUM, got {quality}"


def test_quality_filter_vague():
    """Test quality filter FILTERS vague content."""
    from app.research.services.evidence_extraction_service import QualityFilter, FindingQuality

    filter = QualityFilter(min_confidence=0.6)

    finding = {
        "content": "Something might possibly maybe happen somehow, perhaps it could be unclear.",
        "confidence_score": 0.8,
    }

    quality, reasons = filter.evaluate(finding)
    print(f"VAGUE test: quality={quality.value}, reasons={reasons}")
    assert quality == FindingQuality.FILTERED, f"Expected FILTERED, got {quality}"
    assert any("vague" in r.lower() for r in reasons), "Should mention vagueness"


def test_quality_filter_low_confidence():
    """Test quality filter FILTERS low confidence findings."""
    from app.research.services.evidence_extraction_service import QualityFilter, FindingQuality

    filter = QualityFilter(min_confidence=0.6)

    finding = {
        "content": "This is a specific claim with enough detail about the situation.",
        "confidence_score": 0.4,
    }

    quality, reasons = filter.evaluate(finding)
    print(f"LOW CONFIDENCE test: quality={quality.value}, reasons={reasons}")
    assert quality == FindingQuality.FILTERED, f"Expected FILTERED, got {quality}"
    assert any("confidence" in r.lower() for r in reasons), "Should mention confidence"


def test_quality_filter_short_content():
    """Test quality filter FILTERS short content."""
    from app.research.services.evidence_extraction_service import QualityFilter, FindingQuality

    filter = QualityFilter(min_confidence=0.6)

    finding = {
        "content": "Too short",
        "confidence_score": 0.9,
    }

    quality, reasons = filter.evaluate(finding)
    print(f"SHORT test: quality={quality.value}, reasons={reasons}")
    assert quality == FindingQuality.FILTERED, f"Expected FILTERED, got {quality}"
    assert any("short" in r.lower() for r in reasons), "Should mention length"


def run_quality_filter_tests():
    """Run all quality filter unit tests."""
    print("\n" + "=" * 70)
    print(" QUALITY FILTER UNIT TESTS")
    print("=" * 70)

    tests = [
        ("test_high_quality", test_quality_filter_high),
        ("test_medium_quality", test_quality_filter_medium),
        ("test_vague_filter", test_quality_filter_vague),
        ("test_low_confidence_filter", test_quality_filter_low_confidence),
        ("test_short_content_filter", test_quality_filter_short_content),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [PASS] {name}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
            failed += 1

    print(f"\n  Results: {passed} passed, {failed} failed")
    return passed, failed


# =============================================================================
# VERIFICATION SERVICE TESTS (Integration tests - requires API)
# =============================================================================


async def test_verify_statement_supported():
    """Test verification with a verifiable true statement."""
    from app.research.db import get_supabase_db
    from app.research.services.verification_service import VerificationService
    from app.research.schemas.verification import VerifyStatementRequest, VerificationVerdict

    print("\n  Testing: verify_statement_supported")

    db = get_supabase_db("default")
    service = VerificationService(db)

    request = VerifyStatementRequest(
        statement="Russia invaded Ukraine on February 24, 2022",
        use_cache=False,  # Force fresh verification
        cache_ttl_hours=1,
    )

    result = await service.verify_statement(request)

    print(f"    Verdict: {result.verdict.value}")
    print(f"    Confidence: {result.confidence_score:.2f}")
    print(f"    Supporting evidence: {len(result.supporting_evidence)}")
    print(f"    Contradicting evidence: {len(result.contradicting_evidence)}")
    print(f"    Processing time: {result.processing_time_ms}ms")

    assert result.verdict == VerificationVerdict.SUPPORTED, f"Expected SUPPORTED, got {result.verdict}"
    assert result.confidence_score >= 0.7, f"Expected high confidence, got {result.confidence_score}"
    assert len(result.supporting_evidence) > 0, "Should have supporting evidence"

    return result


async def test_verify_statement_contradicted():
    """Test verification with a false statement."""
    from app.research.db import get_supabase_db
    from app.research.services.verification_service import VerificationService
    from app.research.schemas.verification import VerifyStatementRequest, VerificationVerdict

    print("\n  Testing: verify_statement_contradicted")

    db = get_supabase_db("default")
    service = VerificationService(db)

    request = VerifyStatementRequest(
        statement="Ukraine invaded Russia in February 2022",
        use_cache=False,
    )

    result = await service.verify_statement(request)

    print(f"    Verdict: {result.verdict.value}")
    print(f"    Confidence: {result.confidence_score:.2f}")
    print(f"    Supporting evidence: {len(result.supporting_evidence)}")
    print(f"    Contradicting evidence: {len(result.contradicting_evidence)}")

    assert result.verdict == VerificationVerdict.CONTRADICTED, f"Expected CONTRADICTED, got {result.verdict}"

    return result


async def test_verify_caching():
    """Test that repeated queries use cache."""
    from app.research.db import get_supabase_db
    from app.research.services.verification_service import VerificationService
    from app.research.schemas.verification import VerifyStatementRequest

    print("\n  Testing: verify_caching")

    db = get_supabase_db("default")
    service = VerificationService(db)

    statement = f"Test caching statement {uuid4().hex[:8]}"

    # First request - not cached
    request1 = VerifyStatementRequest(
        statement=statement,
        use_cache=True,
        cache_ttl_hours=1,
    )

    result1 = await service.verify_statement(request1)
    print(f"    First request cached: {result1.cached}")
    assert not result1.cached, "First request should not be cached"

    # Second request - should be cached
    result2 = await service.verify_statement(request1)
    print(f"    Second request cached: {result2.cached}")
    assert result2.cached, "Second request should be cached"

    return result1, result2


async def run_verification_tests():
    """Run verification service integration tests."""
    print("\n" + "=" * 70)
    print(" VERIFICATION SERVICE TESTS")
    print("=" * 70)

    results = []
    errors = []

    tests = [
        ("verify_statement_supported", test_verify_statement_supported),
        ("verify_statement_contradicted", test_verify_statement_contradicted),
        ("verify_caching", test_verify_caching),
    ]

    for name, test_fn in tests:
        try:
            result = await test_fn()
            results.append({"name": name, "success": True, "result": result})
            print(f"  [PASS] {name}")
        except AssertionError as e:
            results.append({"name": name, "success": False, "error": str(e)})
            errors.append(name)
            print(f"  [FAIL] {name}: {e}")
        except Exception as e:
            results.append({"name": name, "success": False, "error": str(e)})
            errors.append(name)
            print(f"  [ERROR] {name}: {e}")

    print(f"\n  Results: {len(results) - len(errors)} passed, {len(errors)} failed")
    return results


# =============================================================================
# EVIDENCE EXTRACTION TESTS (Integration tests - requires API)
# =============================================================================


async def test_extract_evidence_from_text():
    """Test evidence extraction from text document."""
    from app.research.db import get_supabase_db
    from app.research.services.evidence_extraction_service import EvidenceExtractionService
    from app.research.schemas.verification import ExtractEvidenceRequest

    print("\n  Testing: extract_evidence_from_text")

    db = get_supabase_db("default")
    service = EvidenceExtractionService(db)

    # Use document content similar to research findings
    document = """
    Russia launched a full-scale invasion of Ukraine on February 24, 2022, marking a significant escalation
    of the Russo-Ukrainian War that began in 2014. The invasion was preceded by a Russian military buildup
    along Ukraine's borders from early 2021.

    President Vladimir Putin justified the invasion by claiming the goals were to "denazify" and
    "demilitarize" Ukraine, as well as to protect Russian-speaking populations in the Donbas region.
    International observers widely rejected these justifications as pretextual.

    NATO countries responded with unprecedented military and financial aid to Ukraine. The United States
    alone has provided over $75 billion in assistance since 2022. European allies have contributed
    significant military equipment including tanks, artillery, and air defense systems.

    The conflict has resulted in significant casualties on both sides and has displaced millions of
    Ukrainian civilians. The war has had far-reaching effects on global energy markets and food security.
    """

    # Create a test topic ID (would need actual topic in production)
    test_topic_id = uuid4()

    options = ExtractEvidenceRequest(
        topic_id=test_topic_id,
        min_confidence_threshold=0.6,
        run_web_context_search=False,  # Skip for faster testing
        run_perspective_analysis=False,  # Skip for faster testing
        check_existing_claims=False,  # Skip since no real topic
        max_findings=10,
    )

    result = await service.extract_evidence(
        topic_id=test_topic_id,
        document_text=document,
        options=options,
    )

    print(f"    Status: {result.status}")
    print(f"    Total extracted: {result.stats.total_extracted}")
    print(f"    Passed quality filter: {result.stats.passed_quality_filter}")
    print(f"    Filtered out: {result.stats.filtered_out}")
    print(f"    New findings (POST): {result.stats.new_findings}")
    print(f"    Processing time: {result.stats.processing_time_ms}ms")

    if result.findings:
        print(f"\n    Sample findings:")
        for f in result.findings[:3]:
            print(f"      [{f.quality.value}] {f.content[:80]}...")

    assert result.status == "completed", f"Expected completed, got {result.status}"
    assert result.stats.total_extracted > 0, "Should extract findings"

    return result


async def test_extract_with_real_research_data():
    """Use findings from previous value_eval test as document."""
    from app.research.db import get_supabase_db
    from app.research.services.evidence_extraction_service import EvidenceExtractionService
    from app.research.schemas.verification import ExtractEvidenceRequest

    print("\n  Testing: extract_with_real_research_data")

    # Load previous e2e results
    results_path = _script_dir / "results"
    result_files = list(results_path.glob("value_eval_*.json"))

    if not result_files:
        print("    [SKIP] No previous value_eval results found")
        return None

    # Use most recent
    latest = max(result_files, key=lambda p: p.stat().st_mtime)
    print(f"    Using results from: {latest.name}")

    with open(latest) as f:
        data = json.load(f)

    # Extract some content from the results to use as document
    document_parts = []
    for test_result in data:
        if test_result.get("success"):
            query = test_result.get("query", "")
            document_parts.append(f"Research Query: {query}")

            # Get coverage info
            coverage = test_result.get("coverage", {})
            covered = coverage.get("covered_aspects", [])
            if covered:
                document_parts.append(f"Covered aspects: {', '.join(covered)}")

    if not document_parts:
        print("    [SKIP] No successful results to use as document")
        return None

    document = "\n\n".join(document_parts)
    print(f"    Document length: {len(document)} chars")

    db = get_supabase_db("default")
    service = EvidenceExtractionService(db)

    test_topic_id = uuid4()
    options = ExtractEvidenceRequest(
        topic_id=test_topic_id,
        min_confidence_threshold=0.5,  # Lower threshold for test data
        run_web_context_search=False,
        run_perspective_analysis=False,
        check_existing_claims=False,
        max_findings=5,
    )

    result = await service.extract_evidence(
        topic_id=test_topic_id,
        document_text=document,
        options=options,
    )

    print(f"    Status: {result.status}")
    print(f"    Total extracted: {result.stats.total_extracted}")
    print(f"    Passed quality filter: {result.stats.passed_quality_filter}")

    return result


async def run_extraction_tests():
    """Run evidence extraction integration tests."""
    print("\n" + "=" * 70)
    print(" EVIDENCE EXTRACTION TESTS")
    print("=" * 70)

    results = []
    errors = []

    tests = [
        ("extract_evidence_from_text", test_extract_evidence_from_text),
        ("extract_with_real_research_data", test_extract_with_real_research_data),
    ]

    for name, test_fn in tests:
        try:
            result = await test_fn()
            if result is not None:
                results.append({"name": name, "success": True, "result": result})
                print(f"  [PASS] {name}")
            else:
                print(f"  [SKIP] {name}")
        except AssertionError as e:
            results.append({"name": name, "success": False, "error": str(e)})
            errors.append(name)
            print(f"  [FAIL] {name}: {e}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            results.append({"name": name, "success": False, "error": str(e)})
            errors.append(name)
            print(f"  [ERROR] {name}: {e}")

    print(f"\n  Results: {len(results) - len(errors)} passed, {len(errors)} failed")
    return results


# =============================================================================
# FULL PIPELINE TEST
# =============================================================================


async def test_full_pipeline():
    """Test complete verification and extraction pipeline."""
    from app.research.db import get_supabase_db
    from app.research.services.verification_service import VerificationService
    from app.research.services.evidence_extraction_service import EvidenceExtractionService
    from app.research.schemas.verification import (
        VerifyStatementRequest,
        ExtractEvidenceRequest,
        VerificationVerdict,
    )

    print("\n" + "=" * 70)
    print(" FULL PIPELINE TEST")
    print("=" * 70)

    db = get_supabase_db("default")

    # Step 1: Verify a statement about Russia-Ukraine conflict
    print("\n  Step 1: Verify statement")
    verification_service = VerificationService(db)

    verify_request = VerifyStatementRequest(
        statement="Russia's stated reason for invading Ukraine was 'denazification', but this claim is widely disputed by international experts",
        use_cache=False,
    )

    verify_result = await verification_service.verify_statement(verify_request)
    print(f"    Verdict: {verify_result.verdict.value}")
    print(f"    Confidence: {verify_result.confidence_score:.2f}")

    # Step 2: Extract evidence from related document
    print("\n  Step 2: Extract evidence from document")
    extraction_service = EvidenceExtractionService(db)

    document = """
    The claim of 'denazification' as Russia's justification for the invasion has been analyzed by multiple
    international bodies. The European Parliament condemned the invasion and rejected Russian claims.
    Ukraine's president Volodymyr Zelenskyy, who is Jewish, called the denazification claim absurd.

    Historical context shows that while Ukraine did have far-right elements like the Azov Battalion,
    these represented a small minority. Ukraine's 2019 parliamentary elections saw far-right parties
    receive only about 2% of the vote, far below the levels in many European countries.

    International fact-checkers have consistently rated Russia's denazification claims as false or
    misleading, noting that Ukraine has democratic institutions and a Jewish president.
    """

    test_topic_id = uuid4()
    options = ExtractEvidenceRequest(
        topic_id=test_topic_id,
        min_confidence_threshold=0.6,
        run_web_context_search=True,  # Enable for full test
        run_perspective_analysis=True,  # Enable for full test
        check_existing_claims=False,
        max_findings=10,
    )

    extract_result = await extraction_service.extract_evidence(
        topic_id=test_topic_id,
        document_text=document,
        options=options,
    )

    print(f"    Status: {extract_result.status}")
    print(f"    Findings extracted: {extract_result.stats.total_extracted}")
    print(f"    Passed quality filter: {extract_result.stats.passed_quality_filter}")
    print(f"    Perspectives generated: {extract_result.stats.perspectives_generated}")

    # Step 3: Summary
    print("\n  Step 3: Pipeline Summary")
    print(f"    Verification: {verify_result.verdict.value} ({verify_result.confidence_score:.0%})")
    print(f"    Extraction: {extract_result.stats.passed_quality_filter} quality findings")
    print(f"    Total processing time: {verify_result.processing_time_ms + extract_result.stats.processing_time_ms}ms")

    return {
        "verification": verify_result,
        "extraction": extract_result,
    }


# =============================================================================
# MAIN
# =============================================================================


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" VERIFICATION & EVIDENCE EXTRACTION TEST SUITE")
    print(f" Started: {datetime.now().isoformat()}")
    print("=" * 70)

    total_passed = 0
    total_failed = 0

    # Unit tests (no API calls)
    passed, failed = run_quality_filter_tests()
    total_passed += passed
    total_failed += failed

    # Integration tests (require API)
    try:
        verification_results = await run_verification_tests()
        v_passed = sum(1 for r in verification_results if r.get("success"))
        total_passed += v_passed
        total_failed += len(verification_results) - v_passed
    except Exception as e:
        print(f"\n  [ERROR] Verification tests failed: {e}")
        total_failed += 1

    try:
        extraction_results = await run_extraction_tests()
        e_passed = sum(1 for r in extraction_results if r.get("success"))
        total_passed += e_passed
        total_failed += len(extraction_results) - e_passed
    except Exception as e:
        print(f"\n  [ERROR] Extraction tests failed: {e}")
        total_failed += 1

    # Full pipeline test
    try:
        pipeline_result = await test_full_pipeline()
        total_passed += 1
        print("\n  [PASS] Full pipeline test")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n  [ERROR] Full pipeline test failed: {e}")
        total_failed += 1

    # Final summary
    print("\n" + "=" * 70)
    print(" FINAL SUMMARY")
    print("=" * 70)
    print(f"\n  Total: {total_passed + total_failed} tests")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print(f"\n  Completed: {datetime.now().isoformat()}")

    return total_passed, total_failed


if __name__ == "__main__":
    passed, failed = asyncio.run(run_all_tests())
    sys.exit(0 if failed == 0 else 1)
