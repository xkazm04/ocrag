"""Value-focused evaluation of research capabilities.

Tests the system's ability to:
1. Answer deep "why" questions (causal analysis)
2. Analyze stakeholder motivations
3. Fact-check specific claims
4. Identify patterns and connections

Run with: python -m tests.research.test_value_evaluation
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

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


# Test queries designed to evaluate analytical depth
TEST_QUERIES = {
    "causal_analysis": {
        "query": "Why did Russia invade Ukraine in 2022? What were the key motivations and triggers?",
        "expected_aspects": [
            "NATO expansion concerns",
            "Historical claims to Ukraine",
            "Domestic political factors",
            "Security concerns",
            "2014 Crimea annexation context",
        ],
        "evaluation_criteria": [
            "Identifies multiple causal factors",
            "Distinguishes between stated and actual motivations",
            "Provides historical context",
            "Notes different perspectives on causation",
        ],
    },
    "stakeholder_analysis": {
        "query": "Why are Western countries providing military aid to Ukraine? What are their strategic interests?",
        "expected_aspects": [
            "Security interests",
            "NATO solidarity",
            "Democratic values",
            "Economic considerations",
            "Geopolitical balance",
        ],
        "evaluation_criteria": [
            "Identifies multiple stakeholders",
            "Analyzes motivations for each",
            "Notes potential conflicts of interest",
            "Considers short vs long-term interests",
        ],
    },
    "fact_check": {
        "query": "Verify: Russia claimed the invasion was to 'denazify' Ukraine. What evidence supports or contradicts this claim?",
        "expected_aspects": [
            "Official Russian statements",
            "Ukraine's political composition",
            "Azov Battalion context",
            "International assessments",
            "Historical context of claim",
        ],
        "evaluation_criteria": [
            "Presents the claim clearly",
            "Provides evidence for both sides",
            "Notes credibility of sources",
            "Draws reasoned conclusion",
        ],
    },
}


async def run_research_query(query: str) -> Dict[str, Any]:
    """Run a research query and return full results."""
    from enhanced_harness import EnhancedResearchHarness
    from gemini_client import GeminiResearchClient
    from inference_client import InferenceClient

    gemini_client = GeminiResearchClient()
    inference_client = InferenceClient()

    harness = EnhancedResearchHarness(
        gemini_client=gemini_client,
        inference_client=inference_client,
    )

    result = await harness.run_enhanced_test(
        query=query,
        template_type="investigative",
        max_searches=3,
        granularity="standard",
        run_decomposition=True,
        execute_sub_queries=True,
        run_perspectives=True,
        run_finding_perspectives=False,
        run_relationships=True,
    )

    return result


def evaluate_findings(findings: List[Any], expected_aspects: List[str]) -> Dict[str, Any]:
    """Evaluate findings against expected aspects."""
    findings_text = " ".join([
        f"{getattr(f, 'content', str(f))} {getattr(f, 'summary', '')}"
        for f in findings
    ]).lower()

    covered = []
    missing = []

    for aspect in expected_aspects:
        # Simple keyword matching (could be enhanced with semantic similarity)
        keywords = aspect.lower().split()
        if any(kw in findings_text for kw in keywords):
            covered.append(aspect)
        else:
            missing.append(aspect)

    return {
        "coverage": len(covered) / len(expected_aspects) if expected_aspects else 0,
        "covered_aspects": covered,
        "missing_aspects": missing,
    }


def analyze_perspective_depth(perspectives: List[Any]) -> Dict[str, Any]:
    """Analyze the depth and diversity of perspectives."""
    if not perspectives:
        return {"depth_score": 0, "perspectives_found": []}

    perspective_types = []
    total_insights = 0
    total_recommendations = 0
    total_warnings = 0

    for p in perspectives:
        ptype = getattr(p, 'perspective_type', 'unknown')
        perspective_types.append(ptype)
        total_insights += len(getattr(p, 'key_insights', []))
        total_recommendations += len(getattr(p, 'recommendations', []))
        total_warnings += len(getattr(p, 'warnings', []))

    # Depth score based on variety and content
    type_variety = len(set(perspective_types)) / max(len(perspective_types), 1)
    content_depth = min((total_insights + total_recommendations + total_warnings) / 20, 1.0)

    return {
        "depth_score": (type_variety + content_depth) / 2,
        "perspectives_found": list(set(perspective_types)),
        "total_insights": total_insights,
        "total_recommendations": total_recommendations,
        "total_warnings": total_warnings,
    }


def analyze_relationship_graph(relationships: List[Any]) -> Dict[str, Any]:
    """Analyze the relationship graph for causal connections."""
    if not relationships:
        return {
            "total_relationships": 0,
            "causal_chains": 0,
            "relationship_types": [],
        }

    rel_types = []
    causal_count = 0

    for r in relationships:
        rtype = getattr(r, 'relationship_type', 'unknown')
        rel_types.append(rtype)
        if rtype in ('causes', 'enables', 'precedes', 'influences'):
            causal_count += 1

    return {
        "total_relationships": len(relationships),
        "causal_chains": causal_count,
        "relationship_types": list(set(rel_types)),
    }


async def evaluate_query(name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Run and evaluate a single query."""
    print(f"\n{'='*70}")
    print(f"EVALUATING: {name}")
    print(f"{'='*70}")
    print(f"Query: {config['query'][:80]}...")

    start_time = datetime.now()

    try:
        result = await run_research_query(config['query'])
        duration = (datetime.now() - start_time).total_seconds()

        findings = getattr(result, 'findings', [])
        perspectives = getattr(result, 'perspectives', [])
        relationships = getattr(result, 'relationships', [])
        sources = getattr(result, 'sources', [])

        # Evaluate coverage of expected aspects
        coverage_eval = evaluate_findings(findings, config['expected_aspects'])

        # Evaluate perspective depth
        perspective_eval = analyze_perspective_depth(perspectives)

        # Evaluate relationship graph
        relationship_eval = analyze_relationship_graph(relationships)

        # Print results
        print(f"\n  Duration: {duration:.1f}s")
        print(f"  Findings: {len(findings)}")
        print(f"  Sources: {len(sources)}")
        print(f"  Perspectives: {len(perspectives)}")
        print(f"  Relationships: {len(relationships)}")

        print(f"\n  ASPECT COVERAGE: {coverage_eval['coverage']*100:.0f}%")
        print(f"    Covered: {coverage_eval['covered_aspects']}")
        print(f"    Missing: {coverage_eval['missing_aspects']}")

        print(f"\n  PERSPECTIVE DEPTH: {perspective_eval['depth_score']*100:.0f}%")
        print(f"    Types: {perspective_eval['perspectives_found']}")
        print(f"    Insights: {perspective_eval['total_insights']}")
        print(f"    Warnings: {perspective_eval['total_warnings']}")

        print(f"\n  CAUSAL ANALYSIS:")
        print(f"    Total relationships: {relationship_eval['total_relationships']}")
        print(f"    Causal chains: {relationship_eval['causal_chains']}")
        print(f"    Types: {relationship_eval['relationship_types']}")

        # Sample findings for review
        print(f"\n  SAMPLE FINDINGS:")
        for i, f in enumerate(findings[:5]):
            summary = getattr(f, 'summary', None) or getattr(f, 'content', str(f))[:100]
            ftype = getattr(f, 'finding_type', 'unknown')
            print(f"    [{ftype}] {summary}")

        return {
            "name": name,
            "query": config['query'],
            "success": True,
            "duration": duration,
            "findings_count": len(findings),
            "sources_count": len(sources),
            "perspectives_count": len(perspectives),
            "relationships_count": len(relationships),
            "coverage": coverage_eval,
            "perspective_depth": perspective_eval,
            "relationships": relationship_eval,
        }

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            "name": name,
            "query": config['query'],
            "success": False,
            "error": str(e),
        }


