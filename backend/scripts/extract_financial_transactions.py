"""
Extract financial transactions from Epstein document analyses.

Scans for documents with financial content (bank statements, financial records)
and extracts structured transaction data using:
1. Regex pattern matching for dollar amounts
2. LLM-based extraction for structured transaction details
"""

import asyncio
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from uuid import UUID

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from google import genai
from supabase import create_client

# Get settings from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Use anon key, same as other scripts

# Configuration
DOCUMENTS_PATH = Path("C:/Users/kazim/dac/epstein-docs.github.io")
ANALYSES_FILE = DOCUMENTS_PATH / "analyses.json"
RESULTS_DIR = DOCUMENTS_PATH / "results"
PROGRESS_FILE = Path(__file__).parent / "financial_extraction_progress.json"
BATCH_SIZE = 20
WORKSPACE_ID = "epstein-investigation"

# Financial document types to prioritize
FINANCIAL_DOC_TYPES = [
    "bank statement", "bank record", "financial statement",
    "wire transfer", "check", "receipt", "invoice",
    "tax return", "accounting", "ledger", "transaction",
    "property deed", "real estate", "mortgage",
    "settlement", "payment record"
]

# Regex patterns for financial amounts
DOLLAR_PATTERNS = [
    r'\$[\d,]+(?:\.\d{2})?',  # $1,234.56 or $1234
    r'\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\s*(?:dollars?|USD)\b',  # 1,234.56 dollars
    r'\b(?:USD|US\$)\s*[\d,]+(?:\.\d{2})?\b',  # USD 1,234.56
]

# Financial keywords
FINANCIAL_KEYWORDS = [
    'wire transfer', 'payment', 'deposit', 'withdrawal',
    'check', 'cash', 'credit', 'debit', 'balance',
    'transaction', 'transfer', 'settlement', 'invoice',
    'purchase', 'sale', 'loan', 'mortgage', 'gift',
    'bank', 'account', 'funds', 'million', 'thousand'
]


