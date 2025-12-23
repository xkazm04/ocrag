#!/usr/bin/env python
"""Test the relationship builder."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")


async def test_relationship_builder():
    """Test relationship building on Ukraine war findings."""
    print("=" * 70)
    print("RELATIONSHIP BUILDER TEST")
    print("=" * 70)

    from relationship_builder import RelationshipBuilder, FindingInfo

    # Create test findings
    findings = [
        FindingInfo(
            id="f1",
            content="The Maidan Revolution in February 2014 led to the overthrow of pro-Russian President Yanukovych",
            finding_type="event",
            date_text="February 2014",
            actors=["Viktor Yanukovych", "Ukrainian protesters"],
        ),
        FindingInfo(
            id="f2",
            content="Russia annexed Crimea in March 2014, citing protection of Russian-speaking population",
            finding_type="event",
            date_text="March 2014",
            actors=["Russia", "Vladimir Putin"],
        ),
        FindingInfo(
            id="f3",
            content="The Minsk I agreement was signed in September 2014 to end fighting in Donbas",
            finding_type="event",
            date_text="September 2014",
            actors=["Ukraine", "Russia", "OSCE"],
        ),
        FindingInfo(
            id="f4",
            content="The Minsk II agreement (February 2015) failed to stop the conflict",
            finding_type="event",
            date_text="February 2015",
            actors=["Ukraine", "Russia", "France", "Germany"],
        ),
        FindingInfo(
            id="f5",
            content="Russia claimed Minsk agreements were used by Ukraine to rearm",
            finding_type="claim",
            date_text="2022",
            actors=["Russia", "Vladimir Putin"],
        ),
        FindingInfo(
            id="f6",
            content="Angela Merkel stated the Minsk agreements gave Ukraine time to strengthen",
            finding_type="claim",
            date_text="December 2022",
            actors=["Angela Merkel"],
        ),
        FindingInfo(
            id="f7",
            content="Russia launched full-scale invasion on February 24, 2022",
            finding_type="event",
            date_text="February 24, 2022",
            actors=["Russia", "Ukraine"],
        ),
        FindingInfo(
            id="f8",
            content="NATO has consistently stated Ukraine was not close to membership",
            finding_type="claim",
            actors=["NATO"],
        ),
        FindingInfo(
            id="f9",
            content="Putin cited NATO expansion as the primary security threat",
            finding_type="claim",
            actors=["Vladimir Putin"],
        ),
        FindingInfo(
            id="f10",
            content="Ukraine has significant natural gas transit infrastructure worth billions",
            finding_type="fact",
            actors=["Ukraine", "Gazprom"],
        ),
    ]

    builder = RelationshipBuilder()
    topic = "Origins of the Russia-Ukraine war and factors leading to the 2022 invasion"

    print(f"\n  Analyzing {len(findings)} findings...")
    graph = await builder.build_graph(findings, topic)

    # Print relationships
    print(f"\n--- RELATIONSHIPS ({len(graph.relationships)}) ---")
    for r in graph.relationships[:8]:
        print(f"  [{r.source_finding_id}] --{r.relationship_type.value}--> [{r.target_finding_id}]")
        print(f"      {r.description[:70]}...")
        print(f"      Strength: {r.strength:.2f}")

    # Print contradictions
    print(f"\n--- CONTRADICTIONS ({len(graph.contradictions)}) ---")
    for c in graph.contradictions[:3]:
        print(f"  [{c.finding_id_1}] vs [{c.finding_id_2}]")
        print(f"    Claim 1: {c.claim_1[:60]}...")
        print(f"    Claim 2: {c.claim_2[:60]}...")
        print(f"    Significance: {c.significance[:80]}..." if c.significance else "    (no significance)")
        print(f"    Resolution Hint: {c.resolution_hint[:60]}..." if c.resolution_hint else "    (no hint)")

    # Print gaps
    print(f"\n--- RESEARCH GAPS ({len(graph.gaps)}) ---")
    for g in graph.gaps[:5]:
        print(f"  [{g.gap_type.value.upper()}] {g.description[:70]}...")
        print(f"    Priority: {g.priority}")
        if g.suggested_queries:
            print(f"    Suggested Query: {g.suggested_queries[0][:60]}...")

    # Print causal chains
    print(f"\n--- CAUSAL CHAINS ({len(graph.causal_chains)}) ---")
    for i, chain in enumerate(graph.causal_chains[:3], 1):
        print(f"\n  Chain {i}:")
        print(f"    Steps: {' -> '.join(chain.finding_ids)}")
        if chain.descriptions:
            for j, desc in enumerate(chain.descriptions[:3]):
                print(f"      {j+1}. {desc[:60]}...")

    print("\n" + "=" * 70)
    print("Relationship builder test completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_relationship_builder())
