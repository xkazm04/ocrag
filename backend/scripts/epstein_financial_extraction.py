"""
Epstein Files Financial Extraction Pipeline

Processes the TrumpEpsteinFiles repository to extract maximum financial tracing.
Uses Claude API for high-quality extraction, with deduplication against existing KB.

Key features:
- Document prioritization by financial relevance score
- Entity deduplication against existing knowledge base
- Structured extraction of transactions, properties, corporate structures
- Batch processing with progress tracking
"""

import os
import re
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('epstein_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Financial keywords for prioritization
FINANCIAL_KEYWORDS = {
    'high_priority': [
        'wire transfer', 'bank account', 'shell company', 'offshore',
        'payment', 'transaction', 'donation', 'trust fund', 'foundation',
        'million', 'billion', '$', 'usd', 'property', 'real estate',
        'purchase', 'sale', 'investment', 'ownership', 'llc', 'corporation',
        'wexner', 'bear stearns', 'limited', 'holdings', 'account number',
    ],
    'medium_priority': [
        'money', 'fund', 'asset', 'transfer', 'paid', 'salary', 'fee',
        'loan', 'debt', 'mortgage', 'settlement', 'compensation', 'stock',
        'shares', 'equity', 'hedge fund', 'financial', 'banking',
    ],
    'entity_indicators': [
        'inc', 'llc', 'ltd', 'corp', 'foundation', 'trust', 'holdings',
        'company', 'enterprises', 'partners', 'associates', 'group',
    ]
}

# Known financial entities in Epstein network (for context)
KNOWN_FINANCIAL_ENTITIES = [
    'J. Epstein & Co', 'Financial Trust Company', 'Butterfly Trust',
    'Gratitude America Ltd', 'C.O.U.Q. Foundation', 'J. Epstein VI Foundation',
    'Intercontinental Assets Group', 'Villard Venture', 'Plan D LLC',
    'Southern Country International', 'Nautilus', 'COUQ Foundation',
    'The Limited', 'L Brands', 'Wexner Foundation', 'New Albany Company',
]


@dataclass
class FinancialDocument:
    """A document with financial relevance scoring."""
    file_path: str
    file_name: str
    batch: str
    content: str
    financial_score: float = 0.0
    keywords_found: List[str] = field(default_factory=list)
    dollar_amounts: List[str] = field(default_factory=list)
    entities_mentioned: List[str] = field(default_factory=list)


@dataclass
class ExtractedTransaction:
    """A financial transaction extracted from documents."""
    source_entity: str
    target_entity: str
    amount: Optional[float] = None
    currency: str = "USD"
    transaction_type: str = "transfer"
    date: Optional[str] = None
    description: str = ""
    evidence_text: str = ""
    source_document: str = ""
    confidence: float = 0.5


@dataclass
class ExtractedEntity:
    """A financial entity extracted from documents."""
    name: str
    entity_type: str  # person, corporation, trust, foundation, etc.
    jurisdiction: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    connected_to: List[str] = field(default_factory=list)
    evidence_text: str = ""
    source_document: str = ""


class ExistingKnowledgeBase:
    """Interface to check existing entities in the knowledge base."""

    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.existing_entities: Dict[str, Dict] = {}
        self.entity_aliases: Dict[str, str] = {}  # alias -> canonical_name

    async def load_existing_entities(self) -> int:
        """Load all existing entities from KB to avoid duplicates."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            offset = 0
            limit = 100
            total_loaded = 0

            while True:
                try:
                    resp = await client.get(
                        f"{self.api_base}/api/research/knowledge/entities",
                        params={"limit": limit, "offset": offset, "workspace_id": "default"}
                    )
                    if resp.status_code != 200:
                        logger.warning(f"Failed to fetch entities: {resp.status_code}")
                        break

                    data = resp.json()
                    entities = data.get("entities", [])

                    if not entities:
                        break

                    for entity in entities:
                        canonical = entity.get("canonical_name", "").lower()
                        self.existing_entities[canonical] = entity

                        # Index aliases
                        for alias in entity.get("aliases", []):
                            self.entity_aliases[alias.lower()] = canonical

                    total_loaded += len(entities)
                    offset += limit

                    if len(entities) < limit:
                        break

                except Exception as e:
                    logger.error(f"Error loading entities: {e}")
                    break

            logger.info(f"Loaded {total_loaded} existing entities with {len(self.entity_aliases)} aliases")
            return total_loaded

    def is_duplicate(self, entity_name: str) -> Tuple[bool, Optional[str]]:
        """Check if entity already exists. Returns (is_duplicate, existing_canonical_name)."""
        name_lower = entity_name.lower().strip()

        # Direct match
        if name_lower in self.existing_entities:
            return True, self.existing_entities[name_lower].get("canonical_name")

        # Alias match
        if name_lower in self.entity_aliases:
            canonical = self.entity_aliases[name_lower]
            return True, self.existing_entities.get(canonical, {}).get("canonical_name")

        # Fuzzy match - check if name is substring of existing
        for existing in self.existing_entities:
            if name_lower in existing or existing in name_lower:
                if len(name_lower) > 5 and len(existing) > 5:  # Avoid short matches
                    return True, self.existing_entities[existing].get("canonical_name")

        return False, None


class FinancialExtractor:
    """Main extraction engine for financial data from Epstein files."""

    def __init__(
        self,
        docs_path: str,
        kb: ExistingKnowledgeBase,
        anthropic_api_key: Optional[str] = None,
    ):
        self.docs_path = Path(docs_path)
        self.kb = kb
        self.api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.processed_docs: List[FinancialDocument] = []
        self.extracted_transactions: List[ExtractedTransaction] = []
        self.extracted_entities: List[ExtractedEntity] = []
        self.new_entities: Set[str] = set()

    def scan_documents(self) -> List[FinancialDocument]:
        """Scan all documents and calculate financial relevance scores."""
        documents = []
        text_dirs = [
            self.docs_path / "PIPELINE" / "TEXT" / "001",
            self.docs_path / "PIPELINE" / "TEXT" / "002",
        ]

        for text_dir in text_dirs:
            if not text_dir.exists():
                logger.warning(f"Directory not found: {text_dir}")
                continue

            batch = text_dir.name

            for txt_file in text_dir.glob("*.txt"):
                if "_extraction" in txt_file.name:
                    continue  # Skip extraction JSON files

                try:
                    content = txt_file.read_text(encoding='utf-8', errors='ignore')
                    doc = self._score_document(txt_file, batch, content)
                    documents.append(doc)
                except Exception as e:
                    logger.error(f"Error reading {txt_file}: {e}")

        # Sort by financial score (highest first)
        documents.sort(key=lambda x: x.financial_score, reverse=True)

        logger.info(f"Scanned {len(documents)} documents")
        logger.info(f"High priority (score > 5): {len([d for d in documents if d.financial_score > 5])}")
        logger.info(f"Medium priority (score 2-5): {len([d for d in documents if 2 <= d.financial_score <= 5])}")

        return documents

    def _score_document(self, file_path: Path, batch: str, content: str) -> FinancialDocument:
        """Calculate financial relevance score for a document."""
        content_lower = content.lower()
        score = 0.0
        keywords_found = []

        # High priority keywords (3 points each)
        for keyword in FINANCIAL_KEYWORDS['high_priority']:
            count = content_lower.count(keyword)
            if count > 0:
                score += min(count * 3, 15)  # Cap at 15 per keyword
                keywords_found.append(f"{keyword}({count})")

        # Medium priority keywords (1 point each)
        for keyword in FINANCIAL_KEYWORDS['medium_priority']:
            count = content_lower.count(keyword)
            if count > 0:
                score += min(count * 1, 5)  # Cap at 5 per keyword
                keywords_found.append(f"{keyword}({count})")

        # Extract dollar amounts
        dollar_pattern = r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand|M|B|K))?'
        dollar_amounts = re.findall(dollar_pattern, content, re.IGNORECASE)
        score += len(dollar_amounts) * 5  # 5 points per dollar amount

        # Look for known financial entities
        entities_mentioned = []
        for entity in KNOWN_FINANCIAL_ENTITIES:
            if entity.lower() in content_lower:
                entities_mentioned.append(entity)
                score += 10  # 10 points for known entity

        # Bonus for entity indicators (suggests corporate structure info)
        for indicator in FINANCIAL_KEYWORDS['entity_indicators']:
            if indicator in content_lower:
                score += 2

        return FinancialDocument(
            file_path=str(file_path),
            file_name=file_path.name,
            batch=batch,
            content=content,
            financial_score=score,
            keywords_found=keywords_found[:20],  # Limit for readability
            dollar_amounts=dollar_amounts[:10],
            entities_mentioned=entities_mentioned,
        )

    async def extract_from_document(self, doc: FinancialDocument) -> Dict[str, Any]:
        """
        Use Claude to extract financial information from a high-priority document.
        """
        if not self.api_key:
            logger.warning("No Anthropic API key available, skipping Claude extraction")
            return {"error": "No API key"}

        prompt = f"""Analyze this document for financial information related to Jeffrey Epstein's network.

DOCUMENT: {doc.file_name}
CONTENT:
{doc.content[:8000]}

Extract and return JSON with:
1. transactions: List of financial transactions
   - source_entity: Who paid/transferred
   - target_entity: Who received
   - amount: Dollar amount if mentioned (number only)
   - currency: USD/EUR/etc
   - transaction_type: payment/transfer/donation/purchase/sale/loan/investment
   - date: Date if mentioned (YYYY-MM-DD format)
   - description: Brief description
   - evidence_quote: Exact quote from document supporting this

2. financial_entities: Companies, trusts, foundations, LLCs mentioned
   - name: Entity name
   - entity_type: corporation/llc/trust/foundation/hedge_fund/bank/property
   - jurisdiction: State/country if mentioned
   - connected_to: List of people/entities connected
   - role: What role in Epstein network (if known)

3. property_records: Real estate mentioned
   - address: Property address
   - owner: Who owns/owned it
   - value: Value if mentioned
   - transaction_date: When bought/sold
   - notes: Additional details

4. key_financial_claims: Important financial assertions
   - claim: The claim text
   - entities_involved: Who's involved
   - amount: If applicable
   - confidence: high/medium/low/alleged

Focus on:
- Payments between individuals
- Company ownership and structure
- Property purchases and transfers
- Trust arrangements
- Offshore entities
- Wexner-Epstein financial arrangements
- Foundation activities

Return ONLY valid JSON. If no financial info found, return empty arrays."""

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
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
                    logger.error(f"Claude API error: {resp.status_code} - {resp.text[:200]}")
                    return {"error": f"API error {resp.status_code}"}

                data = resp.json()
                content = data.get("content", [{}])[0].get("text", "{}")

                # Extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())

                return {"error": "No JSON in response"}

        except Exception as e:
            logger.error(f"Extraction error for {doc.file_name}: {e}")
            return {"error": str(e)}

    async def process_batch(
        self,
        documents: List[FinancialDocument],
        batch_size: int = 10,
        min_score: float = 5.0,
    ) -> Dict[str, Any]:
        """Process a batch of high-priority documents."""
        high_priority = [d for d in documents if d.financial_score >= min_score]
        logger.info(f"Processing {len(high_priority)} high-priority documents (score >= {min_score})")

        results = {
            "processed": 0,
            "transactions": [],
            "entities": [],
            "properties": [],
            "claims": [],
            "errors": [],
            "new_entities_found": [],
            "duplicate_entities_skipped": [],
        }

        for i in range(0, len(high_priority), batch_size):
            batch = high_priority[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(high_priority)-1)//batch_size + 1}")

            for doc in batch:
                logger.info(f"  Extracting: {doc.file_name} (score: {doc.financial_score:.1f})")

                extraction = await self.extract_from_document(doc)

                if "error" in extraction:
                    results["errors"].append({
                        "document": doc.file_name,
                        "error": extraction["error"]
                    })
                    continue

                results["processed"] += 1

                # Process transactions
                for txn in extraction.get("transactions", []):
                    txn["source_document"] = doc.file_name
                    results["transactions"].append(txn)

                # Process entities with deduplication
                for entity in extraction.get("financial_entities", []):
                    entity_name = entity.get("name", "")
                    is_dup, existing = self.kb.is_duplicate(entity_name)

                    if is_dup:
                        results["duplicate_entities_skipped"].append({
                            "found": entity_name,
                            "existing": existing
                        })
                    else:
                        entity["source_document"] = doc.file_name
                        results["entities"].append(entity)
                        results["new_entities_found"].append(entity_name)
                        self.new_entities.add(entity_name)

                # Properties
                for prop in extraction.get("property_records", []):
                    prop["source_document"] = doc.file_name
                    results["properties"].append(prop)

                # Claims
                for claim in extraction.get("key_financial_claims", []):
                    claim["source_document"] = doc.file_name
                    results["claims"].append(claim)

                # Rate limiting
                await asyncio.sleep(1)

        return results

    async def save_to_knowledge_base(self, results: Dict[str, Any]) -> Dict[str, int]:
        """Save extracted data to the knowledge base."""
        saved = {"entities": 0, "claims": 0, "transactions": 0}

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Save new entities
            for entity in results.get("entities", []):
                try:
                    resp = await client.post(
                        f"{self.kb.api_base}/api/research/knowledge/entities",
                        json={
                            "canonical_name": entity.get("name"),
                            "entity_type": self._map_entity_type(entity.get("entity_type")),
                            "aliases": [],
                            "workspace_id": "default",
                        }
                    )
                    if resp.status_code == 200:
                        saved["entities"] += 1
                except Exception as e:
                    logger.error(f"Failed to save entity {entity.get('name')}: {e}")

            # Save claims from financial assertions
            for claim in results.get("claims", []):
                try:
                    resp = await client.post(
                        f"{self.kb.api_base}/api/research/knowledge/claims",
                        json={
                            "content": claim.get("claim"),
                            "claim_type": "factual",
                            "source_type": "document",
                            "source_reference": claim.get("source_document"),
                            "workspace_id": "default",
                        }
                    )
                    if resp.status_code == 200:
                        saved["claims"] += 1
                except Exception as e:
                    logger.error(f"Failed to save claim: {e}")

        return saved

    def _map_entity_type(self, entity_type: str) -> str:
        """Map extraction entity types to KB entity types."""
        mapping = {
            "corporation": "organization",
            "llc": "organization",
            "trust": "organization",
            "foundation": "organization",
            "hedge_fund": "organization",
            "bank": "organization",
            "property": "location",
            "person": "person",
        }
        return mapping.get(entity_type.lower() if entity_type else "unknown", "organization")


async def main():
    """Main entry point for financial extraction pipeline."""
    # Configuration
    DOCS_PATH = r"C:\Users\kazim\dac\TrumpEpsteinFiles"
    MIN_SCORE = 5.0  # Minimum financial relevance score
    BATCH_SIZE = 5   # Documents per batch

    logger.info("=" * 60)
    logger.info("EPSTEIN FILES FINANCIAL EXTRACTION PIPELINE")
    logger.info("=" * 60)

    # Initialize knowledge base interface
    kb = ExistingKnowledgeBase()
    await kb.load_existing_entities()

    # Initialize extractor
    extractor = FinancialExtractor(DOCS_PATH, kb)

    # Scan and prioritize documents
    logger.info("\n--- PHASE 1: Document Scanning ---")
    documents = extractor.scan_documents()

    # Show top documents
    logger.info("\nTop 20 documents by financial relevance:")
    for i, doc in enumerate(documents[:20]):
        logger.info(f"  {i+1}. {doc.file_name} (score: {doc.financial_score:.1f})")
        if doc.dollar_amounts:
            logger.info(f"      Amounts: {', '.join(doc.dollar_amounts[:5])}")
        if doc.entities_mentioned:
            logger.info(f"      Entities: {', '.join(doc.entities_mentioned[:3])}")

    # Process high-priority documents
    logger.info("\n--- PHASE 2: Financial Extraction ---")
    results = await extractor.process_batch(documents, batch_size=BATCH_SIZE, min_score=MIN_SCORE)

    # Summary
    logger.info("\n--- EXTRACTION SUMMARY ---")
    logger.info(f"Documents processed: {results['processed']}")
    logger.info(f"Transactions found: {len(results['transactions'])}")
    logger.info(f"New entities found: {len(results['entities'])}")
    logger.info(f"Duplicate entities skipped: {len(results['duplicate_entities_skipped'])}")
    logger.info(f"Properties found: {len(results['properties'])}")
    logger.info(f"Key claims found: {len(results['claims'])}")
    logger.info(f"Errors: {len(results['errors'])}")

    # Save results to file
    output_file = Path("epstein_financial_extraction_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\nResults saved to: {output_file}")

    # Save to knowledge base
    logger.info("\n--- PHASE 3: Saving to Knowledge Base ---")
    saved = await extractor.save_to_knowledge_base(results)
    logger.info(f"Saved: {saved}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
