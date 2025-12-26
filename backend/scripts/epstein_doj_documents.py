"""
Process Epstein DOJ documents from epstein-docs.github.io.

Uses pre-analyzed document data with:
- Document-level analyses (summaries, significance, key people with roles)
- Page-level OCR results

Implements deduplication against existing claims.
"""

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from uuid import UUID

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.research.db.client import get_supabase_client
from app.research.db.claims import ClaimOperations
from app.research.db.entities import EntityOperations
from app.research.db.relationships import ClaimEntityOperations, ClaimSourceOperations
from app.research.db.topics import TopicOperations
from app.research.schemas import KnowledgeClaimCreate


# Configuration
DOCUMENTS_PATH = Path("C:/Users/kazim/dac/epstein-docs.github.io")
ANALYSES_FILE = DOCUMENTS_PATH / "analyses.json"
RESULTS_DIR = DOCUMENTS_PATH / "results"
PROGRESS_FILE = Path(__file__).parent / "doj_processing_progress.json"
BATCH_SIZE = 100
WORKSPACE_ID = "epstein-investigation"

# Document types to prioritize
HIGH_VALUE_TYPES = [
    "pilot's flight log", "flight log",
    "deposition", "transcript",
    "email", "email chain",
    "court filing", "court order", "court transcript",
    "financial record", "bank record",
    "medical record"
]

# Skip these low-value types
SKIP_TYPES = [
    "blank page", "separator", "cover sheet", "index",
    "table of contents", "redacted page"
]


