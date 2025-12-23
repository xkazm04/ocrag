#!/usr/bin/env python
"""Test the OpenRouter inference client with Gemini 3 Flash Preview."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")


async def test_inference_client():
    """Test basic inference with the OpenRouter client."""
    print("=" * 60)
    print("INFERENCE CLIENT TEST - Gemini 3 Flash Preview")
    print("=" * 60)

    from inference_client import InferenceClient, check_availability

    # Check availability
    print("\n--- Checking Availability ---")
    avail = check_availability()
    print(f"  API Key Set: {avail['api_key_set']}")

    if not avail['api_key_set']:
        print("\nERROR: OPENROUTER_API_KEY not set")
        return

    # Initialize client
    client = InferenceClient()
    print(f"  Model: {client.model}")

    # Test 1: Simple text generation
    print("\n--- Test 1: Simple Generation ---")
    response = await client.generate(
        "What is 2 + 2? Reply with just the number.",
        temperature=0.0,
    )
    print(f"  Response: {response.text.strip()}")
    if response.token_usage:
        print(f"  Tokens: in={response.token_usage.input_tokens}, out={response.token_usage.output_tokens}")
    print(f"  Cost: ${response.cost_usd:.6f}" if response.cost_usd else "  Cost: N/A")

    # Test 2: JSON generation
    print("\n--- Test 2: JSON Generation ---")
    json_result, response = await client.generate_json(
        """Analyze this event and return JSON:
        Event: "Russia annexed Crimea in March 2014"

        Return: {"actors": [...], "date": "...", "significance": "..."}""",
        temperature=0.3,
    )
    print(f"  Parsed JSON: {json_result}")
    if response.token_usage:
        print(f"  Tokens: in={response.token_usage.input_tokens}, out={response.token_usage.output_tokens}")

    # Test 3: System prompt
    print("\n--- Test 3: With System Prompt ---")
    response = await client.generate(
        "What are the key motivations for the Russia-Ukraine conflict?",
        system_prompt="You are a geopolitical analyst. Be brief and factual.",
        temperature=0.3,
        max_tokens=200,
    )
    print(f"  Response preview: {response.text[:200]}...")
    if response.token_usage:
        print(f"  Tokens: in={response.token_usage.input_tokens}, out={response.token_usage.output_tokens}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_inference_client())
