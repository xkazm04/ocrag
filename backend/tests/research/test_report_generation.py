"""End-to-end test for report generation API.

Tests the complete report generation flow:
1. Module imports
2. Data aggregation from database
3. Markdown composition for all variants
4. HTML generation via OpenRouter
5. PDF generation (if weasyprint available)

Run with: python -m tests.research.test_report_generation
Or: python tests/research/test_report_generation.py (from backend dir)
"""

import asyncio
import os
import sys
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
    """Test that all report generation modules can be imported."""
    print("\n" + "="*70)
    print("STEP 1: Testing Report Generation Imports")
    print("="*70)

    errors = []

    # Test schema imports
    try:
        from app.research.reports.schemas import (
            GenerateReportRequest, ReportResponse, ReportFormat,
            ReportVariant, ReportData, ReportMetadata
        )
        print("  [OK] Report schemas imported")
    except ImportError as e:
        errors.append(f"Report schemas: {e}")
        print(f"  [FAIL] Report schemas: {e}")

    # Test composer imports
    try:
        from app.research.reports.composers import (
            BaseComposer, get_composer, COMPOSER_REGISTRY,
            ExecutiveSummaryComposer, FullReportComposer,
            InvestigativeComposer, CompetitiveComposer,
            FinancialComposer, LegalComposer
        )
        print(f"  [OK] Composers imported ({len(COMPOSER_REGISTRY)} variants)")
    except ImportError as e:
        errors.append(f"Composers: {e}")
        print(f"  [FAIL] Composers: {e}")

    # Test generator imports
    try:
        from app.research.reports.generators import (
            HTMLGenerator, create_html_generator,
            is_pdf_available, get_style_guide
        )
        print(f"  [OK] Generators imported (PDF available: {is_pdf_available()})")
    except ImportError as e:
        errors.append(f"Generators: {e}")
        print(f"  [FAIL] Generators: {e}")

    # Test aggregator import
    try:
        from app.research.reports.data.aggregator import ReportDataAggregator
        print("  [OK] Data aggregator imported")
    except ImportError as e:
        errors.append(f"Data aggregator: {e}")
        print(f"  [FAIL] Data aggregator: {e}")

    # Test service import
    try:
        from app.research.reports.service import ReportGenerationService
        print("  [OK] Report service imported")
    except ImportError as e:
        errors.append(f"Report service: {e}")
        print(f"  [FAIL] Report service: {e}")

    # Test router import
    try:
        from app.research.reports.router import router
        print("  [OK] Report router imported")
    except ImportError as e:
        errors.append(f"Report router: {e}")
        print(f"  [FAIL] Report router: {e}")

    if errors:
        print(f"\n  IMPORT ERRORS: {len(errors)}")
        return False

    print("\n  All report generation imports successful!")
    return True


async def test_database_connection():
    """Test database connection for research data."""
    print("\n" + "="*70)
    print("STEP 2: Testing Database Connection")
    print("="*70)

    try:
        from app.research.db import get_supabase_db

        db = get_supabase_db("default")
        print("  [OK] Database client created")

        # Test session query
        result = db.client.table("research_sessions").select("id, title, template_type").limit(5).execute()
        print(f"  [OK] Found {len(result.data)} research sessions")

        if result.data:
            for session in result.data[:3]:
                print(f"      - {session['id'][:8]}... ({session['template_type']}): {session.get('title', 'No title')[:40]}")

        return True, result.data
    except Exception as e:
        print(f"  [FAIL] Database connection: {e}")
        return False, []


