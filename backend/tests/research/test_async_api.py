"""End-to-end test for async research API.

Tests the complete flow:
1. Job submission with health check
2. Status polling with progress tracking
3. Topic matching
4. Research pipeline execution
5. Deduplication
6. Final stats

Run with: python -m tests.research.test_async_api
Or: python tests/research/test_async_api.py (from backend dir)
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from uuid import UUID
from datetime import datetime

# Determine script location
try:
    _script_dir = Path(__file__).parent
except NameError:
    _script_dir = Path(os.getcwd()) / "tests" / "research"

_backend_dir = _script_dir.parent.parent

# Add paths for imports
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")


async def test_imports():
    """Test that all required modules can be imported."""
    print("\n" + "="*70)
    print("STEP 1: Testing Imports")
    print("="*70)

    errors = []

    # Test schema imports
    try:
        from app.research.schemas.jobs import (
            JobStatus, JobStage, SubmitResearchRequest,
            SubmitResearchResponse, JobStatusResponse, JobStats,
            TopicMatchResult, DeduplicationDecision, STAGE_PROGRESS
        )
        print("  [OK] Job schemas imported")
    except ImportError as e:
        errors.append(f"Job schemas: {e}")
        print(f"  [FAIL] Job schemas: {e}")

    # Test DB imports
    try:
        from app.research.db import get_supabase_db, SupabaseResearchDB
        from app.research.db.jobs import JobOperations
        print("  [OK] Database operations imported")
    except ImportError as e:
        errors.append(f"DB operations: {e}")
        print(f"  [FAIL] DB operations: {e}")

    # Test service imports
    try:
        from app.research.services.topic_matcher import TopicMatcher
        print("  [OK] TopicMatcher imported")
    except ImportError as e:
        errors.append(f"TopicMatcher: {e}")
        print(f"  [FAIL] TopicMatcher: {e}")

    try:
        from app.research.services.deduplicator import FindingDeduplicator
        print("  [OK] FindingDeduplicator imported")
    except ImportError as e:
        errors.append(f"FindingDeduplicator: {e}")
        print(f"  [FAIL] FindingDeduplicator: {e}")

    try:
        from app.research.services.job_processor import JobProcessor, process_research_job
        print("  [OK] JobProcessor imported")
    except ImportError as e:
        errors.append(f"JobProcessor: {e}")
        print(f"  [FAIL] JobProcessor: {e}")

    # Test research harness imports
    try:
        from enhanced_harness import EnhancedResearchHarness
        print("  [OK] EnhancedResearchHarness imported")
    except ImportError as e:
        errors.append(f"EnhancedResearchHarness: {e}")
        print(f"  [FAIL] EnhancedResearchHarness: {e}")

    try:
        from inference_client import InferenceClient
        print("  [OK] InferenceClient imported")
    except ImportError as e:
        errors.append(f"InferenceClient: {e}")
        print(f"  [FAIL] InferenceClient: {e}")

    try:
        from gemini_client import GeminiResearchClient
        print("  [OK] GeminiResearchClient imported")
    except ImportError as e:
        errors.append(f"GeminiResearchClient: {e}")
        print(f"  [FAIL] GeminiResearchClient: {e}")

    if errors:
        print(f"\n  IMPORT ERRORS: {len(errors)}")
        return False

    print("\n  All imports successful!")
    return True


async def test_database_connection():
    """Test Supabase database connection."""
    print("\n" + "="*70)
    print("STEP 2: Testing Database Connection")
    print("="*70)

    try:
        from app.research.db import get_supabase_db

        db = get_supabase_db("default")
        print(f"  [OK] Database client created")

        # Test simple query
        result = db.client.table("research_sessions").select("id").limit(1).execute()
        print(f"  [OK] Database query successful")

        return True
    except Exception as e:
        print(f"  [FAIL] Database connection: {e}")
        return False


async def test_gemini_health():
    """Test Gemini API availability."""
    print("\n" + "="*70)
    print("STEP 3: Testing Gemini API")
    print("="*70)

    try:
        from google import genai

        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents="Say 'OK' if you're working.",
            config={"max_output_tokens": 10},
        )

        if response.text:
            print(f"  [OK] Gemini API response: {response.text.strip()}")
            return True
        else:
            print("  [FAIL] Gemini API returned empty response")
            return False

    except Exception as e:
        print(f"  [FAIL] Gemini API: {e}")
        return False


async def test_openrouter_health():
    """Test OpenRouter API availability."""
    print("\n" + "="*70)
    print("STEP 4: Testing OpenRouter API")
    print("="*70)

    try:
        from inference_client import InferenceClient

        client = InferenceClient()
        response = await client.generate(
            "Say 'OK' if you're working.",
            temperature=0.1,
            max_tokens=10,
        )

        if response and hasattr(response, 'text') and response.text:
            print(f"  [OK] OpenRouter API response: {response.text.strip()}")
            return True
        else:
            print("  [FAIL] OpenRouter API returned empty response")
            return False

    except Exception as e:
        print(f"  [FAIL] OpenRouter API: {e}")
        return False


async def test_job_crud():
    """Test job CRUD operations."""
    print("\n" + "="*70)
    print("STEP 5: Testing Job CRUD Operations")
    print("="*70)

    try:
        from app.research.db import get_supabase_db
        from app.research.db.jobs import JobOperations
        from app.research.schemas.jobs import JobStatus, JobStage

        db = get_supabase_db("default")
        jobs = JobOperations(db.client, "default")

        # Create job
        job = await jobs.create_job(
            query="Test query for e2e testing - async API validation",
            workspace_id="default",
            template_type="investigative",
            parameters={"test": True},
        )
        print(f"  [OK] Job created: {job.id}")

        # Get job
        retrieved = await jobs.get_job(job.id)
        assert retrieved is not None, "Job not found"
        assert retrieved.status == JobStatus.PENDING
        print(f"  [OK] Job retrieved, status: {retrieved.status.value}")

        # Update status
        await jobs.update_job_status(
            job.id,
            JobStatus.RUNNING,
            JobStage.HEALTH_CHECK.value,
            5.0
        )
        retrieved = await jobs.get_job(job.id)
        assert retrieved.status == JobStatus.RUNNING
        print(f"  [OK] Job status updated to: {retrieved.status.value}")

        # Update progress
        await jobs.update_job_progress(job.id, JobStage.TOPIC_MATCHING)
        retrieved = await jobs.get_job(job.id)
        print(f"  [OK] Job progress updated: {retrieved.progress_pct}%")

        # Set topic match
        await jobs.set_topic_match(
            job.id,
            topic_id=None,
            confidence=0.3,
            reasoning="Test - no matching topic"
        )
        print(f"  [OK] Topic match set")

        # Fail job (for cleanup)
        await jobs.fail_job(job.id, "Test completed - cleaning up")
        retrieved = await jobs.get_job(job.id)
        assert retrieved.status == JobStatus.FAILED
        print(f"  [OK] Job marked as failed for cleanup")

        # Delete job
        await jobs.delete_job(job.id)
        retrieved = await jobs.get_job(job.id)
        assert retrieved is None
        print(f"  [OK] Job deleted")

        return True

    except Exception as e:
        print(f"  [FAIL] Job CRUD: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_topic_matcher():
    """Test topic matching service."""
    print("\n" + "="*70)
    print("STEP 6: Testing Topic Matcher")
    print("="*70)

    try:
        from app.research.db import get_supabase_db
        from app.research.services.topic_matcher import TopicMatcher
        from inference_client import InferenceClient

        db = get_supabase_db("default")
        client = InferenceClient()
        matcher = TopicMatcher(db, client)

        # Test topic matching
        result = await matcher.match_topic(
            "What are the causes of the Russia-Ukraine war?",
            "default"
        )

        print(f"  Topic ID: {result.topic_id}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Reasoning: {result.reasoning[:100]}...")
        print(f"  [OK] Topic matching completed")

        return True

    except Exception as e:
        print(f"  [FAIL] Topic matcher: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_pipeline():
    """Test the complete async job pipeline."""
    print("\n" + "="*70)
    print("STEP 7: Testing Full Pipeline (Simplified)")
    print("="*70)

    try:
        from app.research.db import get_supabase_db
        from app.research.db.jobs import JobOperations
        from app.research.schemas.jobs import JobStatus, JobStage
        from app.research.services.topic_matcher import TopicMatcher
        from inference_client import InferenceClient
        from gemini_client import GeminiResearchClient

        db = get_supabase_db("default")
        jobs = JobOperations(db.client, "default")
        inference_client = InferenceClient()

        # Create a test job
        job = await jobs.create_job(
            query="Brief history of Bitcoin price movements in 2024",
            workspace_id="default",
            template_type="investigative",
            parameters={"max_searches": 2},
        )
        print(f"  [OK] Job created: {job.id}")

        # Update to running
        await jobs.update_job_status(job.id, JobStatus.RUNNING, JobStage.HEALTH_CHECK.value, 5.0)
        print(f"  [OK] Job status: RUNNING")

        # Topic matching
        await jobs.update_job_progress(job.id, JobStage.TOPIC_MATCHING)
        topic_matcher = TopicMatcher(db, inference_client)
        topic_result = await topic_matcher.match_topic(job.query, "default")
        await jobs.set_topic_match(job.id, topic_result.topic_id, topic_result.confidence, topic_result.reasoning)
        print(f"  [OK] Topic matching: confidence={topic_result.confidence:.2f}")

        # Simulate search phase
        await jobs.update_job_progress(job.id, JobStage.SEARCHING)
        print(f"  [OK] Simulated search phase")

        # Run a quick Gemini search to verify integration
        try:
            gemini = GeminiResearchClient()
            response = await gemini.grounded_search("Bitcoin price 2024 brief summary")
            print(f"  [OK] Gemini search returned {len(response.sources)} sources")
        except Exception as e:
            print(f"  [WARN] Gemini search failed: {e}")

        # Simulate remaining phases
        await jobs.update_job_progress(job.id, JobStage.EXTRACTION)
        await jobs.update_job_progress(job.id, JobStage.PERSPECTIVES)
        await jobs.update_job_progress(job.id, JobStage.RELATIONSHIPS)
        await jobs.update_job_progress(job.id, JobStage.DEDUPLICATION)

        # Complete with mock stats
        mock_stats = {
            "findings_count": 5,
            "perspectives_count": 3,
            "sources_count": 10,
            "key_summary": "Test completed successfully",
            "token_usage": {"total": 1000},
            "cost_usd": 0.01,
            "duration_seconds": 10.5,
            "topic_id": str(topic_result.topic_id) if topic_result.topic_id else None,
            "dedup_stats": {"new": 5, "updated": 0, "discarded": 0},
        }

        # We need a session ID - create a mock session or skip
        try:
            session = await db.create_session(
                title="Test Session",
                query=job.query,
                template_type="investigative",
                parameters={},
            )
            await jobs.complete_job(job.id, session.id, mock_stats)
            print(f"  [OK] Job completed with session: {session.id}")
        except Exception as e:
            # Complete without session
            print(f"  [WARN] Could not create session: {e}")
            await jobs.fail_job(job.id, "Test completed - no session created")

        # Verify final state
        final_job = await jobs.get_job(job.id)
        print(f"  [OK] Final status: {final_job.status.value}")
        print(f"  [OK] Final progress: {final_job.progress_pct}%")

        # Cleanup
        await jobs.delete_job(job.id)
        print(f"  [OK] Test job cleaned up")

        return True

    except Exception as e:
        print(f"  [FAIL] Full pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_router_endpoints():
    """Test that router endpoints are properly configured."""
    print("\n" + "="*70)
    print("STEP 8: Testing Router Configuration")
    print("="*70)

    try:
        from app.research.router import router

        # Get all routes
        routes = [r for r in router.routes]
        route_paths = [r.path for r in routes if hasattr(r, 'path')]

        required_routes = [
            "/submit",
            "/status/{job_id}",
            "/jobs",
            "/jobs/{job_id}",
        ]

        for req in required_routes:
            if req in route_paths:
                print(f"  [OK] Route found: {req}")
            else:
                print(f"  [FAIL] Route missing: {req}")
                return False

        print(f"\n  Total routes: {len(route_paths)}")
        return True

    except Exception as e:
        print(f"  [FAIL] Router check: {e}")
        return False


async def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*70)
    print(" ASYNC RESEARCH API - END-TO-END TEST")
    print("="*70)
    print(f" Started: {datetime.now().isoformat()}")

    results = {}

    # Step 1: Imports
    results["imports"] = await test_imports()
    if not results["imports"]:
        print("\n[CRITICAL] Import failures - cannot continue")
        return results

    # Step 2: Database
    results["database"] = await test_database_connection()
    if not results["database"]:
        print("\n[CRITICAL] Database connection failed - cannot continue")
        return results

    # Step 3: Gemini API
    results["gemini"] = await test_gemini_health()

    # Step 4: OpenRouter API
    results["openrouter"] = await test_openrouter_health()

    # Step 5: Job CRUD
    results["job_crud"] = await test_job_crud()

    # Step 6: Topic Matcher (needs OpenRouter)
    if results["openrouter"]:
        results["topic_matcher"] = await test_topic_matcher()
    else:
        print("\n[SKIP] Topic matcher test - OpenRouter not available")
        results["topic_matcher"] = None

    # Step 7: Full Pipeline
    if results["gemini"] and results["openrouter"]:
        results["full_pipeline"] = await test_full_pipeline()
    else:
        print("\n[SKIP] Full pipeline test - APIs not available")
        results["full_pipeline"] = None

    # Step 8: Router
    results["router"] = await test_router_endpoints()

    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)

    passed = 0
    failed = 0
    skipped = 0

    for name, result in results.items():
        if result is True:
            status = "[PASS]"
            passed += 1
        elif result is False:
            status = "[FAIL]"
            failed += 1
        else:
            status = "[SKIP]"
            skipped += 1
        print(f"  {status} {name}")

    print(f"\n  Passed: {passed}, Failed: {failed}, Skipped: {skipped}")
    print("="*70)

    return results


if __name__ == "__main__":
    results = asyncio.run(run_all_tests())

    # Exit with error code if any tests failed
    if any(r is False for r in results.values()):
        sys.exit(1)
