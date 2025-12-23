#!/usr/bin/env python
"""Test the query decomposer."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")


async def test_decomposer():
    """Test query decomposition."""
    print("=" * 60)
    print("QUERY DECOMPOSER TEST")
    print("=" * 60)

    from decomposer import QueryDecomposer, BatchExecutor

    decomposer = QueryDecomposer()

    # Test 1: Simple query (no decomposition needed)
    print("\n--- Test 1: Simple Query ---")
    simple_query = "What happened in the 2022 Russia-Ukraine invasion?"

    result = await decomposer.analyze_and_decompose(simple_query)
    print(f"  Query: {simple_query}")
    print(f"  Needs decomposition: {result.needs_decomposition}")
    print(f"  Strategy: {result.strategy.value}")
    print(f"  Reasoning: {result.decomposition_reasoning[:100]}...")

    # Test 2: Long time range query
    print("\n--- Test 2: Long Time Range Query ---")
    long_range_query = "How did the relationship between Russia and Ukraine evolve from 1991 to 2024?"

    result = await decomposer.analyze_and_decompose(long_range_query)
    print(f"  Query: {long_range_query}")
    print(f"  Needs decomposition: {result.needs_decomposition}")
    print(f"  Strategy: {result.strategy.value}")
    print(f"  Date range: {result.detected_date_range}")
    print(f"  Year span: {result.date_range_years} years")
    print(f"  Themes: {result.detected_themes}")
    print(f"  Actors: {result.detected_actors}")
    print(f"  Reasoning: {result.decomposition_reasoning}")

    if result.sub_queries:
        print(f"\n  Sub-queries ({len(result.sub_queries)}):")
        for sq in result.sub_queries:
            print(f"    [{sq.batch_order}] {sq.query[:80]}...")
            print(f"        Role: {sq.composition_role}, Focus: {sq.focus_theme}")

    # Test 3: Multi-thematic query
    print("\n--- Test 3: Multi-Thematic Query ---")
    thematic_query = "What are the political, economic, and military dimensions of the Russia-Ukraine conflict?"

    result = await decomposer.analyze_and_decompose(thematic_query)
    print(f"  Query: {thematic_query}")
    print(f"  Needs decomposition: {result.needs_decomposition}")
    print(f"  Strategy: {result.strategy.value}")
    print(f"  Themes: {result.detected_themes}")
    print(f"  Reasoning: {result.decomposition_reasoning}")

    if result.sub_queries:
        print(f"\n  Sub-queries ({len(result.sub_queries)}):")
        for sq in result.sub_queries:
            print(f"    [{sq.batch_order}] {sq.query[:80]}...")
            print(f"        Theme: {sq.focus_theme}")

    # Test 4: Batch execution order
    if result.sub_queries:
        print("\n--- Test 4: Batch Execution Order ---")
        executor = BatchExecutor()
        batches = executor.get_execution_order(result.sub_queries)
        print(f"  Execution batches: {len(batches)}")
        for i, batch in enumerate(batches, 1):
            print(f"    Batch {i}: {[sq.id for sq in batch]}")

    print("\n" + "=" * 60)
    print("All decomposer tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_decomposer())