async def test_data_aggregation(session_id: UUID):
    """Test data aggregation for a session."""
    print("\n" + "="*70)
    print(f"STEP 3: Testing Data Aggregation for Session {str(session_id)[:8]}...")
    print("="*70)

    try:
        from app.research.db import get_supabase_db
        from app.research.reports.data.aggregator import ReportDataAggregator

        db = get_supabase_db("default")
        aggregator = ReportDataAggregator(db)

        data = await aggregator.aggregate(session_id)

        print(f"  [OK] Data aggregated successfully:")
        print(f"      - Query: {data.session_query[:50]}...")
        print(f"      - Template: {data.template_type}")
        print(f"      - Status: {data.status}")
        print(f"      - Findings: {len(data.findings)}")
        print(f"      - Perspectives: {len(data.perspectives)}")
        print(f"      - Sources: {len(data.sources)}")
        print(f"      - Claims: {len(data.claims)}")
        print(f"      - High confidence findings: {len(data.high_confidence_findings)}")

        return True, data
    except Exception as e:
        print(f"  [FAIL] Data aggregation: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_markdown_composition(data):
    """Test markdown composition for all variants."""
    print("\n" + "="*70)
    print("STEP 4: Testing Markdown Composition")
    print("="*70)

    try:
        from app.research.reports.composers import get_composer, COMPOSER_REGISTRY
        from app.research.reports.schemas import ReportVariant

        results = {}

        for variant_name in COMPOSER_REGISTRY.keys():
            try:
                variant = ReportVariant(variant_name)
                composer = get_composer(variant_name)
                markdown = composer.compose(data, variant)

                # Basic validation
                word_count = len(markdown.split())
                has_header = markdown.startswith("#")

                results[variant_name] = {
                    "success": True,
                    "chars": len(markdown),
                    "words": word_count,
                    "has_header": has_header
                }
                print(f"  [OK] {variant_name}: {word_count} words, {len(markdown)} chars")

            except Exception as e:
                results[variant_name] = {"success": False, "error": str(e)}
                print(f"  [FAIL] {variant_name}: {e}")

        success_count = sum(1 for r in results.values() if r.get("success"))
        print(f"\n  Composition results: {success_count}/{len(results)} variants successful")

        return success_count == len(results), results

    except Exception as e:
        print(f"  [FAIL] Markdown composition: {e}")
        return False, {}


async def test_html_generation(data):
    """Test HTML generation via OpenRouter."""
    print("\n" + "="*70)
    print("STEP 5: Testing HTML Generation")
    print("="*70)

    try:
        from app.research.reports.composers import get_composer
        from app.research.reports.schemas import ReportVariant
        from app.research.reports.generators import create_html_generator

        # Generate markdown first
        composer = get_composer("executive_summary")
        markdown = composer.compose(data, ReportVariant.EXECUTIVE_SUMMARY)
        print(f"  [OK] Markdown generated: {len(markdown)} chars")

        # Try HTML generation
        try:
            generator = create_html_generator()
            html = await generator.generate(
                markdown_content=markdown,
                template_type=data.template_type,
                title="Test Report"
            )

            # Validate HTML
            has_doctype = html.lower().startswith("<!doctype")
            has_style = "<style" in html.lower()
            has_body = "<body" in html.lower()

            print(f"  [OK] HTML generated: {len(html)} chars")
            print(f"      - Has DOCTYPE: {has_doctype}")
            print(f"      - Has embedded styles: {has_style}")
            print(f"      - Has body: {has_body}")

            return True, html

        except Exception as e:
            print(f"  [WARN] LLM HTML generation failed: {e}")
            print("  [INFO] Testing fallback HTML generation...")

            # Test fallback
            generator = create_html_generator()
            html = generator.generate_fallback_html(
                markdown_content=markdown,
                title="Test Report",
                template_type=data.template_type
            )

            print(f"  [OK] Fallback HTML generated: {len(html)} chars")
            return True, html

    except Exception as e:
        print(f"  [FAIL] HTML generation: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_pdf_generation(html_content: str):
    """Test PDF generation from HTML."""
    print("\n" + "="*70)
    print("STEP 6: Testing PDF Generation")
    print("="*70)

    try:
        from app.research.reports.generators import is_pdf_available

        if not is_pdf_available():
            print("  [SKIP] PDF generation not available (weasyprint not installed)")
            print("  [INFO] Install with: pip install weasyprint>=60.0")
            return None

        from app.research.reports.generators import create_pdf_generator

        generator = create_pdf_generator()
        pdf_bytes = generator.generate(html_content)

        print(f"  [OK] PDF generated: {len(pdf_bytes)} bytes")

        # Basic PDF validation
        is_valid_pdf = pdf_bytes[:4] == b'%PDF'
        print(f"      - Valid PDF header: {is_valid_pdf}")

        # Optionally save to file for inspection
        output_path = _backend_dir / "test_report_output.pdf"
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        print(f"      - Saved to: {output_path}")

        return True

    except Exception as e:
        print(f"  [FAIL] PDF generation: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_service(session_id: UUID):
    """Test the complete report generation service."""
    print("\n" + "="*70)
    print("STEP 7: Testing Full Report Service")
    print("="*70)

    try:
        from app.research.db import get_supabase_db
        from app.research.reports.service import ReportGenerationService
        from app.research.reports.schemas import GenerateReportRequest, ReportFormat, ReportVariant

        db = get_supabase_db("default")
        service = ReportGenerationService(db)

        # Test JSON format
        request = GenerateReportRequest(
            session_id=session_id,
            variant=ReportVariant.EXECUTIVE_SUMMARY,
            format=ReportFormat.JSON
        )

        response = await service.generate_report(request)

        print(f"  [OK] Report generated successfully:")
        print(f"      - Title: {response.title[:50]}...")
        print(f"      - Variant: {response.variant}")
        print(f"      - Format: {response.format}")
        print(f"      - Markdown: {len(response.markdown_content)} chars")
        print(f"      - Findings count: {response.metadata.findings_count}")
        print(f"      - Sources count: {response.metadata.sources_count}")

        # Test variant listing
        variants = service.get_available_variants(response.metadata.template_type)
        print(f"      - Available variants: {len(variants)}")

        return True, response

    except Exception as e:
        print(f"  [FAIL] Report service: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_router_endpoints():
    """Test that router endpoints are properly configured."""
    print("\n" + "="*70)
    print("STEP 8: Testing Router Configuration")
    print("="*70)

    try:
        from app.research.reports.router import router

        routes = [r for r in router.routes]
        route_paths = [r.path for r in routes if hasattr(r, 'path')]

        required_routes = [
            "/generate",
            "/variants",
            "/formats",
            "/preview/{session_id}",
        ]

        all_found = True
        for req in required_routes:
            if req in route_paths:
                print(f"  [OK] Route found: {req}")
            else:
                print(f"  [FAIL] Route missing: {req}")
                all_found = False

        print(f"\n  Total routes: {len(route_paths)}")
        return all_found

    except Exception as e:
        print(f"  [FAIL] Router check: {e}")
        return False


async def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*70)
    print(" REPORT GENERATION - END-TO-END TEST")
    print("="*70)
    print(f" Started: {datetime.now().isoformat()}")

    results = {}

    # Step 1: Imports
    results["imports"] = await test_imports()
    if not results["imports"]:
        print("\n[CRITICAL] Import failures - cannot continue")
        return results

    # Step 2: Database
    db_success, sessions = await test_database_connection()
    results["database"] = db_success
    if not db_success:
        print("\n[CRITICAL] Database connection failed - cannot continue")
        return results

    # Find a session to test with
    if not sessions:
        print("\n[CRITICAL] No research sessions found - cannot test report generation")
        results["no_data"] = True
        return results

    # Pick the first session with data
    test_session_id = UUID(sessions[0]["id"])
    print(f"\n  Using session for testing: {test_session_id}")

    # Step 3: Data Aggregation
    agg_success, data = await test_data_aggregation(test_session_id)
    results["aggregation"] = agg_success

    if not agg_success or not data:
        print("\n[CRITICAL] Data aggregation failed - cannot continue")
        return results

    # Step 4: Markdown Composition
    comp_success, comp_results = await test_markdown_composition(data)
    results["composition"] = comp_success

    # Step 5: HTML Generation
    html_success, html_content = await test_html_generation(data)
    results["html_generation"] = html_success

    # Step 6: PDF Generation (optional)
    if html_content:
        results["pdf_generation"] = await test_pdf_generation(html_content)
    else:
        results["pdf_generation"] = None

    # Step 7: Full Service
    service_success, response = await test_full_service(test_session_id)
    results["full_service"] = service_success

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
