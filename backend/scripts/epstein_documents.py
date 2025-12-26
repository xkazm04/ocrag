"""
Process Epstein case documents from TrumpEpsteinFiles.

Reads OCR-processed JSON files and extracts:
- Person-Location-Date events
- Person-Organization associations
- Key facts from document metadata

Inserts to Supabase with proper entity deduplication.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.research.db.client import get_supabase_client
from app.research.db.claims import ClaimOperations
from app.research.db.entities import EntityOperations
from app.research.db.relationships import ClaimEntityOperations, ClaimSourceOperations
from app.research.db.topics import TopicOperations
from app.research.schemas import KnowledgeClaimCreate, KnowledgeTopicCreate


# Configuration
DOCUMENTS_PATH = Path("C:/Users/kazim/dac/TrumpEpsteinFiles/PIPELINE/IMAGES")
PROGRESS_FILE = Path(__file__).parent / "processing_progress.json"
BATCH_SIZE = 50
MIN_CONFIDENCE = 0.6
MIN_TEXT_LENGTH = 100
WORKSPACE_ID = "epstein-investigation"

# Document types to skip
SKIP_DOC_TYPES = [
    "blank page", "separator", "cover page", "divider",
    "blank", "empty", "table of contents"
]

# Key entities to prioritize
KEY_PEOPLE = [
    "Jeffrey Epstein", "Ghislaine Maxwell", "Les Wexner",
    "Prince Andrew", "Alan Dershowitz", "Bill Clinton",
    "Donald Trump", "Steven Hoffenberg", "Jean-Luc Brunel"
]

KEY_LOCATIONS = [
    "Palm Beach", "Little Saint James", "Zorro Ranch",
    "Manhattan", "New York", "Virgin Islands", "Mar-a-Lago"
]

KEY_ORGS = [
    "Bear Stearns", "J. Epstein", "Towers Financial",
    "L Brands", "The Limited", "Victoria's Secret"
]


class DocumentProcessor:
    """Processes Epstein case documents and extracts findings."""

    def __init__(self):
        self.client = get_supabase_client()
        self.claims_db = ClaimOperations(self.client)
        self.entities_db = EntityOperations(self.client)
        self.claim_entities_db = ClaimEntityOperations(self.client)
        self.claim_sources_db = ClaimSourceOperations(self.client)
        self.topics_db = TopicOperations(self.client)

        self.progress = self._load_progress()
        self.topic_id: Optional[UUID] = None
        self.entity_cache: Dict[str, UUID] = {}  # name -> entity_id

        # Stats
        self.stats = {
            "processed": 0,
            "skipped": 0,
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
            "total_claims_created": 0,
            "total_entities_created": 0
        }

    def _save_progress(self):
        """Save processing progress to file."""
        with open(PROGRESS_FILE, "w") as f:
            json.dump(self.progress, f, indent=2, default=str)

    async def setup_topics(self) -> UUID:
        """Create topic hierarchy for Epstein investigation."""
        # Create or get parent topic
        parent = await self.topics_db.get_topic_by_slug("epstein-investigation")
        if not parent:
            parent = await self.topics_db.create_topic(KnowledgeTopicCreate(
                name="Jeffrey Epstein Investigation",
                slug="epstein-investigation",
                description="Knowledge base for Jeffrey Epstein case documents",
                topic_type="domain",  # Valid type: domain, event, entity, concept, region, timeperiod
                icon="search",
                color="#dc2626"
            ))
            print(f"Created parent topic: {parent.name}")

        # Create sub-topics
        subtopics = [
            ("business-activities", "Business Activities", "Financial dealings and business relationships"),
            ("personal-network", "Personal Network", "Social connections and associates"),
            ("properties-assets", "Properties & Assets", "Real estate and property holdings"),
            ("legal-proceedings", "Legal Proceedings", "Court cases and legal documents"),
            ("document-evidence", "Document Evidence", "Primary source documents"),
        ]

        for slug, name, desc in subtopics:
            existing = await self.topics_db.get_topic_by_slug(slug)
            if not existing:
                await self.topics_db.create_topic(KnowledgeTopicCreate(
                    name=name,
                    slug=slug,
                    description=desc,
                    topic_type="concept",  # Valid type
                    parent_id=parent.id
                ))
                print(f"  Created subtopic: {name}")

        self.topic_id = parent.id
        return parent.id

    def should_process(self, doc: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if document should be processed."""
        doc_id = doc.get("document_id", "")

        # Skip if already processed
        if doc_id in self.progress["processed_ids"]:
            return False, "already_processed"

        # Check confidence
        confidence = doc.get("confidence", {}).get("overall", 0)
        if confidence < MIN_CONFIDENCE:
            return False, "low_confidence"

        # Check text length
        full_text = doc.get("text_extraction", {}).get("full_text", "")
        if len(full_text) < MIN_TEXT_LENGTH:
            return False, "insufficient_text"

        # Check document type
        doc_type = doc.get("document_metadata", {}).get("document_type", "").lower()
        for skip_type in SKIP_DOC_TYPES:
            if skip_type in doc_type:
                return False, f"skip_type:{doc_type}"

        # Check for OCR errors
        if "error" in doc:
            return False, "ocr_error"

        return True, "ok"

    def calculate_priority(self, doc: Dict[str, Any]) -> int:
        """Calculate document priority based on key entities."""
        priority = 0

        people = doc.get("structured_data", {}).get("people", [])
        orgs = doc.get("structured_data", {}).get("organizations", [])
        locations = doc.get("structured_data", {}).get("locations", [])

        # Boost for key people
        for person in people:
            for key_person in KEY_PEOPLE:
                if key_person.lower() in person.lower():
                    priority += 10

        # Boost for key organizations
        for org in orgs:
            for key_org in KEY_ORGS:
                if key_org.lower() in org.lower():
                    priority += 5

        # Boost for key locations
        for loc in locations:
            for key_loc in KEY_LOCATIONS:
                if key_loc.lower() in loc.lower():
                    priority += 3

        return priority

    async def get_or_create_entity(
        self,
        name: str,
        entity_type: str
    ) -> Tuple[UUID, bool]:
        """Get or create entity with caching."""
        cache_key = f"{entity_type}:{name.lower()}"

        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key], False

        entity, created = await self.entities_db.get_or_create_entity(
            name=name,
            entity_type=entity_type
        )

        self.entity_cache[cache_key] = entity.id
        if created:
            self.stats["entities_created"] += 1

        return entity.id, created

    async def extract_and_create_claims(
        self,
        doc: Dict[str, Any]
    ) -> List[UUID]:
        """Extract findings from document and create claims."""
        created_claim_ids = []
        doc_id = doc.get("document_id", "unknown")
        structured = doc.get("structured_data", {})
        metadata = doc.get("document_metadata", {})

        people = structured.get("people", [])
        orgs = structured.get("organizations", [])
        locations = structured.get("locations", [])
        dates = structured.get("dates", [])
        confidence = doc.get("confidence", {}).get("overall", 0.5)

        # Claim 1: Person-Location-Date events
        if people and locations and dates:
            for person in people[:3]:  # Limit to first 3 people
                for location in locations[:2]:  # Limit to first 2 locations
                    for date_str in dates[:2]:  # Limit to first 2 dates
                        content = f"{person} documented at {location} ({date_str})"

                        claim = await self.claims_db.create_claim(
                            KnowledgeClaimCreate(
                                claim_type="event",
                                content=content,
                                summary=f"{person} presence at {location}",
                                topic_id=self.topic_id,
                                tags=["document-evidence", "location", date_str],
                                confidence_score=confidence * 0.9,
                                temporal_context="historical",  # Valid: historical, current, ongoing, predicted
                                extracted_data={
                                    "source_document": doc_id,
                                    "person": person,
                                    "location": location,
                                    "date": date_str
                                },
                                workspace_id=WORKSPACE_ID
                            )
                        )
                        created_claim_ids.append(claim.id)

                        # Link entities
                        person_id, _ = await self.get_or_create_entity(person, "person")
                        await self.claim_entities_db.link_claim_entity(
                            claim.id, person_id, role="subject"
                        )

                        location_id, _ = await self.get_or_create_entity(location, "location")
                        await self.claim_entities_db.link_claim_entity(
                            claim.id, location_id, role="location"
                        )

                        # Add document source
                        await self.claim_sources_db.add_source(
                            claim_id=claim.id,
                            source_type="document",
                            document_path=doc_id,
                            excerpt=doc.get("text_extraction", {}).get("full_text", "")[:500],
                            support_strength=confidence
                        )

        # Claim 2: Person-Organization associations
        if people and orgs:
            for person in people[:3]:
                for org in orgs[:3]:
                    content = f"{person} associated with {org}"

                    claim = await self.claims_db.create_claim(
                        KnowledgeClaimCreate(
                            claim_type="relationship",
                            content=content,
                            summary=f"{person} - {org} connection",
                            topic_id=self.topic_id,
                            tags=["document-evidence", "association"],
                            confidence_score=confidence * 0.8,
                            extracted_data={
                                "source_document": doc_id,
                                "person": person,
                                "organization": org
                            },
                            workspace_id=WORKSPACE_ID
                        )
                    )
                    created_claim_ids.append(claim.id)

                    # Link entities
                    person_id, _ = await self.get_or_create_entity(person, "person")
                    await self.claim_entities_db.link_claim_entity(
                        claim.id, person_id, role="subject"
                    )

                    org_id, _ = await self.get_or_create_entity(org, "organization")
                    await self.claim_entities_db.link_claim_entity(
                        claim.id, org_id, role="object"
                    )

                    await self.claim_sources_db.add_source(
                        claim_id=claim.id,
                        source_type="document",
                        document_path=doc_id,
                        excerpt=doc.get("text_extraction", {}).get("full_text", "")[:500],
                        support_strength=confidence
                    )

        # Claim 3: Document subject matter (if substantive)
        subject = metadata.get("subject", "")
        if subject and len(subject) > 20:
            claim = await self.claims_db.create_claim(
                KnowledgeClaimCreate(
                    claim_type="fact",
                    content=f"Document {doc_id}: {subject}",
                    summary=subject[:100],
                    topic_id=self.topic_id,
                    tags=["document-evidence", "metadata"],
                    confidence_score=confidence,
                    extracted_data={
                        "source_document": doc_id,
                        "document_type": metadata.get("document_type", "unknown"),
                        "subject": subject
                    },
                    workspace_id=WORKSPACE_ID
                )
            )
            created_claim_ids.append(claim.id)

            await self.claim_sources_db.add_source(
                claim_id=claim.id,
                source_type="document",
                document_path=doc_id,
                excerpt=doc.get("text_extraction", {}).get("full_text", "")[:500],
                support_strength=confidence
            )

        # Claim 4: Financial amounts
        financial = structured.get("financial_amounts", [])
        if financial:
            for amount in financial[:3]:
                content = f"Financial reference in {doc_id}: {amount}"

                claim = await self.claims_db.create_claim(
                    KnowledgeClaimCreate(
                        claim_type="evidence",
                        content=content,
                        summary=f"Financial: {amount}",
                        topic_id=self.topic_id,
                        tags=["document-evidence", "financial"],
                        confidence_score=confidence * 0.85,
                        extracted_data={
                            "source_document": doc_id,
                            "amount": amount
                        },
                        workspace_id=WORKSPACE_ID
                    )
                )
                created_claim_ids.append(claim.id)

                await self.claim_sources_db.add_source(
                    claim_id=claim.id,
                    source_type="document",
                    document_path=doc_id,
                    excerpt=doc.get("text_extraction", {}).get("full_text", "")[:500],
                    support_strength=confidence
                )

        return created_claim_ids

    async def process_document(self, doc_path: Path) -> bool:
        """Process a single document."""
        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                doc = json.load(f)

            doc_id = doc.get("document_id", doc_path.stem)

            # Check if should process
            should_process, reason = self.should_process(doc)
            if not should_process:
                self.stats["skipped"] += 1
                return False

            # Extract and create claims
            claim_ids = await self.extract_and_create_claims(doc)

            # Update progress
            self.progress["processed_ids"].append(doc_id)
            self.stats["processed"] += 1
            self.stats["claims_created"] += len(claim_ids)

            return True

        except Exception as e:
            doc_id = doc_path.stem
            self.progress["failed_ids"][doc_id] = {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            self.stats["errors"] += 1
            print(f"  Error processing {doc_id}: {e}")
            return False

    async def process_batch(self, batch_dir: Path) -> Dict[str, int]:
        """Process a batch of documents."""
        json_files = list(batch_dir.glob("*.json"))
        print(f"\nProcessing batch: {batch_dir.name} ({len(json_files)} files)")

        # Sort by priority (high priority first)
        doc_priorities = []
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    doc = json.load(f)
                priority = self.calculate_priority(doc)
                doc_priorities.append((priority, json_file))
            except:
                doc_priorities.append((0, json_file))

        doc_priorities.sort(key=lambda x: x[0], reverse=True)
        sorted_files = [f for _, f in doc_priorities]

        # Process in batches
        for i in range(0, len(sorted_files), BATCH_SIZE):
            batch = sorted_files[i:i + BATCH_SIZE]
            print(f"  Batch {i//BATCH_SIZE + 1}: Processing {len(batch)} files...")

            for doc_path in batch:
                await self.process_document(doc_path)

            # Save progress after each batch
            self._save_progress()

            print(f"    Processed: {self.stats['processed']}, "
                  f"Skipped: {self.stats['skipped']}, "
                  f"Claims: {self.stats['claims_created']}, "
                  f"Entities: {self.stats['entities_created']}, "
                  f"Errors: {self.stats['errors']}")

        return self.stats

    async def run(self):
        """Run the full document processing pipeline."""
        print("=" * 60)
        print("EPSTEIN DOCUMENT PROCESSOR")
        print("=" * 60)

        # Setup topics
        print("\n1. Setting up topic hierarchy...")
        await self.setup_topics()

        # Process batches
        print("\n2. Processing document batches...")

        batch_dirs = [
            DOCUMENTS_PATH / "001",
            DOCUMENTS_PATH / "004"
        ]

        for batch_dir in batch_dirs:
            if batch_dir.exists():
                await self.process_batch(batch_dir)

        # Final save
        self.progress["total_claims_created"] = self.stats["claims_created"]
        self.progress["total_entities_created"] = self.stats["entities_created"]
        self._save_progress()

        # Summary
        print("\n" + "=" * 60)
        print("PROCESSING COMPLETE")
        print("=" * 60)
        print(f"Documents processed: {self.stats['processed']}")
        print(f"Documents skipped: {self.stats['skipped']}")
        print(f"Claims created: {self.stats['claims_created']}")
        print(f"Entities created: {self.stats['entities_created']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"\nProgress saved to: {PROGRESS_FILE}")


async def main():
    processor = DocumentProcessor()
    await processor.run()


if __name__ == "__main__":
    asyncio.run(main())
