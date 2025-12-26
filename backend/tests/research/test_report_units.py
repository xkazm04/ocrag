"""Unit tests for report generation components.

Tests individual components without full import chain.
Run with: python tests/research/test_report_units.py (from backend dir)
"""

import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Setup path
_script_dir = Path(__file__).parent
_backend_dir = _script_dir.parent.parent
sys.path.insert(0, str(_backend_dir))


def test_report_schemas():
    """Test report schema definitions."""
    print("\n" + "="*60)
    print("TEST: Report Schemas")
    print("="*60)

    try:
        from app.research.reports.schemas import (
            GenerateReportRequest, ReportResponse, ReportFormat,
            ReportVariant, ReportData, ReportMetadata
        )

        # Test enum values
        assert len(ReportFormat) == 4
        assert len(ReportVariant) == 16
        print(f"  [OK] ReportFormat has {len(ReportFormat)} values")
        print(f"  [OK] ReportVariant has {len(ReportVariant)} values")

        # Test ReportData
        data = ReportData(
            session_id=uuid4(),
            session_query="Test query",
            template_type="investigative",
            status="completed",
            parameters={},
            created_at=datetime.now(),
            completed_at=datetime.now(),
            findings=[
                {"finding_type": "fact", "content": "Test fact", "confidence_score": 0.8},
                {"finding_type": "event", "content": "Test event", "confidence_score": 0.5},
            ],
            perspectives=[],
            sources=[],
            claims=[]
        )

        assert len(data.high_confidence_findings) == 1
        print(f"  [OK] ReportData with {len(data.findings)} findings, {len(data.high_confidence_findings)} high confidence")

        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_style_guides():
    """Test style guide configurations."""
    print("\n" + "="*60)
    print("TEST: Style Guides")
    print("="*60)

    try:
        from app.research.reports.generators.style_guides import (
            TEMPLATE_STYLE_GUIDES, get_style_guide, format_style_guide_for_prompt
        )

        # Test all template types
        for template_type in ["investigative", "competitive", "financial", "legal", "general"]:
            guide = get_style_guide(template_type)
            assert "tone" in guide
            assert "visual_style" in guide
            print(f"  [OK] {template_type}: {guide['tone'][:40]}...")

        # Test prompt formatting
        guide = get_style_guide("financial")
        prompt_text = format_style_guide_for_prompt(guide)
        assert "Tone:" in prompt_text
        assert "Visual Style:" in prompt_text
        print(f"  [OK] Style guide formatted to {len(prompt_text)} chars")

        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_composer_registry():
    """Test composer registry and variant mapping."""
    print("\n" + "="*60)
    print("TEST: Composer Registry")
    print("="*60)

    try:
        from app.research.reports.composers import COMPOSER_REGISTRY, get_composer

        # Verify all 16 variants are registered
        expected_variants = [
            "executive_summary", "full_report", "findings_only", "source_bibliography",
            "timeline_report", "actor_dossier", "evidence_brief",
            "competitive_matrix", "swot_analysis", "battlecard",
            "investment_thesis", "earnings_summary", "risk_assessment",
            "legal_brief", "case_digest", "compliance_checklist"
        ]

        for variant in expected_variants:
            assert variant in COMPOSER_REGISTRY, f"Missing variant: {variant}"
            composer = get_composer(variant)
            assert composer is not None
            print(f"  [OK] {variant}: {composer.__class__.__name__}")

        print(f"\n  [OK] All {len(expected_variants)} variants registered")
        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_markdown_composition():
    """Test markdown composition with mock data."""
    print("\n" + "="*60)
    print("TEST: Markdown Composition")
    print("="*60)

    try:
        from app.research.reports.schemas import ReportData, ReportVariant
        from app.research.reports.composers import get_composer

        # Create mock data
        data = ReportData(
            session_id=uuid4(),
            session_query="What is the competitive landscape for AI assistants?",
            template_type="competitive",
            status="completed",
            parameters={"max_searches": 10, "granularity": "detailed"},
            created_at=datetime.now(),
            completed_at=datetime.now(),
            findings=[
                {
                    "finding_type": "fact",
                    "content": "ChatGPT has 100 million users as of 2024",
                    "summary": "ChatGPT user base",
                    "confidence_score": 0.9
                },
                {
                    "finding_type": "actor",
                    "content": "OpenAI is a leading AI research company",
                    "summary": "OpenAI",
                    "confidence_score": 0.85,
                    "extracted_data": {"market_position": "Leader"}
                },
                {
                    "finding_type": "pattern",
                    "content": "AI assistants are becoming increasingly capable",
                    "summary": "AI capability trend",
                    "confidence_score": 0.75
                },
                {
                    "finding_type": "gap",
                    "content": "Limited data on enterprise adoption rates",
                    "confidence_score": 0.6
                }
            ],
            perspectives=[
                {
                    "perspective_type": "competitive_advantage",
                    "analysis_text": "The market is highly competitive with several major players.",
                    "key_insights": ["Strong network effects", "Data moats are crucial"],
                    "recommendations": ["Focus on differentiation", "Build unique datasets"],
                    "warnings": ["Rapid pace of change"],
                    "confidence": 0.8
                }
            ],
            sources=[
                {
                    "url": "https://example.com/ai-report",
                    "title": "AI Industry Report 2024",
                    "domain": "example.com",
                    "snippet": "Comprehensive analysis of the AI industry...",
                    "credibility_score": 0.8,
                    "source_type": "research_report"
                }
            ],
            claims=[]
        )

        # Test a few key variants
        test_variants = [
            ("executive_summary", 200),
            ("competitive_matrix", 100),
            ("swot_analysis", 150),
        ]

        for variant_name, min_words in test_variants:
            variant = ReportVariant(variant_name)
            composer = get_composer(variant_name)
            markdown = composer.compose(data, variant)

            word_count = len(markdown.split())
            has_header = markdown.startswith("#")

            assert word_count >= min_words, f"{variant_name}: only {word_count} words"
            assert has_header, f"{variant_name}: missing header"

            print(f"  [OK] {variant_name}: {word_count} words")
            # Print first 200 chars
            preview = markdown[:200].replace("\n", " ")
            print(f"      Preview: {preview}...")

        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_html_fallback():
    """Test fallback HTML generation (no LLM)."""
    print("\n" + "="*60)
    print("TEST: HTML Fallback Generation")
    print("="*60)

    try:
        from app.research.reports.generators.html_generator import HTMLGenerator

        # Create generator with dummy key (won't be used for fallback)
        generator = HTMLGenerator(api_key="test", model="test")

        markdown = """# Test Report

**Research Query:** AI landscape analysis

## Key Findings

- Finding one with **bold**
- Finding two with *italics*

### Details

This is a paragraph with [a link](https://example.com).

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |

---

*Generated by test*
"""

        html = generator.generate_fallback_html(
            markdown_content=markdown,
            title="Test Report",
            template_type="competitive"
        )

        # Validate HTML
        assert html.startswith("<!DOCTYPE html>")
        assert "<style>" in html
        assert "<h1>" in html
        assert "</html>" in html

        print(f"  [OK] HTML generated: {len(html)} chars")
        print(f"      Has DOCTYPE: {html.startswith('<!DOCTYPE')}")
        print(f"      Has styles: {'<style>' in html}")

        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pdf_availability():
    """Test PDF generator availability."""
    print("\n" + "="*60)
    print("TEST: PDF Generator")
    print("="*60)

    try:
        from app.research.reports.generators import is_pdf_available

        available = is_pdf_available()
        print(f"  [INFO] WeasyPrint available: {available}")

        if available:
            from app.research.reports.generators import create_pdf_generator

            generator = create_pdf_generator()
            print(f"  [OK] PDF generator created")

            # Test with minimal HTML
            html = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Test PDF</h1><p>Hello world</p></body>
</html>"""

            pdf_bytes = generator.generate(html)
            assert pdf_bytes[:4] == b'%PDF'
            print(f"  [OK] PDF generated: {len(pdf_bytes)} bytes")
        else:
            print("  [SKIP] WeasyPrint not installed")
            print("  [INFO] Install with: pip install weasyprint>=60.0")

        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all unit tests."""
    print("\n" + "="*60)
    print(" REPORT GENERATION UNIT TESTS")
    print("="*60)
    print(f" Started: {datetime.now().isoformat()}")

    tests = [
        ("schemas", test_report_schemas),
        ("style_guides", test_style_guides),
        ("composer_registry", test_composer_registry),
        ("markdown_composition", test_markdown_composition),
        ("html_fallback", test_html_fallback),
        ("pdf_availability", test_pdf_availability),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n  [ERROR] {name}: {e}")
            results[name] = False

    # Summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)

    passed = sum(1 for r in results.values() if r)
    failed = len(results) - passed

    for name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\n  Passed: {passed}, Failed: {failed}")
    print("="*60)

    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
