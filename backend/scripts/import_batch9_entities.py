"""
Import Batch 9 entities: Scientists and academics network.
Major discovery: Lawrence Krauss, Marvin Minsky, Edge Foundation connections.
"""

import asyncio
import os
import sys
sys.path.insert(0, ".")

from supabase import create_client, Client
from app.research.db import SupabaseResearchDB
from app.research.schemas import KnowledgeEntityCreate


def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(url, key)


BATCH9_ENTITIES = [
    # === Scientists ===
    {"canonical_name": "Lawrence Krauss", "entity_type": "person", "aliases": ["Lawrence M. Krauss"],
     "description": "Arizona State University physicist, Origins Project founder. 27 documents in Epstein archive. Close Epstein associate who organized conferences, traveled to island, and defended Epstein after 2008 conviction. Resigned from ASU 2018 over sexual misconduct allegations."},

    {"canonical_name": "Marvin Minsky", "entity_type": "person", "aliases": [],
     "description": "MIT AI Lab co-founder, AI pioneer. Named in victim allegations - Virginia Giuffre stated she was directed to have sex with him. 42 documents in archive. Member of Edge Foundation network. Died January 2016."},

    {"canonical_name": "Danny Hillis", "entity_type": "person", "aliases": ["W. Daniel Hillis"],
     "description": "Computer scientist, Thinking Machines founder, Applied Minds co-founder. Key Edge Foundation member connecting tech world to Epstein. 13 documents in archive."},

    {"canonical_name": "George Church", "entity_type": "person", "aliases": [],
     "description": "Harvard geneticist, pioneer in genome sequencing. 33 documents in archive. Received Epstein funding for research. Met with Epstein multiple times including after 2008 conviction."},

    {"canonical_name": "Frank Wilczek", "entity_type": "person", "aliases": [],
     "description": "MIT physicist, Nobel Prize 2004 for work on strong force. Participated in Epstein-funded Origins Project events organized by Lawrence Krauss."},

    {"canonical_name": "Stuart Russell", "entity_type": "person", "aliases": [],
     "description": "UC Berkeley AI researcher, author of leading AI textbook. Participated in Lawrence Krauss Origins Project AI workshop February 2017."},

    {"canonical_name": "Stephen Hawking", "entity_type": "person", "aliases": [],
     "description": "Cambridge physicist, cosmologist. Attended conferences at Epstein's island. Mentioned in BBC Today Programme guest list. Died March 2018."},

    # === Organizations ===
    {"canonical_name": "Origins Project", "entity_type": "organization", "aliases": ["ASU Origins Project"],
     "description": "Arizona State University science initiative founded by Lawrence Krauss. Received Epstein funding. Organized high-profile AI workshop February 2017."},

    {"canonical_name": "Edge Foundation", "entity_type": "organization", "aliases": ["Edge.org"],
     "description": "Organization founded by John Brockman connecting scientists, tech billionaires. Key gateway for Epstein's scientific network. Organized 'billionaires dinners' at Epstein properties."},

    {"canonical_name": "Thinking Machines", "entity_type": "organization", "aliases": ["Thinking Machines Corporation"],
     "description": "Supercomputer company founded by Danny Hillis 1983. Early AI/parallel computing pioneer. Connected to Epstein network through Hillis."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 9: SCIENTISTS AND ACADEMICS NETWORK")
    print("Major Discovery: Lawrence Krauss, Marvin Minsky, Edge Foundation")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH9_ENTITIES:
        existing = await db.find_entity_by_name(entity_data["canonical_name"])

        if existing:
            if len(entity_data.get("description", "")) > len(existing.description or ""):
                try:
                    db.client.table("knowledge_entities").update({
                        "description": entity_data["description"]
                    }).eq("id", str(existing.id)).execute()
                    print(f"UPDATED: {entity_data['canonical_name']}")
                    updated += 1
                except Exception as e:
                    print(f"  Error updating: {e}")
            else:
                print(f"SKIP (exists): {entity_data['canonical_name']}")
            skipped += 1
            continue

        exists_as_alias = False
        for alias in entity_data.get("aliases", []):
            existing = await db.find_entity_by_name(alias)
            if existing:
                print(f"SKIP (alias exists): {entity_data['canonical_name']} -> {alias}")
                exists_as_alias = True
                skipped += 1
                break

        if exists_as_alias:
            continue

        try:
            entity = KnowledgeEntityCreate(
                canonical_name=entity_data["canonical_name"],
                entity_type=entity_data["entity_type"],
                aliases=entity_data.get("aliases", []),
                description=entity_data.get("description"),
            )
            result = await db.create_entity(entity)
            print(f"CREATED: {result.canonical_name} (ID: {result.id})")
            created += 1
        except Exception as e:
            print(f"ERROR: {entity_data['canonical_name']}: {e}")

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)
    print(f"Entities Created: {created}")
    print(f"Entities Updated: {updated}")
    print(f"Entities Skipped: {skipped}")
    print(f"Total processed: {len(BATCH9_ENTITIES)}")


if __name__ == "__main__":
    asyncio.run(main())
