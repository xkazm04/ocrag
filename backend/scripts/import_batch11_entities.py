"""
Import Batch 11 entities: Properties and shell companies.
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


BATCH11_ENTITIES = [
    {"canonical_name": "Little St. James Island", "entity_type": "organization", "aliases": ["Little St James", "LSJ", "Pedophile Island"],
     "description": "Epstein's 70-acre private island in US Virgin Islands, purchased 1998 for $7.95 million. Held through L.S.J. LLC. Features included main house, guest houses, mysterious temple structure, private dock. Site of alleged trafficking activities."},

    {"canonical_name": "Great St. James Island", "entity_type": "organization", "aliases": ["Great St James"],
     "description": "Epstein's second US Virgin Islands island, purchased 2016 for $18 million. Adjacent to Little St. James. Development was planned before Epstein's arrest."},

    {"canonical_name": "Zorro Ranch", "entity_type": "organization", "aliases": ["Zorro Trust Ranch"],
     "description": "Epstein's 10,000-acre ranch in Stanley, New Mexico. Held through Zorro Trust. Features airstrip, main house, guest houses. Site of alleged abuse and Epstein's eugenics/DNA plans."},

    {"canonical_name": "Southern Trust Company", "entity_type": "organization", "aliases": [],
     "description": "US Virgin Islands entity used by Epstein for financial operations and to take advantage of USVI tax benefits."},

    {"canonical_name": "L.S.J. LLC", "entity_type": "organization", "aliases": ["LSJ LLC"],
     "description": "Delaware LLC that holds Little St. James Island for Jeffrey Epstein."},

    {"canonical_name": "JEGE LLC", "entity_type": "organization", "aliases": [],
     "description": "Epstein shell company. Name derived from 'JE' (Jeffrey Epstein) and 'GE' (Ghislaine). Used for various holdings."},

    {"canonical_name": "Plan D LLC", "entity_type": "organization", "aliases": [],
     "description": "Epstein entity that held aircraft including the Boeing 727 'Lolita Express'."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 11: PROPERTIES AND SHELL COMPANIES")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH11_ENTITIES:
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
