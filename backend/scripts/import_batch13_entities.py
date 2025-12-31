"""
Import Batch 13 entities: Government officials and law enforcement.
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


BATCH13_ENTITIES = [
    {"canonical_name": "Michael Reiter", "entity_type": "person", "aliases": ["Chief Reiter"],
     "description": "Palm Beach Police Chief who led the 2005-2006 investigation into Jeffrey Epstein. Built comprehensive case documenting systematic abuse. Frustrated when federal prosecutors accepted lenient plea deal."},

    {"canonical_name": "Joseph Recarey", "entity_type": "person", "aliases": ["Joe Recarey", "Detective Recarey"],
     "description": "Palm Beach Police Detective. Lead field investigator who compiled detailed incident reports documenting Epstein's crimes and the pyramid scheme recruiting minors."},

    {"canonical_name": "E. Nesbitt Kuyrkendall", "entity_type": "person", "aliases": ["Nesbitt Kuyrkendall", "SA Kuyrkendall"],
     "description": "FBI Special Agent. Lead FBI agent on Epstein investigation. Attempted to serve grand jury subpoenas on Epstein associates including Leslie Groff."},

    {"canonical_name": "Jason Richards", "entity_type": "person", "aliases": ["SA Jason Richards"],
     "description": "FBI Special Agent on the Epstein case. Worked with SA Kuyrkendall on investigation."},

    {"canonical_name": "Jeffrey H. Sloman", "entity_type": "person", "aliases": ["Jeffrey Sloman"],
     "description": "First Assistant US Attorney under Alex Acosta in Southern District of Florida. Involved in NPA negotiations. Defended plea deal in February 2019 opinion piece after Miami Herald investigation."},

    {"canonical_name": "Karen Atkinson", "entity_type": "person", "aliases": [],
     "description": "DOJ supervisor of AUSA Marie Villafana on the Epstein case. Handled communications with defense team."},

    {"canonical_name": "Bradley J. Edwards", "entity_type": "person", "aliases": ["Brad Edwards"],
     "description": "Victims' attorney who represented L.M., E.W., and Jane Doe against Epstein. Filed Crime Victims Rights Act lawsuit July 2008 alleging prosecutors violated victims' rights by keeping NPA secret. Case pending for over a decade."},

    {"canonical_name": "Jack Scarola", "entity_type": "person", "aliases": [],
     "description": "Attorney at Searcy Denney Scarola Barnhart and Shipley representing several Epstein victims. Co-counsel with Bradley Edwards."},

    {"canonical_name": "Paul Cassell", "entity_type": "person", "aliases": [],
     "description": "Attorney who filed Crime Victims Rights Act lawsuit on behalf of Epstein victims. February 2019: Judge Kenneth Marra ruled government violated CVRA."},

    {"canonical_name": "Alfredo Rodriguez", "entity_type": "person", "aliases": [],
     "description": "Epstein household employee who kept the 'Holy Grail' journal - a directory from Epstein's computer containing names of underage victims and VIP contacts. Charged with obstruction for trying to sell journal. Testified Maxwell kept photos of girls on her computer."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 13: GOVERNMENT OFFICIALS AND LAW ENFORCEMENT")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH13_ENTITIES:
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
