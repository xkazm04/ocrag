"""
Focused Epstein Financial Extraction Script
Processes top-priority documents combining Epstein mentions with financial content
"""

import os
import re
import json
import asyncio
from pathlib import Path
from datetime import datetime
import httpx

DOCS_PATH = Path("C:/Users/kazim/dac/TrumpEpsteinFiles/PIPELINE/TEXT")

# Get API key
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Financial + Epstein combined scoring
def score_for_epstein_financial(content: str) -> tuple:
    """Score document for BOTH Epstein relevance AND financial content."""
    content_lower = content.lower()

    # Must mention Epstein
    epstein_score = content_lower.count("epstein") * 5
    if epstein_score == 0:
        return 0, [], []

    financial_score = 0
    keywords_found = []

    # Financial keywords
    fin_keywords = [
        ("wexner", 20), ("million", 5), ("billion", 10),
        ("transfer", 3), ("payment", 3), ("donation", 5),
        ("foundation", 5), ("trust", 3), ("property", 3),
        ("purchase", 3), ("mansion", 5), ("wire", 5),
        ("account", 3), ("offshore", 10), ("cayman", 10),
        ("llc", 5), ("corporation", 3), ("settlement", 5),
        ("compensation", 3), ("mortgage", 3), ("loan", 3),
    ]

    for kw, weight in fin_keywords:
        count = content_lower.count(kw)
        if count > 0:
            financial_score += min(count * weight, weight * 5)
            keywords_found.append(f"{kw}({count})")

    # Dollar amounts
    dollars = re.findall(r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|M|B))?', content, re.IGNORECASE)
    financial_score += len(dollars) * 10

    total_score = epstein_score + financial_score
    return total_score, keywords_found, dollars[:5]


def scan_documents():
    """Scan and score all documents."""
    results = []

    for batch in ["001", "002"]:
        batch_dir = DOCS_PATH / batch
        if not batch_dir.exists():
            continue

        for txt_file in batch_dir.glob("*.txt"):
            if "_extraction" in txt_file.name:
                continue
            try:
                content = txt_file.read_text(encoding='utf-8', errors='ignore')
                score, keywords, dollars = score_for_epstein_financial(content)

                if score > 0:
                    results.append({
                        "file": txt_file.name,
                        "batch": batch,
                        "path": str(txt_file),
                        "score": score,
                        "keywords": keywords[:10],
                        "dollars": dollars,
                        "content_preview": content[:500],
                    })
            except Exception as e:
                print(f"Error reading {txt_file}: {e}")

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


async def extract_financial_data(file_path: str, content: str) -> dict:
    """Use Claude to extract financial information."""
    if not ANTHROPIC_API_KEY:
        return {"error": "No API key"}

    prompt = f"""Analyze this document for FINANCIAL information related to Jeffrey Epstein's network.

FILE: {Path(file_path).name}

CONTENT (first 10000 chars):
{content[:10000]}

Extract ONLY financial information. Return JSON:
{{
    "transactions": [
        {{
            "source": "who paid/transferred",
            "target": "who received",
            "amount": "dollar amount or null",
            "type": "payment/transfer/donation/purchase/salary/settlement/loan",
            "date": "date if known",
            "description": "brief description",
            "evidence": "exact quote from document"
        }}
    ],
    "entities": [
        {{
            "name": "company/trust/foundation name",
            "type": "corporation/llc/trust/foundation/bank/property",
            "jurisdiction": "state/country if known",
            "connection": "how connected to Epstein network"
        }}
    ],
    "properties": [
        {{
            "address": "property address",
            "owner": "owner name",
            "value": "value if mentioned",
            "transaction_type": "purchase/sale/transfer/gift",
            "date": "date if known"
        }}
    ],
    "key_amounts": [
        {{
            "amount": "$X",
            "context": "what this amount refers to",
            "entities_involved": ["names"]
        }}
    ]
}}

Focus on concrete financial facts. If no financial info, return empty arrays."""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )

            if resp.status_code != 200:
                return {"error": f"API error: {resp.status_code}"}

            data = resp.json()
            text = data.get("content", [{}])[0].get("text", "{}")

            # Extract JSON
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group())
            return {"error": "No JSON found"}

    except Exception as e:
        return {"error": str(e)}


