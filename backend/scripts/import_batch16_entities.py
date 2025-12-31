"""
Import Batch 16 entities: International connections (royalty, foreign nationals).
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


BATCH16_ENTITIES = [
    {"canonical_name": "Prince Andrew", "entity_type": "person", "aliases": ["Duke of York", "Andrew Windsor", "HRH Prince Andrew"],
     "description": "British royal, Duke of York. Virginia Giuffre alleged she was trafficked to have sex with him at age 17 in London, New York, and Virgin Islands. Famous photo exists of Andrew with arm around Giuffre at Maxwell's London townhouse. Initially denied knowing Giuffre. Settled civil lawsuit with Giuffre February 2022. Friend of Ghislaine Maxwell. Epstein took 5th when asked about socializing with 'Prince Andrew of Great Britain' in presence of females under 18."},

    {"canonical_name": "Gordon Getty", "entity_type": "person", "aliases": [],
     "description": "Billionaire heir to Getty oil fortune. Documents show draft writings found in Epstein files. Member of wealthy Epstein social circle."},

    {"canonical_name": "Naomi Campbell", "entity_type": "person", "aliases": [],
     "description": "Supermodel. Appeared on Epstein's flight logs. Friend of Ghislaine Maxwell."},

    {"canonical_name": "Kevin Spacey", "entity_type": "person", "aliases": [],
     "description": "Actor. Flew with Bill Clinton and Chris Tucker on Epstein's plane to Africa. Referenced in Vanity Fair article about Epstein's celebrity connections."},

    {"canonical_name": "Chris Tucker", "entity_type": "person", "aliases": [],
     "description": "Actor/comedian. Flew with Bill Clinton and Kevin Spacey on Epstein's Boeing 727 to Africa. Trip reported in national media as evidence of Clinton-Epstein friendship."},

    {"canonical_name": "Boies Schiller Flexner LLP", "entity_type": "organization", "aliases": ["Boies Schiller"],
     "description": "Law firm representing Virginia Giuffre in her lawsuit against Alan Dershowitz and others. Filed April 2019 complaint."},

    {"canonical_name": "David Boies", "entity_type": "person", "aliases": [],
     "description": "Prominent attorney. Partner at Boies Schiller Flexner. Represented Virginia Giuffre in her civil lawsuits. Former attorney for Harvey Weinstein."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 16: INTERNATIONAL CONNECTIONS")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH16_ENTITIES:
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


if __name__ == "__main__":
    asyncio.run(main())
