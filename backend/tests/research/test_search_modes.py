#!/usr/bin/env python
"""Test Gemini client with Search and Grounded modes."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")


def format_token_usage(response) -> str:
    """Format token usage for display."""
    if response.token_usage:
        tu = response.token_usage
        return f"in={tu.input_tokens}, out={tu.output_tokens}, total={tu.total_tokens}"
    return "?"


async def test_search_modes():
    """Test search and grounded modes."""
    print("=" * 70)
    print("GEMINI CLIENT - SEARCH MODES TEST")
    print("=" * 70)

    from gemini_client import (
        GeminiResearchClient,
        SearchMode,
        check_availability,
    )

    # Check availability
    print("\n--- Availability ---")
    avail = check_availability()
    for key, value in avail.items():
        status = "[OK]" if value else "[NO]"
        print(f"  {status} {key}: {value}")

    if not avail["api_key_set"]:
        print("\nERROR: API key not set.")
        return

    client = GeminiResearchClient(search_mode=SearchMode.GROUNDED)

    # Test 1: Grounded Search with full metadata
    print("\n" + "=" * 70)
    print("TEST 1: GROUNDED SEARCH")
    print("=" * 70)
    print("\nQuery: Who won Euro 2024?")

    response = await client.grounded_search("Who won Euro 2024?")

    print(f"\n[OK] Tokens: {format_token_usage(response)}")
    print(f"[OK] Mode: {response.search_mode.value}")
    print(f"\nAnswer:\n{response.text}")

    if response.search_queries:
        print(f"\n[OK] Search queries used: {response.search_queries}")

    if response.sources:
        print(f"\n[OK] Sources ({len(response.sources)}):")
        for s in response.sources:
            print(f"  - {s.title} ({s.domain})")

    # Show grounding supports (text-to-source attribution)
    segments = response.get_grounded_segments()
    if segments:
        print(f"\n[OK] Grounded Segments ({len(segments)}):")
        for seg in segments[:5]:
            text_preview = seg['text'][:60] + "..." if len(seg['text']) > 60 else seg['text']
            sources = [s['title'] for s in seg['sources']]
            print(f"  \"{text_preview}\"")
            print(f"    -> Sources: {sources}")

    # Test 2: Simple Search (no full grounding metadata)
    print("\n" + "=" * 70)
    print("TEST 2: SIMPLE SEARCH")
    print("=" * 70)
    print("\nQuery: What is the capital of France?")

    response2 = await client.search("What is the capital of France?")

    print(f"\n[OK] Tokens: {format_token_usage(response2)}")
    print(f"[OK] Mode: {response2.search_mode.value}")
    print(f"\nAnswer:\n{response2.text}")

    if response2.sources:
        print(f"\n[OK] Sources: {[s.title for s in response2.sources]}")

    # Test 3: No Search (LLM only)
    print("\n" + "=" * 70)
    print("TEST 3: NO SEARCH (LLM ONLY)")
    print("=" * 70)
    print("\nQuery: What is the capital of France?")

    response3 = await client.generate("What is the capital of France?")

    print(f"\n[OK] Tokens: {format_token_usage(response3)}")
    print(f"[OK] Mode: {response3.search_mode.value}")
    print(f"\nAnswer:\n{response3.text}")

    # Test 4: Research with custom system prompt
    print("\n" + "=" * 70)
    print("TEST 4: RESEARCH WITH SYSTEM PROMPT")
    print("=" * 70)
    print("\nQuery: Latest news on AI regulation")

    response4 = await client.research(
        "What are the latest developments in AI regulation?",
        system_prompt="You are a policy analyst. Provide a brief, factual summary.",
        mode=SearchMode.GROUNDED
    )

    print(f"\n[OK] Tokens: {format_token_usage(response4)}")
    print(f"\nAnswer preview:\n{response4.text[:500]}...")

    if response4.grounding_metadata:
        print(f"\n[OK] Grounding Metadata:")
        print(f"  - Queries: {response4.grounding_metadata.web_search_queries}")
        print(f"  - Chunks: {len(response4.grounding_metadata.grounding_chunks)}")
        print(f"  - Supports: {len(response4.grounding_metadata.grounding_supports)}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
Search Modes (all use Google Search):

  NONE:     LLM only, no web search
  SEARCH:   Google Search + answer + sources
  GROUNDED: Google Search + answer + sources + grounding supports
            (shows which text is supported by which source)

Key Methods:
  - client.generate()        -> No search
  - client.search()          -> Quick search
  - client.grounded_search() -> Full grounding metadata
  - client.research()        -> Configurable mode
""")


async def main():
    await test_search_modes()


if __name__ == "__main__":
    asyncio.run(main())