class DOJDocumentProcessor:
    """Processes DOJ Epstein documents with deduplication."""

    def __init__(self):
        self.client = get_supabase_client()
        self.claims_db = ClaimOperations(self.client)
        self.entities_db = EntityOperations(self.client)
        self.claim_entities_db = ClaimEntityOperations(self.client)
        self.claim_sources_db = ClaimSourceOperations(self.client)
        self.topics_db = TopicOperations(self.client)

        self.progress = self._load_progress()
        self.topic_id: Optional[UUID] = None
        self.entity_cache: Dict[str, UUID] = {}
        self.existing_hashes: Set[str] = set()

        # Stats
        self.stats = {
            "processed": 0,
            "skipped": 0,
            "duplicates": 0,
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

    def _hash_content(self, content: str) -> str:
        """Generate hash for content deduplication."""
        return hashlib.md5(content.lower().strip().encode()).hexdigest()

    async def load_existing_hashes(self):
        """Load existing claim content hashes for deduplication."""
        print("Loading existing claim hashes for deduplication...")

        # Get all existing claims in workspace
        result = self.client.table("knowledge_claims").select(
            "content_hash"
        ).eq("workspace_id", WORKSPACE_ID).execute()

        self.existing_hashes = {row["content_hash"] for row in result.data}
        print(f"  Loaded {len(self.existing_hashes)} existing hashes")

    async def get_topic(self) -> UUID:
        """Get or create the investigation topic."""
        topic = await self.topics_db.get_topic_by_slug("epstein-investigation")
        if topic:
            self.topic_id = topic.id
            return topic.id
        raise Exception("Topic 'epstein-investigation' not found. Run epstein_documents.py first.")

    def should_process(self, doc: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if document should be processed."""
        doc_id = doc.get("document_id", "")

        # Skip if already processed
        if doc_id in self.progress["processed_ids"]:
            return False, "already_processed"

        # Check document type
        analysis = doc.get("analysis", {})
        doc_type = analysis.get("document_type", "").lower()

        for skip_type in SKIP_TYPES:
            if skip_type in doc_type:
                return False, f"skip_type:{doc_type}"

        # Must have some content
        summary = analysis.get("summary", "")
        if len(summary) < 20:
            return False, "no_summary"

        return True, "ok"

    def is_duplicate(self, content: str) -> bool:
        """Check if content already exists."""
        content_hash = self._hash_content(content)
        return content_hash in self.existing_hashes

    async def get_or_create_entity(
        self,
        name: str,
        entity_type: str,
        role: Optional[str] = None
    ) -> Tuple[UUID, bool]:
        """Get or create entity with caching."""
        # Clean name
        name = name.strip()
        if not name or len(name) < 2:
            return None, False

        cache_key = f"{entity_type}:{name.lower()}"

        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key], False

        try:
            entity, created = await self.entities_db.get_or_create_entity(
                name=name,
                entity_type=entity_type,
                description=role
            )

            self.entity_cache[cache_key] = entity.id
            if created:
                self.stats["entities_created"] += 1

            return entity.id, created
        except Exception as e:
            print(f"    Error creating entity {name}: {e}")
            return None, False

    async def process_document(self, doc: Dict[str, Any]) -> List[UUID]:
        """Process a single document analysis."""
        created_claim_ids = []
        doc_id = doc.get("document_id", "unknown")
        analysis = doc.get("analysis", {})

        doc_type = analysis.get("document_type", "unknown")
        summary = analysis.get("summary", "")
        significance = analysis.get("significance", "")
        key_topics = analysis.get("key_topics", [])
        key_people = analysis.get("key_people", [])

        # Claim 1: Document summary
        if summary and len(summary) > 20:
            content = f"[{doc_type}] {summary}"

            if not self.is_duplicate(content):
                try:
                    claim = await self.claims_db.create_claim(
                        KnowledgeClaimCreate(
                            claim_type="fact",
                            content=content,
                            summary=summary[:200],
                            topic_id=self.topic_id,
                            tags=["doj-document", doc_type.lower().replace(" ", "-")],
                            confidence_score=0.85,
                            temporal_context="historical",
                            extracted_data={
                                "source_document": doc_id,
                                "document_type": doc_type,
                                "key_topics": key_topics
                            },
                            workspace_id=WORKSPACE_ID
                        )
                    )
                    created_claim_ids.append(claim.id)
                    self.existing_hashes.add(self._hash_content(content))

                    # Link people as entities
                    # Valid roles: subject, object, actor, target, location, mentioned, source, beneficiary
                    for person in key_people:
                        name = person.get("name", "") if isinstance(person, dict) else str(person)
                        role_desc = person.get("role", "") if isinstance(person, dict) else None

                        entity_id, _ = await self.get_or_create_entity(name, "person", role_desc)
                        if entity_id:
                            await self.claim_entities_db.link_claim_entity(
                                claim.id, entity_id, role="mentioned", context=role_desc
                            )

                    # Add document source
                    await self.claim_sources_db.add_source(
                        claim_id=claim.id,
                        source_type="document",
                        document_path=doc_id,
                        excerpt=summary[:500],
                        support_strength=0.85
                    )
                except Exception as e:
                    print(f"    Error creating summary claim: {e}")
            else:
                self.stats["duplicates"] += 1

        # Claim 2: Significance (if different from summary)
        if significance and len(significance) > 30 and significance != summary:
            content = f"Significance: {significance}"

            if not self.is_duplicate(content):
                try:
                    claim = await self.claims_db.create_claim(
                        KnowledgeClaimCreate(
                            claim_type="evidence",
                            content=content,
                            summary=f"Significance of {doc_id}",
                            topic_id=self.topic_id,
                            tags=["doj-document", "significance"],
                            confidence_score=0.8,
                            temporal_context="historical",
                            extracted_data={
                                "source_document": doc_id,
                                "document_type": doc_type
                            },
                            workspace_id=WORKSPACE_ID
                        )
                    )
                    created_claim_ids.append(claim.id)
                    self.existing_hashes.add(self._hash_content(content))

                    await self.claim_sources_db.add_source(
                        claim_id=claim.id,
                        source_type="document",
                        document_path=doc_id,
                        excerpt=significance[:500],
                        support_strength=0.8
                    )
                except Exception as e:
                    print(f"    Error creating significance claim: {e}")
            else:
                self.stats["duplicates"] += 1

        # Claim 3: Person-role relationships
        for person in key_people:
            if isinstance(person, dict):
                name = person.get("name", "")
                role = person.get("role", "")

                if name and role and len(role) > 3:
                    content = f"{name} - {role} (from {doc_type})"

                    if not self.is_duplicate(content):
                        try:
                            claim = await self.claims_db.create_claim(
                                KnowledgeClaimCreate(
                                    claim_type="relationship",
                                    content=content,
                                    summary=f"{name}: {role}",
                                    topic_id=self.topic_id,
                                    tags=["doj-document", "person-role"],
                                    confidence_score=0.9,
                                    temporal_context="historical",
                                    extracted_data={
                                        "source_document": doc_id,
                                        "person": name,
                                        "role": role
                                    },
                                    workspace_id=WORKSPACE_ID
                                )
                            )
                            created_claim_ids.append(claim.id)
                            self.existing_hashes.add(self._hash_content(content))

                            entity_id, _ = await self.get_or_create_entity(name, "person", role)
                            if entity_id:
                                await self.claim_entities_db.link_claim_entity(
                                    claim.id, entity_id, role="subject", context=role
                                )

                            await self.claim_sources_db.add_source(
                                claim_id=claim.id,
                                source_type="document",
                                document_path=doc_id,
                                excerpt=f"{name} identified as {role}",
                                support_strength=0.9
                            )
                        except Exception as e:
                            print(f"    Error creating relationship claim: {e}")
                    else:
                        self.stats["duplicates"] += 1

        return created_claim_ids

    async def run(self):
        """Run the full document processing pipeline."""
        print("=" * 60)
        print("DOJ EPSTEIN DOCUMENT PROCESSOR")
        print("=" * 60)

        # Load analyses
        print(f"\n1. Loading analyses from {ANALYSES_FILE}...")
        with open(ANALYSES_FILE, "r") as f:
            data = json.load(f)
        analyses = data.get("analyses", [])
        print(f"   Loaded {len(analyses)} document analyses")

        # Get topic
        print("\n2. Getting investigation topic...")
        await self.get_topic()
        print(f"   Topic ID: {self.topic_id}")

        # Load existing hashes for deduplication
        print("\n3. Loading existing claims for deduplication...")
        await self.load_existing_hashes()

        # Process in batches
        print(f"\n4. Processing documents (batch size: {BATCH_SIZE})...")

        # Sort by document type priority
        def get_priority(doc):
            doc_type = doc.get("analysis", {}).get("document_type", "").lower()
            for i, ht in enumerate(HIGH_VALUE_TYPES):
                if ht in doc_type:
                    return i
            return len(HIGH_VALUE_TYPES)

        analyses.sort(key=get_priority)

        for i in range(0, len(analyses), BATCH_SIZE):
            batch = analyses[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(analyses) + BATCH_SIZE - 1) // BATCH_SIZE

            print(f"\n  Batch {batch_num}/{total_batches}: Processing {len(batch)} documents...")

            for doc in batch:
                doc_id = doc.get("document_id", "unknown")

                should_process, reason = self.should_process(doc)
                if not should_process:
                    self.stats["skipped"] += 1
                    continue

                try:
                    claim_ids = await self.process_document(doc)

                    self.progress["processed_ids"].append(doc_id)
                    self.stats["processed"] += 1
                    self.stats["claims_created"] += len(claim_ids)

                except Exception as e:
                    self.progress["failed_ids"][doc_id] = {
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    self.stats["errors"] += 1
                    print(f"    Error processing {doc_id}: {e}")

            # Save progress after each batch
            self._save_progress()

            print(f"    Processed: {self.stats['processed']}, "
                  f"Skipped: {self.stats['skipped']}, "
                  f"Duplicates: {self.stats['duplicates']}, "
                  f"Claims: {self.stats['claims_created']}, "
                  f"Entities: {self.stats['entities_created']}, "
                  f"Errors: {self.stats['errors']}")

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
        print(f"Duplicates avoided: {self.stats['duplicates']}")
        print(f"Claims created: {self.stats['claims_created']}")
        print(f"Entities created: {self.stats['entities_created']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"\nProgress saved to: {PROGRESS_FILE}")


async def main():
    processor = DOJDocumentProcessor()
    await processor.run()


if __name__ == "__main__":
    asyncio.run(main())
