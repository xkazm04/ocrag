#!/usr/bin/env python
"""Test the perspective agents."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")


async def test_perspectives():
    """Test perspective agents on Ukraine war topic."""
    print("=" * 70)
    print("PERSPECTIVE AGENTS TEST")
    print("=" * 70)

    from perspectives import PerspectiveRunner, PerspectiveContext
    from schemas.perspective import PerspectiveType

    # Create test context
    context = PerspectiveContext(
        topic="Why did the Russia-Ukraine war start?",
        topic_summary="""
        The Russia-Ukraine war has complex origins dating back to the 2014 annexation
        of Crimea and the Donbas conflict. Key factors include NATO expansion concerns,
        historical ties between Russia and Ukraine, the 2014 Maidan Revolution, and
        the failure of the Minsk agreements. The full-scale invasion began on
        February 24, 2022.
        """,
        finding_summaries=[
            "Russia annexed Crimea in March 2014 following the Maidan Revolution",
            "The Minsk agreements (2014-2015) failed to resolve the Donbas conflict",
            "Putin cited NATO expansion as a key security concern",
            "Ukraine has significant natural gas transit infrastructure",
            "The war has caused massive displacement and humanitarian crisis",
            "Western sanctions have impacted the Russian economy significantly",
            "Wagner Group played a major role in the early conflict",
        ],
        actors=[
            "Vladimir Putin",
            "Volodymyr Zelenskyy",
            "NATO",
            "European Union",
            "United States",
            "Wagner Group",
        ],
        events=[
            "2014 Crimea annexation",
            "2022 full-scale invasion",
            "Maidan Revolution",
            "Minsk agreements",
        ],
        allow_training_data=True,
    )

    # Test 1: Run single perspective (Historical)
    print("\n--- Test 1: Historical Perspective Only ---")
    runner = PerspectiveRunner(perspectives=[PerspectiveType.HISTORICAL])
    result = await runner.run_topic_analysis(context, parallel=True)

    if PerspectiveType.HISTORICAL in result.analyses:
        hist = result.analyses[PerspectiveType.HISTORICAL]
        print(f"\n  Analysis (first 300 chars):")
        print(f"    {hist.analysis[:300]}...")
        print(f"\n  Historical Parallels: {hist.historical_parallels[:2]}")
        print(f"\n  Historical Patterns: {hist.historical_patterns[:2]}")
        print(f"\n  Likely Consequences: {hist.likely_consequences[:2]}")

    # Test 2: Run Financial perspective
    print("\n--- Test 2: Financial Perspective ---")
    runner = PerspectiveRunner(perspectives=[PerspectiveType.FINANCIAL])
    result = await runner.run_topic_analysis(context, parallel=True)

    if PerspectiveType.FINANCIAL in result.analyses:
        fin = result.analyses[PerspectiveType.FINANCIAL]
        print(f"\n  Analysis (first 300 chars):")
        print(f"    {fin.analysis[:300]}...")
        print(f"\n  Cui Bono: {fin.cui_bono[:3]}")
        print(f"\n  Financial Mechanisms: {fin.financial_mechanisms[:2]}")
        print(f"\n  Sanctions Relevance: {fin.sanctions_relevance[:100]}..." if fin.sanctions_relevance else "  N/A")

    # Test 3: Run Journalist perspective
    print("\n--- Test 3: Journalist Perspective ---")
    runner = PerspectiveRunner(perspectives=[PerspectiveType.JOURNALIST])
    result = await runner.run_topic_analysis(context, parallel=True)

    if PerspectiveType.JOURNALIST in result.analyses:
        jour = result.analyses[PerspectiveType.JOURNALIST]
        print(f"\n  Analysis (first 300 chars):")
        print(f"    {jour.analysis[:300]}...")
        print(f"\n  Propaganda Indicators: {jour.propaganda_indicators[:3]}")
        print(f"\n  Contradictions ({len(jour.contradictions_found)}):")
        for c in jour.contradictions_found[:2]:
            print(f"    - Claim 1: {c.claim1[:50]}...")
            print(f"      Claim 2: {c.claim2[:50]}...")
        print(f"\n  Unanswered Questions: {jour.unanswered_questions[:3]}")

    # Test 4: Run Conspirator perspective
    print("\n--- Test 4: Conspirator (Intelligence Analyst) Perspective ---")
    runner = PerspectiveRunner(perspectives=[PerspectiveType.CONSPIRATOR])
    result = await runner.run_topic_analysis(context, parallel=True)

    if PerspectiveType.CONSPIRATOR in result.analyses:
        cons = result.analyses[PerspectiveType.CONSPIRATOR]
        print(f"\n  Theory: {cons.theory[:200]}...")
        print(f"\n  Probability: {cons.theory_probability.value}")
        print(f"\n  Supporting Evidence ({len(cons.supporting_evidence)}):")
        for e in cons.supporting_evidence[:2]:
            print(f"    - {e.how_it_supports[:70]}...")
        print(f"\n  Counter Evidence ({len(cons.counter_evidence)}):")
        for e in cons.counter_evidence[:2]:
            print(f"    - {e.how_it_contradicts[:70]}...")
        print(f"\n  Hidden Motivations: {cons.hidden_motivations[:3]}")

    # Test 5: Run Network perspective
    print("\n--- Test 5: Network Perspective ---")
    runner = PerspectiveRunner(perspectives=[PerspectiveType.NETWORK])
    result = await runner.run_topic_analysis(context, parallel=True)

    if PerspectiveType.NETWORK in result.analyses:
        net = result.analyses[PerspectiveType.NETWORK]
        print(f"\n  Analysis (first 300 chars):")
        print(f"    {net.analysis[:300]}...")
        print(f"\n  Relationships ({len(net.relationships_revealed)}):")
        for r in net.relationships_revealed[:3]:
            print(f"    - {r.actor1} <-> {r.actor2}: {r.relationship_type}")
        print(f"\n  Intermediaries: {net.intermediaries}")
        print(f"\n  Network Patterns: {net.network_patterns[:2]}")

    # Test 6: Run all perspectives in parallel
    print("\n--- Test 6: All Perspectives (Parallel) ---")
    runner = PerspectiveRunner()  # All perspectives
    result = await runner.run_topic_analysis(context, parallel=True)

    print(f"\n  Perspectives analyzed: {len(result.analyses)}")
    for ptype, analysis in result.analyses.items():
        analysis_preview = analysis.analysis[:50] if analysis.analysis else "N/A"
        print(f"    [{ptype.value}] {analysis_preview}...")

    print("\n" + "=" * 70)
    print("All perspective tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_perspectives())