async def main():
    print("=" * 60)
    print("EPSTEIN FINANCIAL EXTRACTION")
    print("=" * 60)

    # Scan documents
    print("\nScanning documents...")
    docs = scan_documents()

    print(f"Total documents with Epstein + financial content: {len(docs)}")
    print(f"High priority (score > 50): {len([d for d in docs if d['score'] > 50])}")

    # Show top 20
    print("\nTOP 20 DOCUMENTS:")
    for i, doc in enumerate(docs[:20]):
        print(f"{i+1:2}. [{doc['batch']}] {doc['file']} (score: {doc['score']})")
        if doc['dollars']:
            print(f"     Amounts: {', '.join(doc['dollars'][:3])}")
        if doc['keywords']:
            print(f"     Keywords: {', '.join(doc['keywords'][:5])}")

    # Process top 10 documents with Claude
    if ANTHROPIC_API_KEY:
        print("\n" + "=" * 60)
        print("EXTRACTING FINANCIAL DATA FROM TOP DOCUMENTS")
        print("=" * 60)

        all_results = {
            "processed_at": datetime.now().isoformat(),
            "documents_processed": 0,
            "transactions": [],
            "entities": [],
            "properties": [],
            "key_amounts": [],
        }

        for doc in docs[:10]:
            print(f"\nProcessing: {doc['file']}...")

            # Read full content
            content = Path(doc['path']).read_text(encoding='utf-8', errors='ignore')

            result = await extract_financial_data(doc['path'], content)

            if "error" in result:
                print(f"  Error: {result['error']}")
                continue

            all_results["documents_processed"] += 1

            # Collect results
            for txn in result.get("transactions", []):
                txn["source_document"] = doc['file']
                all_results["transactions"].append(txn)

            for ent in result.get("entities", []):
                ent["source_document"] = doc['file']
                all_results["entities"].append(ent)

            for prop in result.get("properties", []):
                prop["source_document"] = doc['file']
                all_results["properties"].append(prop)

            for amt in result.get("key_amounts", []):
                amt["source_document"] = doc['file']
                all_results["key_amounts"].append(amt)

            print(f"  Found: {len(result.get('transactions', []))} transactions, "
                  f"{len(result.get('entities', []))} entities, "
                  f"{len(result.get('properties', []))} properties")

            await asyncio.sleep(1)  # Rate limiting

        # Save results
        output_file = Path("epstein_financial_results.json")
        with open(output_file, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nResults saved to: {output_file}")

        # Summary
        print("\n" + "=" * 60)
        print("EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"Documents processed: {all_results['documents_processed']}")
        print(f"Total transactions: {len(all_results['transactions'])}")
        print(f"Total entities: {len(all_results['entities'])}")
        print(f"Total properties: {len(all_results['properties'])}")
        print(f"Key amounts found: {len(all_results['key_amounts'])}")

        if all_results['transactions']:
            print("\nSAMPLE TRANSACTIONS:")
            for txn in all_results['transactions'][:5]:
                print(f"  - {txn.get('source', '?')} -> {txn.get('target', '?')}: "
                      f"{txn.get('amount', 'N/A')} ({txn.get('type', '?')})")

        if all_results['entities']:
            print("\nSAMPLE ENTITIES:")
            for ent in all_results['entities'][:5]:
                print(f"  - {ent.get('name', '?')} ({ent.get('type', '?')}) - {ent.get('jurisdiction', 'N/A')}")

    else:
        print("\nNo ANTHROPIC_API_KEY found. Set it to enable Claude extraction.")
        print("For now, showing document analysis only.")


if __name__ == "__main__":
    asyncio.run(main())