async def run_value_evaluation():
    """Run full value evaluation suite."""
    print("\n" + "="*70)
    print(" RESEARCH VALUE EVALUATION")
    print(" Testing analytical depth, causal reasoning, and fact-checking")
    print("="*70)
    print(f" Started: {datetime.now().isoformat()}")

    results = []

    for name, config in TEST_QUERIES.items():
        result = await evaluate_query(name, config)
        results.append(result)

    # Summary
    print("\n" + "="*70)
    print(" EVALUATION SUMMARY")
    print("="*70)

    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]

    print(f"\n  Tests: {len(results)} total, {len(successful)} passed, {len(failed)} failed")

    if successful:
        avg_coverage = sum(r['coverage']['coverage'] for r in successful) / len(successful)
        avg_depth = sum(r['perspective_depth']['depth_score'] for r in successful) / len(successful)
        avg_findings = sum(r['findings_count'] for r in successful) / len(successful)

        print(f"\n  AVERAGE SCORES:")
        print(f"    Aspect Coverage: {avg_coverage*100:.0f}%")
        print(f"    Perspective Depth: {avg_depth*100:.0f}%")
        print(f"    Findings per query: {avg_findings:.1f}")

    # Value assessment
    print("\n" + "="*70)
    print(" VALUE ASSESSMENT")
    print("="*70)

    value_indicators = []

    if successful:
        # Check if system answers "why" questions
        causal_result = next((r for r in successful if r['name'] == 'causal_analysis'), None)
        if causal_result:
            if causal_result['coverage']['coverage'] >= 0.6:
                value_indicators.append("[+] Strong causal analysis - identifies multiple factors")
            if causal_result['relationships']['causal_chains'] >= 3:
                value_indicators.append("[+] Good relationship mapping for cause-effect chains")

        # Check stakeholder analysis
        stakeholder_result = next((r for r in successful if r['name'] == 'stakeholder_analysis'), None)
        if stakeholder_result:
            if stakeholder_result['coverage']['coverage'] >= 0.6:
                value_indicators.append("[+] Good stakeholder motivation analysis")

        # Check fact-checking capability
        factcheck_result = next((r for r in successful if r['name'] == 'fact_check'), None)
        if factcheck_result:
            if factcheck_result['findings_count'] >= 5:
                value_indicators.append("[+] Gathers evidence for verification")
            if factcheck_result['perspective_depth']['total_warnings'] >= 1:
                value_indicators.append("[+] Identifies potential issues/contradictions")

    if value_indicators:
        print("\n  STRENGTHS IDENTIFIED:")
        for indicator in value_indicators:
            print(f"    {indicator}")
    else:
        print("\n  No strong value indicators found - consider tuning prompts")

    # Suggestions for improvement
    print("\n  POTENTIAL IMPROVEMENTS:")
    if successful:
        all_missing = set()
        for r in successful:
            all_missing.update(r['coverage'].get('missing_aspects', []))
        if all_missing:
            print(f"    - Missing aspects to investigate: {list(all_missing)[:3]}")

    print("\n" + "="*70)

    # Save results
    output_path = _script_dir / "results" / f"value_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved to: {output_path}")

    return results


if __name__ == "__main__":
    results = asyncio.run(run_value_evaluation())
