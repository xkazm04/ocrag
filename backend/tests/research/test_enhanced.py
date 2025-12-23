#!/usr/bin/env python
"""Test the enhanced research harness with all new features."""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")

# Results directory
RESULTS_DIR = Path(__file__).parent / "results"


def ensure_results_dir():
    """Ensure results directory exists."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def save_enhanced_result(result, filename: str = None):
    """Save enhanced test result to JSON."""
    ensure_results_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not filename:
        filename = f"enhanced_test_{timestamp}.json"

    output_path = RESULTS_DIR / filename

    # Build result dict
    data = {
        "query": result.query,
        "template_type": result.template_type,
        "timestamp": timestamp,
        "duration_seconds": (
            (result.completed_at - result.started_at).seconds
            if result.completed_at else 0
        ),

        # Decomposition
        "decomposition": None,

        # Search
        "search_queries": result.search_queries,
        "sources": [
            {
                "url": s.url,
                "title": s.title,
                "domain": s.domain,
                "snippet": s.snippet[:200],
            }
            for s in result.sources[:20]
        ],

        # Findings
        "findings": [
            {
                "type": f.finding_type,
                "content": f.content,
                "summary": f.summary,
                "date_text": f.date_text,
                "temporal_context": f.temporal_context,
            }
            for f in result.findings
        ],

        # Timeline
        "timeline": [
            {
                "date": e.extracted_date.display_text,
                "summary": e.summary,
                "content": e.content[:200],
            }
            for e in result.timeline
        ],

        # Perspectives
        "perspectives": {},

        # Relationship Graph
        "relationship_graph": None,

        # Metrics
        "metrics": {
            "total_tokens": result.token_stats.total_tokens,
            "input_tokens": result.token_stats.input_tokens,
            "output_tokens": result.token_stats.output_tokens,
            "total_cost_usd": result.total_cost_usd,
            "tokens_search": result.tokens_search,
            "tokens_extraction": result.tokens_extraction,
            "tokens_perspectives": result.tokens_perspectives,
            "tokens_relationships": result.tokens_relationships,
        },

        "errors": result.errors,
    }

    # Add decomposition
    if result.decomposition:
        data["decomposition"] = {
            "needs_decomposition": result.decomposition.needs_decomposition,
            "strategy": result.decomposition.strategy.value,
            "detected_themes": result.decomposition.detected_themes,
            "detected_actors": result.decomposition.detected_actors,
            "date_range_years": result.decomposition.date_range_years,
            "sub_queries": [
                {
                    "id": sq.id,
                    "query": sq.query,
                    "focus_theme": sq.focus_theme,
                    "batch_order": sq.batch_order,
                    "composition_role": sq.composition_role,
                }
                for sq in result.decomposition.sub_queries
            ],
        }

    # Add perspectives
    if result.topic_perspectives:
        for ptype, analysis in result.topic_perspectives.analyses.items():
            data["perspectives"][ptype.value] = {
                "analysis": analysis.analysis,
                "data": analysis.to_dict() if hasattr(analysis, 'to_dict') else {},
            }

    # Add relationship graph
    if result.relationship_graph:
        data["relationship_graph"] = {
            "relationships": [
                {
                    "source": r.source_finding_id,
                    "target": r.target_finding_id,
                    "type": r.relationship_type.value,
                    "description": r.description,
                    "strength": r.strength,
                }
                for r in result.relationship_graph.relationships
            ],
            "contradictions": [
                {
                    "finding_1": c.finding_id_1,
                    "finding_2": c.finding_id_2,
                    "claim_1": c.claim_1,
                    "claim_2": c.claim_2,
                    "significance": c.significance,
                    "resolution_hint": c.resolution_hint,
                }
                for c in result.relationship_graph.contradictions
            ],
            "gaps": [
                {
                    "type": g.gap_type.value,
                    "description": g.description,
                    "priority": g.priority,
                    "suggested_queries": g.suggested_queries,
                }
                for g in result.relationship_graph.gaps
            ],
            "causal_chains": [
                {
                    "finding_ids": c.finding_ids,
                    "descriptions": c.descriptions,
                }
                for c in result.relationship_graph.causal_chains
            ],
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nResult saved to: {output_path}")
    return output_path


async def test_enhanced_harness():
    """Run a complete enhanced research test."""
    print("=" * 70)
    print("ENHANCED RESEARCH HARNESS TEST")
    print("=" * 70)

    from enhanced_harness import EnhancedResearchHarness

    harness = EnhancedResearchHarness()

    # Run enhanced test with ALL features enabled
    result = await harness.run_enhanced_test(
        query="Why did the Russia-Ukraine war start? What were the key events and actors?",
        template_type="investigative",
        max_searches=4,
        granularity="standard",
        run_decomposition=True,
        run_perspectives=True,
        run_relationships=True,
    )

    # Save to JSON
    output_path = save_enhanced_result(result)

    # Print summary
    print("\n" + "=" * 70)
    print("ENHANCED TEST SUMMARY")
    print("=" * 70)

    # Decomposition
    if result.decomposition:
        print(f"\n--- Decomposition ---")
        print(f"  Needs decomposition: {result.decomposition.needs_decomposition}")
        print(f"  Strategy: {result.decomposition.strategy.value}")
        print(f"  Themes detected: {result.decomposition.detected_themes}")

    # Findings
    print(f"\n--- Findings ({len(result.findings)}) ---")
    by_type = {}
    for f in result.findings:
        by_type[f.finding_type] = by_type.get(f.finding_type, 0) + 1
    for ftype, count in sorted(by_type.items()):
        print(f"  {ftype}: {count}")

    # Perspectives
    if result.topic_perspectives:
        print(f"\n--- Perspectives ({len(result.topic_perspectives.analyses)}) ---")
        for ptype, analysis in result.topic_perspectives.analyses.items():
            preview = analysis.analysis[:100] if analysis.analysis else "N/A"
            print(f"  [{ptype.value}]")
            print(f"    {preview}...")

    # Relationships
    if result.relationship_graph:
        print(f"\n--- Relationship Graph ---")
        print(f"  Relationships: {len(result.relationship_graph.relationships)}")
        for r in result.relationship_graph.relationships[:5]:
            print(f"    {r.source_finding_id} --{r.relationship_type.value}--> {r.target_finding_id}")

        print(f"\n  Contradictions: {len(result.relationship_graph.contradictions)}")
        for c in result.relationship_graph.contradictions[:2]:
            print(f"    [{c.finding_id_1}] vs [{c.finding_id_2}]: {c.significance[:60]}...")

        print(f"\n  Research Gaps: {len(result.relationship_graph.gaps)}")
        for g in result.relationship_graph.gaps[:3]:
            print(f"    [{g.gap_type.value}] {g.description[:60]}...")

    # Timeline
    if result.timeline:
        print(f"\n--- Timeline ({len(result.timeline)} events) ---")
        for event in result.timeline[:5]:
            date_str = event.extracted_date.display_text
            print(f"  {date_str}: {event.summary[:50]}...")

    # Metrics
    print(f"\n--- Metrics ---")
    print(f"  Total tokens: {result.token_stats.total_tokens:,}")
    print(f"  Total cost: ${result.total_cost_usd:.4f}")
    if result.completed_at and result.started_at:
        duration = (result.completed_at - result.started_at).seconds
        print(f"  Duration: {duration}s")

    print("\n" + "=" * 70)
    print("Enhanced test completed!")
    print("=" * 70)

    return result


if __name__ == "__main__":
    asyncio.run(test_enhanced_harness())
