"""
Import Batch 10 entities: Legal team and Acosta deal.
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


BATCH10_ENTITIES = [
    {"canonical_name": "Alex Acosta", "entity_type": "person", "aliases": ["R. Alexander Acosta"],
     "description": "US Attorney Southern District of Florida who approved Epstein Non Prosecution Agreement September 2008. Trump Labor Secretary 2017-2019. Resigned July 2019 after Miami Herald investigation exposed NPA details. Previously worked at Kirkland & Ellis."},

    {"canonical_name": "Marie Villafaña", "entity_type": "person", "aliases": ["Ann Marie Villafaña"],
     "description": "Federal prosecutor on Epstein case. Emails show she expressed frustration with plea deal. Wrote that Epstein defense team was 'out-lawyering' the government."},

    {"canonical_name": "Kenneth Marra", "entity_type": "person", "aliases": [],
     "description": "Federal judge Southern District of Florida. February 2019 ruled government violated Crime Victims Rights Act by keeping NPA secret from victims."},

    {"canonical_name": "Roy Black", "entity_type": "person", "aliases": [],
     "description": "Prominent Miami defense attorney. Part of Epstein 'dream team' legal defense alongside Dershowitz, Starr, Lefcourt."},

    {"canonical_name": "Gerald Lefcourt", "entity_type": "person", "aliases": ["Gerald B. Lefcourt"],
     "description": "New York defense attorney. Part of Epstein legal team. Signed letter to prosecutors calling Epstein 'a committed philanthropist'."},

    {"canonical_name": "Julie Brown", "type": "person", "aliases": [],
     "description": "Miami Herald investigative reporter. 'Perversion of Justice' series (2018) exposed details of Acosta deal, led to Epstein's 2019 re-arrest and Acosta's resignation."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 10: LEGAL TEAM AND ACOSTA DEAL")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH10_ENTITIES:
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
                entity_type=entity_data.get("entity_type", "person"),
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
