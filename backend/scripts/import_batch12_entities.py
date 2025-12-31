"""
Import Batch 12 entities: Media and journalists.
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


BATCH12_ENTITIES = [
    {"canonical_name": "Julie Brown", "entity_type": "person", "aliases": [],
     "description": "Miami Herald investigative reporter. 'Perversion of Justice' series (November 2018) exposed details of Acosta plea deal. Led to Epstein's July 2019 re-arrest and Acosta's resignation as Labor Secretary."},

    {"canonical_name": "Emily Steel", "entity_type": "person", "aliases": [],
     "description": "New York Times reporter. Covered Epstein story and connections to elite figures."},

    {"canonical_name": "James Patterson", "entity_type": "person", "aliases": [],
     "description": "Author, 'Filthy Rich' book about Epstein (2016). Book was actually ghostwritten by John Connolly (Vanity Fair)."},

    {"canonical_name": "Kate Kelly", "entity_type": "person", "aliases": [],
     "description": "Wall Street Journal reporter. Epstein called her 'a snake' in January 2010 email to Jes Staley advising on PR strategy at Davos."},

    {"canonical_name": "Ronan Farrow", "entity_type": "person", "aliases": [],
     "description": "New Yorker journalist. Investigated Epstein connections. March 2019 Larry Summers-Epstein email was about 'Call from New Yorker'."},

    {"canonical_name": "Nicholas Confessore", "entity_type": "person", "aliases": [],
     "description": "New York Times reporter. Co-authored 'Unease at Clinton Foundation' article referenced in Epstein emails."},

    {"canonical_name": "Miami Herald", "entity_type": "organization", "aliases": [],
     "description": "Newspaper that published Julie Brown's 'Perversion of Justice' investigation November 2018, leading to Epstein's re-arrest."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 12: MEDIA AND JOURNALISTS")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH12_ENTITIES:
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
