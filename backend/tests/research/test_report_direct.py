"""Direct unit tests for report generation components.

Imports modules directly to avoid triggering the research __init__ chain.
Run with: python tests/research/test_report_direct.py (from backend dir)
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
    """Test report schema definitions with direct import."""
    print("\n" + "="*60)
    print("TEST: Report Schemas (Direct Import)")
    print("="*60)

    try:
        # Direct import bypassing the research __init__
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "report_schemas",
            _backend_dir / "app" / "research" / "reports" / "schemas.py"
        )
        schemas = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schemas)

        # Test enum values
        assert len(schemas.ReportFormat) == 4
        assert len(schemas.ReportVariant) == 16
        print(f"  [OK] ReportFormat has {len(schemas.ReportFormat)} values")
        print(f"  [OK] ReportVariant has {len(schemas.ReportVariant)} values")

        # Test ReportData
        data = schemas.ReportData(
            session_id=uuid4(),
            session_title="Test Session",
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

        # Test request/response models
        req = schemas.GenerateReportRequest(
            session_id=uuid4(),
            variant=schemas.ReportVariant.EXECUTIVE_SUMMARY,
            format=schemas.ReportFormat.JSON
        )
        print(f"  [OK] GenerateReportRequest created: {req.variant}")

        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_style_guides():
    """Test style guide configurations."""
    print("\n" + "="*60)
    print("TEST: Style Guides (Direct Import)")
    print("="*60)

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "style_guides",
            _backend_dir / "app" / "research" / "reports" / "generators" / "style_guides.py"
        )
        style_guides = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(style_guides)

        # Test all template types
        for template_type in ["investigative", "competitive", "financial", "legal", "general"]:
            guide = style_guides.get_style_guide(template_type)
            assert "tone" in guide
            assert "visual_style" in guide
            print(f"  [OK] {template_type}: {guide['tone'][:40]}...")

        # Test prompt formatting
        guide = style_guides.get_style_guide("financial")
        prompt_text = style_guides.format_style_guide_for_prompt(guide)
        assert "Tone:" in prompt_text
        assert "Visual Style:" in prompt_text
        print(f"  [OK] Style guide formatted to {len(prompt_text)} chars")

        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_base_composer():
    """Test base composer abstract class."""
    print("\n" + "="*60)
    print("TEST: Base Composer (Direct Import)")
    print("="*60)

    try:
        # First load schemas
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "report_schemas",
            _backend_dir / "app" / "research" / "reports" / "schemas.py"
        )
        schemas = importlib.util.module_from_spec(spec)
        sys.modules['app.research.reports.schemas'] = schemas
        spec.loader.exec_module(schemas)

        # Now load base composer
        spec = importlib.util.spec_from_file_location(
            "base_composer",
            _backend_dir / "app" / "research" / "reports" / "composers" / "base.py"
        )
        base = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(base)

        # Test helper methods on a concrete implementation
        class TestComposer(base.BaseComposer):
            def compose(self, data, variant, title=None, include_sections=None):
                return "test"

        composer = TestComposer()

        # Test confidence formatting
        assert "High" in composer._format_confidence(0.85)
        assert "Medium" in composer._format_confidence(0.65)
        assert "Low" in composer._format_confidence(0.35)
        print("  [OK] _format_confidence works correctly")

        # Test section divider
        assert "---" in composer._section_divider()
        print("  [OK] _section_divider works correctly")

        # Test finding formatting
        finding = {
            "finding_type": "fact",
            "content": "Test content",
            "summary": "Test summary",
            "confidence_score": 0.8
        }
        formatted = composer._format_finding(finding)
        assert "FACT" in formatted
        assert "Test summary" in formatted
        print("  [OK] _format_finding works correctly")

        # Test source formatting
        source = {
            "url": "https://example.com",
            "title": "Example",
            "domain": "example.com",
            "credibility_score": 0.8,
            "source_type": "news"
        }
        formatted = composer._format_source(source)
        assert "[Example]" in formatted
        assert "example.com" in formatted
        print("  [OK] _format_source works correctly")

        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_executive_composer():
    """Test executive summary composer."""
    print("\n" + "="*60)
    print("TEST: Executive Summary Composer")
    print("="*60)

    try:
        # Load dependencies
        import importlib.util

        # Load schemas
        spec = importlib.util.spec_from_file_location(
            "report_schemas",
            _backend_dir / "app" / "research" / "reports" / "schemas.py"
        )
        schemas = importlib.util.module_from_spec(spec)
        sys.modules['app.research.reports.schemas'] = schemas
        sys.modules['..schemas'] = schemas
        spec.loader.exec_module(schemas)

        # Load base composer
        spec = importlib.util.spec_from_file_location(
            "base_composer",
            _backend_dir / "app" / "research" / "reports" / "composers" / "base.py"
        )
        base = importlib.util.module_from_spec(spec)
        sys.modules['app.research.reports.composers.base'] = base
        sys.modules['.base'] = base
        spec.loader.exec_module(base)

        # Load executive composer
        spec = importlib.util.spec_from_file_location(
            "executive_composer",
            _backend_dir / "app" / "research" / "reports" / "composers" / "executive.py"
        )
        executive = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(executive)

        # Create mock data
        data = schemas.ReportData(
            session_id=uuid4(),
            session_query="What is the competitive landscape for AI assistants?",
            template_type="competitive",
            status="completed",
            parameters={},
            created_at=datetime.now(),
            completed_at=datetime.now(),
            findings=[
                {
                    "finding_type": "fact",
                    "content": "ChatGPT has 100 million users",
                    "summary": "ChatGPT user base",
                    "confidence_score": 0.9
                },
                {
                    "finding_type": "pattern",
                    "content": "AI assistants are becoming more capable",
                    "confidence_score": 0.75
                }
            ],
            perspectives=[
                {
                    "perspective_type": "competitive_advantage",
                    "analysis_text": "The market is highly competitive.",
                    "key_insights": ["Strong network effects"],
                    "recommendations": ["Focus on differentiation"],
                    "warnings": ["Rapid pace of change"],
                    "confidence": 0.8
                }
            ],
            sources=[
                {
                    "url": "https://example.com/ai-report",
                    "title": "AI Industry Report 2024",
                    "domain": "example.com",
                    "credibility_score": 0.8,
                    "source_type": "research_report"
                }
            ],
            claims=[]
        )

        # Generate executive summary
        composer = executive.ExecutiveSummaryComposer()
        markdown = composer.compose(data, schemas.ReportVariant.EXECUTIVE_SUMMARY)

        # Validate output
        word_count = len(markdown.split())
        assert word_count > 50, f"Only {word_count} words"
        assert "# Executive Summary" in markdown or "# " in markdown
        assert "Findings" in markdown
        print(f"  [OK] Executive summary: {word_count} words")

        # Print preview
        preview = markdown[:300].replace("\n", " ")
        print(f"      Preview: {preview}...")

        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def test_html_generator():
    """Test HTML generator fallback."""
    print("\n" + "="*60)
    print("TEST: HTML Generator Fallback")
    print("="*60)

    try:
        # Load style guides
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "style_guides",
            _backend_dir / "app" / "research" / "reports" / "generators" / "style_guides.py"
        )
        style_guides = importlib.util.module_from_spec(spec)
        sys.modules['app.research.reports.generators.style_guides'] = style_guides
        sys.modules['.style_guides'] = style_guides
        spec.loader.exec_module(style_guides)

        # Load schemas (mock)
        spec = importlib.util.spec_from_file_location(
            "report_schemas",
            _backend_dir / "app" / "research" / "reports" / "schemas.py"
        )
        schemas = importlib.util.module_from_spec(spec)
        sys.modules['app.research.reports.schemas'] = schemas
        sys.modules['..schemas'] = schemas
        spec.loader.exec_module(schemas)

        # Load HTML generator
        spec = importlib.util.spec_from_file_location(
            "html_generator",
            _backend_dir / "app" / "research" / "reports" / "generators" / "html_generator.py"
        )
        html_gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(html_gen)

        # Create generator with dummy key (won't be used for fallback)
        generator = html_gen.HTMLGenerator(api_key="test", model="test")

        markdown = """# Test Report

**Research Query:** AI landscape analysis

## Key Findings

- Finding one with **bold**
- Finding two with *italics*

### Details

This is a paragraph with [a link](https://example.com).

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
        assert "</html>" in html

        print(f"  [OK] Fallback HTML generated: {len(html)} chars")
        print(f"      Has DOCTYPE: {html.startswith('<!DOCTYPE')}")
        print(f"      Has styles: {'<style>' in html}")

        return True

    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all unit tests."""
    print("\n" + "="*60)
    print(" REPORT GENERATION UNIT TESTS (DIRECT IMPORTS)")
    print("="*60)
    print(f" Started: {datetime.now().isoformat()}")

    tests = [
        ("schemas", test_report_schemas),
        ("style_guides", test_style_guides),
        ("base_composer", test_base_composer),
        ("executive_composer", test_executive_composer),
        ("html_generator", test_html_generator),
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
