"""
Import Batch 15 entities: Trump network and Mar-a-Lago connections.
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


BATCH15_ENTITIES = [
    {"canonical_name": "Donald Trump", "entity_type": "person", "aliases": [],
     "description": "45th US President. Long-time acquaintance of Epstein. Quoted in Vanity Fair saying of Epstein 'terrific guy...likes beautiful women as much as I do, many on the younger side.' 14 phone numbers in Epstein's directory. Mark Epstein testified Trump flew on Epstein's plane. Jane Doe 102 (Virginia Giuffre) was recruited by Maxwell at Trump's Mar-a-Lago. Trump reportedly banned Epstein from Mar-a-Lago after incident with underage girl. In deposition, Epstein took 5th when asked if he socialized with Trump in presence of females under 18."},

    {"canonical_name": "Mar-a-Lago", "entity_type": "organization", "aliases": ["Maralago", "Mar a Lago"],
     "description": "Trump's Palm Beach resort. Location where Ghislaine Maxwell approached and recruited Virginia Giuffre (then 15) to become Epstein's 'massage' girl. Site of 1997 Victoria's Secret party attended by Trump, Epstein, and models."},

    {"canonical_name": "Mark Epstein", "entity_type": "person", "aliases": [],
     "description": "Jeffrey Epstein's brother. Testified in deposition that Donald Trump flew on Jeffrey Epstein's plane. Epstein bought legal representation for him during civil cases."},

    {"canonical_name": "Nicholas Ribis", "entity_type": "person", "aliases": [],
     "description": "Epstein associate. Appears in May 2019 emails related to Trump inauguration news and Stephanie Winston Wolkoff. Corresponded with Epstein (jeevacation@gmail.com)."},

    {"canonical_name": "Trump Model Management", "entity_type": "organization", "aliases": ["Trump Models"],
     "description": "Donald Trump's modeling agency. Photo exists of Trump and Epstein at 1997 Victoria's Secret Angels party with newly signed Trump Model."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 15: TRUMP NETWORK AND MAR-A-LAGO CONNECTIONS")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH15_ENTITIES:
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
