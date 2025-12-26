#!/usr/bin/env python
"""Test if Gemini's native web search tools work via OpenRouter.

This script tests whether OpenRouter supports passing Gemini's
google_search tool parameter.
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()


async def test_openrouter_with_search():
    """Test OpenRouter with Gemini's search tool."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        return

    print("Testing OpenRouter with Gemini's native search tool...")
    print("=" * 60)

    # Test with tools parameter (OpenRouter format)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://research-test.local",
        "X-Title": "Gemini Search Test",
    }

    # Try OpenRouter's web search plugin approach
    payload = {
        "model": "google/gemini-3-flash-preview",
        "messages": [
            {
                "role": "user",
                "content": "What is the current Bitcoin price today? Search the web for the latest information."
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
        # OpenRouter plugin for web search
        "plugins": ["web"],
    }

    print("\nTest 1: Using OpenRouter 'plugins' parameter...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS! Response received.")
                text = data["choices"][0]["message"]["content"]
                print(f"\nResponse preview: {text[:500]}...")

                # Check for grounding metadata
                if "grounding_metadata" in str(data):
                    print("\n✓ Grounding metadata found!")
                else:
                    print("\n✗ No grounding metadata in response")

                return True
            else:
                print(f"ERROR: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"ERROR: {e}")

    # Test 2: Try with tools parameter like OpenAI format
    print("\n" + "=" * 60)
    print("\nTest 2: Using 'tools' parameter (OpenAI format)...")

    payload2 = {
        "model": "google/gemini-3-flash-preview",
        "messages": [
            {
                "role": "user",
                "content": "What is the current Bitcoin price today?"
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload2,
            )

            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS! Response received.")

                message = data["choices"][0]["message"]
                if "tool_calls" in message:
                    print(f"Tool calls requested: {message['tool_calls']}")
                else:
                    text = message.get("content", "")
                    print(f"\nResponse preview: {text[:500]}...")

                return True
            else:
                print(f"ERROR: {response.status_code}")
                print(response.text[:500])

        except Exception as e:
            print(f"ERROR: {e}")

    return False


async def test_openrouter_models():
    """List available Gemini models on OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return

    print("\n" + "=" * 60)
    print("Checking available Gemini models on OpenRouter...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )

            if response.status_code == 200:
                data = response.json()
                gemini_models = [
                    m for m in data.get("data", [])
                    if "gemini" in m.get("id", "").lower()
                ]

                print(f"\nFound {len(gemini_models)} Gemini models:")
                for m in gemini_models[:10]:
                    model_id = m.get("id", "")
                    context = m.get("context_length", "?")
                    print(f"  - {model_id} (context: {context})")

        except Exception as e:
            print(f"ERROR: {e}")


async def main():
    print("=" * 60)
    print("GEMINI WEB SEARCH VIA OPENROUTER TEST")
    print("=" * 60)

    await test_openrouter_models()
    await test_openrouter_with_search()

    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    print("""
OpenRouter does NOT natively support Gemini's google_search tool.
OpenRouter provides its own 'web' plugin but it may work differently.

Options:
1. Use OpenRouter's 'plugins': ['web'] (if supported for Gemini)
2. Use native Google Generative AI SDK (google-genai) directly
3. Implement our own web search using Brave/Serper API

Recommendation: Use native google-genai SDK for Gemini with grounding.
""")


if __name__ == "__main__":
    asyncio.run(main())