class FinancialTransactionExtractor:
    """Extracts financial transactions from document analyses."""

    def __init__(self):
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.genai_client = genai.Client()
        self.progress = self._load_progress()
        self.topic_id: Optional[str] = None
        self.entity_cache: Dict[str, str] = {}
        self.existing_hashes: Set[str] = set()

        # Stats
        self.stats = {
            "documents_scanned": 0,
            "financial_docs_found": 0,
            "transactions_extracted": 0,
            "claims_created": 0,
            "entities_created": 0,
            "errors": 0
        }

    def _load_progress(self) -> Dict[str, Any]:
        """Load processing progress from file."""
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f)
        return {
            "processed_ids": [],
            "failed_ids": {},
            "total_transactions": 0
        }

    def _save_progress(self):
        """Save processing progress to file."""
        with open(PROGRESS_FILE, "w") as f:
            json.dump(self.progress, f, indent=2, default=str)

    def _hash_content(self, content: str) -> str:
        """Generate hash for content deduplication."""
        return hashlib.md5(content.lower().strip().encode()).hexdigest()

    def load_existing_hashes(self):
        """Load existing claim content hashes for deduplication."""
        print("Loading existing claim hashes for deduplication...")
        result = self.client.table("knowledge_claims").select(
            "content_hash"
        ).eq("workspace_id", WORKSPACE_ID).execute()
        self.existing_hashes = {row["content_hash"] for row in result.data}
        print(f"  Loaded {len(self.existing_hashes)} existing hashes")

    def get_topic(self) -> str:
        """Get the investigation topic."""
        result = self.client.table("knowledge_topics").select(
            "id"
        ).eq("slug", "epstein-investigation").execute()

        if result.data:
            self.topic_id = result.data[0]["id"]
            return self.topic_id
        raise Exception("Topic 'epstein-investigation' not found")

    def is_financial_document(self, analysis: Dict[str, Any]) -> bool:
        """Check if document contains financial content."""
        doc_type = analysis.get("document_type", "").lower()
        summary = analysis.get("summary", "").lower()
        topics = [t.lower() for t in analysis.get("key_topics", [])]

        # Check document type
        for ft in FINANCIAL_DOC_TYPES:
            if ft in doc_type:
                return True

        # Check summary for financial keywords
        text = summary + " " + " ".join(topics)
        keyword_count = sum(1 for kw in FINANCIAL_KEYWORDS if kw in text)

        # Check for dollar amounts in summary
        has_amounts = any(re.search(p, summary) for p in DOLLAR_PATTERNS)

        return keyword_count >= 2 or has_amounts

    def get_page_text(self, doc_id: str) -> Optional[str]:
        """Get full OCR text for a document from page results."""
        for subdir in RESULTS_DIR.iterdir():
            if subdir.is_dir():
                doc_file = subdir / f"{doc_id}.json"
                if doc_file.exists():
                    try:
                        with open(doc_file, "r") as f:
                            data = json.load(f)
                        return data.get("full_text", "")
                    except Exception:
                        pass
        return None

    def extract_transactions_llm(
        self,
        doc_id: str,
        doc_type: str,
        summary: str,
        full_text: str = ""
    ) -> List[Dict[str, Any]]:
        """Use LLM to extract structured financial transactions."""
        # Rate limit: wait between requests (10 requests/min = 6 seconds between)
        time.sleep(7)

        # Limit text size
        text_preview = full_text[:8000] if full_text else summary

        prompt = f"""
You are a financial forensic analyst extracting transaction data from documents.

Document ID: {doc_id}
Document Type: {doc_type}

Document Content:
{text_preview}

Extract ALL financial transactions mentioned. For each transaction, provide:
1. amount: The dollar amount as a NUMBER (e.g., 10000.00, not "$10,000")
2. currency: "USD" unless otherwise specified
3. payer: Who paid/transferred the money (person or organization)
4. payee: Who received the money (person or organization)
5. transaction_date: Date in YYYY-MM-DD format if known, otherwise null
6. transaction_type: One of: payment, wire_transfer, check, deposit, withdrawal, gift, loan, property_purchase, property_sale, settlement, investment, salary, fee
7. institution: Bank or financial institution if mentioned
8. purpose: Brief description of what the transaction was for
9. confidence: 0.0-1.0 based on how clear the information is

IMPORTANT:
- amount MUST be a number, not a string (e.g., 10000.00 not "10,000")
- Extract EVERY transaction with a dollar amount
- If payer/payee is unclear, use "Unknown" but still extract
- Include property transfers as transactions
- Include gifts and loans

Return as JSON array. If no transactions found, return empty array [].
"""

        try:
            response = self.genai_client.models.generate_content(
                model="gemini-3-flash-preview",  # Use stable model
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1
                }
            )

            result = json.loads(response.text)
            if isinstance(result, list):
                return result
            return []

        except Exception as e:
            print(f"    LLM extraction error: {e}")
            return []

    def get_or_create_entity(self, name: str, entity_type: str = "person") -> Optional[str]:
        """Get or create entity with caching."""
        name = name.strip()
        if not name or len(name) < 2 or name.lower() == "unknown":
            return None

        cache_key = f"{entity_type}:{name.lower()}"
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]

        try:
            # Check if exists
            name_hash = hashlib.md5(name.lower().encode()).hexdigest()
            result = self.client.table("knowledge_entities").select(
                "id"
            ).eq("name_hash", name_hash).execute()

            if result.data:
                entity_id = result.data[0]["id"]
                self.entity_cache[cache_key] = entity_id
                return entity_id

            # Create new
            result = self.client.table("knowledge_entities").insert({
                "canonical_name": name,
                "entity_type": entity_type,
                "name_hash": name_hash,
                "aliases": []
            }).execute()

            if result.data:
                entity_id = result.data[0]["id"]
                self.entity_cache[cache_key] = entity_id
                self.stats["entities_created"] += 1
                return entity_id

        except Exception as e:
            print(f"    Error creating entity {name}: {e}")
        return None

    def create_transaction_claim(
        self,
        transaction: Dict[str, Any],
        doc_id: str,
        doc_type: str
    ) -> Optional[str]:
        """Create a claim for a financial transaction."""
        raw_amount = transaction.get("amount", 0)
        # Handle string amounts
        if isinstance(raw_amount, str):
            # Remove $ and commas
            raw_amount = re.sub(r'[$,]', '', raw_amount)
            try:
                amount = float(raw_amount)
            except (ValueError, TypeError):
                amount = 0.0
        else:
            amount = float(raw_amount) if raw_amount else 0.0

        if amount <= 0:
            return None  # Skip invalid amounts

        payer = transaction.get("payer", "Unknown")
        payee = transaction.get("payee", "Unknown")
        trans_type = transaction.get("transaction_type", "payment")
        purpose = transaction.get("purpose", "")
        trans_date = transaction.get("transaction_date")

        # Build content
        content = f"${amount:,.2f} {trans_type}"
        if payer and payer != "Unknown":
            content += f" from {payer}"
        if payee and payee != "Unknown":
            content += f" to {payee}"
        if purpose:
            content += f" for {purpose}"
        if trans_date:
            content += f" on {trans_date}"

        # Check for duplicate
        content_hash = self._hash_content(content)
        if content_hash in self.existing_hashes:
            return None

        try:
            # Create claim
            claim_data = {
                "claim_type": "financial",
                "content": content,
                "summary": f"${amount:,.2f} {trans_type}",
                "content_hash": content_hash,
                "topic_id": self.topic_id,
                "tags": ["financial-transaction", trans_type, "doj-document"],
                "confidence_score": transaction.get("confidence", 0.7),
                "temporal_context": "historical",
                "event_date": trans_date,
                "extracted_data": {
                    "amount": amount,
                    "currency": transaction.get("currency", "USD"),
                    "payer": payer,
                    "payee": payee,
                    "transaction_type": trans_type,
                    "institution": transaction.get("institution"),
                    "purpose": purpose,
                    "source_document": doc_id,
                    "document_type": doc_type
                },
                "workspace_id": WORKSPACE_ID
            }

            result = self.client.table("knowledge_claims").insert(claim_data).execute()

            if not result.data:
                return None

            claim_id = result.data[0]["id"]
            self.existing_hashes.add(content_hash)

            # Link payer entity
            if payer and payer != "Unknown":
                entity_id = self.get_or_create_entity(payer)
                if entity_id:
                    self.client.table("claim_entities").upsert({
                        "claim_id": claim_id,
                        "entity_id": entity_id,
                        "role": "actor",
                        "context_snippet": "payer"
                    }, on_conflict="claim_id,entity_id,role").execute()

            # Link payee entity
            if payee and payee != "Unknown":
                entity_id = self.get_or_create_entity(payee)
                if entity_id:
                    self.client.table("claim_entities").upsert({
                        "claim_id": claim_id,
                        "entity_id": entity_id,
                        "role": "beneficiary",
                        "context_snippet": "payee"
                    }, on_conflict="claim_id,entity_id,role").execute()

            # Link institution entity
            institution = transaction.get("institution")
            if institution:
                entity_id = self.get_or_create_entity(institution, "organization")
                if entity_id:
                    self.client.table("claim_entities").upsert({
                        "claim_id": claim_id,
                        "entity_id": entity_id,
                        "role": "mentioned",
                        "context_snippet": "financial institution"
                    }, on_conflict="claim_id,entity_id,role").execute()

            # Add document source
            self.client.table("claim_sources").insert({
                "claim_id": claim_id,
                "source_type": "document",
                "document_path": doc_id,
                "excerpt": content[:500],
                "support_strength": transaction.get("confidence", 0.7)
            }).execute()

            return claim_id

        except Exception as e:
            print(f"    Error creating transaction claim: {e}")
            return None

    def process_document(self, doc: Dict[str, Any]) -> int:
        """Process a single document for financial transactions."""
        doc_id = doc.get("document_id", "unknown")
        analysis = doc.get("analysis", {})
        doc_type = analysis.get("document_type", "unknown")
        summary = analysis.get("summary", "")

        # Get full text if available
        full_text = self.get_page_text(doc_id) or ""

        # Extract transactions using LLM
        transactions = self.extract_transactions_llm(
            doc_id, doc_type, summary, full_text
        )

        claims_created = 0
        for trans in transactions:
            claim_id = self.create_transaction_claim(trans, doc_id, doc_type)
            if claim_id:
                claims_created += 1
                self.stats["transactions_extracted"] += 1

        return claims_created

    def run(self):
        """Run the financial extraction pipeline."""
        print("=" * 60)
        print("FINANCIAL TRANSACTION EXTRACTOR")
        print("=" * 60)

        # Load analyses
        print(f"\n1. Loading analyses from {ANALYSES_FILE}...")
        with open(ANALYSES_FILE, "r") as f:
            data = json.load(f)
        analyses = data.get("analyses", [])
        print(f"   Loaded {len(analyses)} document analyses")

        # Get topic
        print("\n2. Getting investigation topic...")
        self.get_topic()
        print(f"   Topic ID: {self.topic_id}")

        # Load existing hashes
        print("\n3. Loading existing claims for deduplication...")
        self.load_existing_hashes()

        # Filter for financial documents
        print("\n4. Identifying financial documents...")
        financial_docs = []
        for doc in analyses:
            analysis = doc.get("analysis", {})
            doc_id = doc.get("document_id", "")

            # Skip already processed
            if doc_id in self.progress["processed_ids"]:
                continue

            if self.is_financial_document(analysis):
                financial_docs.append(doc)

        print(f"   Found {len(financial_docs)} financial documents to process")
        self.stats["financial_docs_found"] = len(financial_docs)

        # Process in batches
        print(f"\n5. Processing documents (batch size: {BATCH_SIZE})...")

        for i in range(0, len(financial_docs), BATCH_SIZE):
            batch = financial_docs[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(financial_docs) + BATCH_SIZE - 1) // BATCH_SIZE

            print(f"\n  Batch {batch_num}/{total_batches}: Processing {len(batch)} documents...")

            for doc in batch:
                doc_id = doc.get("document_id", "unknown")
                self.stats["documents_scanned"] += 1

                try:
                    claims_created = self.process_document(doc)
                    self.stats["claims_created"] += claims_created
                    self.progress["processed_ids"].append(doc_id)

                    if claims_created > 0:
                        print(f"    {doc_id}: {claims_created} transactions")

                except Exception as e:
                    self.progress["failed_ids"][doc_id] = {
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    self.stats["errors"] += 1
                    print(f"    Error processing {doc_id}: {e}")

            # Save progress after each batch
            self._save_progress()

            print(f"    Batch complete: {self.stats['transactions_extracted']} transactions, "
                  f"{self.stats['claims_created']} claims")

        # Final summary
        self.progress["total_transactions"] = self.stats["transactions_extracted"]
        self._save_progress()

        print("\n" + "=" * 60)
        print("EXTRACTION COMPLETE")
        print("=" * 60)
        print(f"Documents scanned: {self.stats['documents_scanned']}")
        print(f"Financial docs found: {self.stats['financial_docs_found']}")
        print(f"Transactions extracted: {self.stats['transactions_extracted']}")
        print(f"Claims created: {self.stats['claims_created']}")
        print(f"Entities created: {self.stats['entities_created']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"\nProgress saved to: {PROGRESS_FILE}")


def main():
    extractor = FinancialTransactionExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
