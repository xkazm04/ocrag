#!/usr/bin/env python
"""Test native Gemini client with web search grounding."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent  # rag/
load_dotenv(_project_root / ".env")


async def test_genai_grounding():
    """Test Gemini's native web search grounding."""
    print("=" * 60)
    print("TESTING NATIVE GEMINI WEB SEARCH GROUNDING")
    print("=" * 60)

    # Check if google-genai is available
    try:
        from .genai_client import (
            GeminiGroundedClient,
            check_genai_available,
            get_gemini_client,
        )
    except ImportError:
        from genai_client import (
            GeminiGroundedClient,
            check_genai_available,
            get_gemini_client,
        )

    if not check_genai_available():
        print("\nERROR: google-genai package not installed.")
        print("Install with: pip install google-genai")
        return False

    api_key = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("\nERROR: GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set.")
        print("Get an API key from: https://aistudio.google.com/apikey")
        return False

    print("\n[OK] google-genai package available")
    print("[OK] API key found")

    try:
        client = GeminiGroundedClient(api_key=api_key)
        print(f"[OK] Client initialized with model: {client.model}")
    except Exception as e:
        print(f"\nERROR initializing client: {e}")
        return False

    # Test 1: Simple grounded query
    print("\n" + "-" * 60)
    print("Test 1: Simple grounded query")
    print("-" * 60)
    print("\nQuery: What is the current Bitcoin price today?")

    try:
        response = await client.generate_with_search(
            prompt="What is the current Bitcoin price today? Give me the exact price.",
            temperature=0.3,
        )

        print(f"\n[OK] Response received ({response.tokens_used or '?'} tokens)")
        print(f"\nText preview:\n{response.text[:500]}...")

        if response.sources:
            print(f"\n[OK] Found {len(response.sources)} grounded sources:")
            for s in response.sources[:5]:
                print(f"  - {s.title} ({s.domain})")
                print(f"    URL: {s.url}")
        else:
            print("\n[NO] No grounded sources found")

        if response.search_queries:
            print(f"\n[OK] Search queries used: {response.search_queries}")
        else:
            print("\n[NO] No search queries in metadata")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Research synthesis query
    print("\n" + "-" * 60)
    print("Test 2: Research synthesis query")
    print("-" * 60)
    print("\nQuery: Recent developments in the Russia-Ukraine conflict")

    try:
        result = await client.search_and_synthesize(
            query="What are the latest developments in the Russia-Ukraine conflict this week?",
            max_sources=10,
        )

        print(f"\n[OK] Synthesis received ({result.get('tokens_used', '?')} tokens)")
        print(f"\nSynthesized content preview:\n{result['synthesized_content'][:500]}...")

        sources = result.get("sources", [])
        if sources:
            print(f"\n[OK] Found {len(sources)} sources:")
            for s in sources[:5]:
                print(f"  - {s.get('title', 'Untitled')} ({s.get('domain', '?')})")
        else:
            print("\n[NO] No sources returned")

        queries = result.get("search_queries", [])
        if queries:
            print(f"\n[OK] Search queries: {queries}")

        cost = result.get("cost_usd")
        if cost:
            print(f"\n[OK] Estimated cost: ${cost:.6f}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("SUCCESS: Native Gemini grounding is working!")
    print("=" * 60)

    return True


async def main():
    success = await test_genai_grounding()
    if not success:
        print("\n" + "=" * 60)
        print("SETUP INSTRUCTIONS")
        print("=" * 60)
        print("""
To use native Gemini with web search grounding:

1. Install the google-genai package:
   pip install google-genai

2. Get a Google API key:
   https://aistudio.google.com/apikey

3. Set the environment variable:
   GOOGLE_API_KEY=your_api_key_here

4. Run this test again to verify.
""")


if __name__ == "__main__":
    asyncio.run(main())
