"""
Import Batch 5 entities: Larry Summers, Ehud Barak, and VIP passenger network.
Major discovery: Larry Summers in personal email contact with Epstein March 2019 (4 months before arrest).
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


BATCH5_ENTITIES = [
    # === MAJOR DISCOVERY: Larry Summers ===
    {"canonical_name": "Larry Summers", "entity_type": "person", "aliases": ["Lawrence Summers", "Lawrence H. Summers"],
     "description": "Treasury Secretary 1999-2001, Harvard President 2001-2006. Personal email exchange with Epstein on March 17, 2019 (4 months before arrest). Subject: 'Call from New Yorker' - coordinating media response. Intimate personal advice exchange including Summers writing 'exit strategy' notes. On VIP passenger list for Epstein's private jets."},

    # === Ehud Barak - Israeli PM ===
    {"canonical_name": "Ehud Barak", "entity_type": "person", "aliases": [],
     "description": "Israeli Prime Minister 1999-2001, Defense Minister, IDF Chief of Staff. Regular email contact with Epstein 2016-2017. Election night 2016 wrote 'The Trump momentum, I believe was stopped. Hillary might be on her way to Win.' On VIP passenger list for Epstein's private jets."},

    # === VIP Passenger List - Politicians ===
    {"canonical_name": "Bill Richardson", "entity_type": "person", "aliases": ["William Richardson"],
     "description": "New Mexico Governor. Named in Daily Beast article as Epstein private jet passenger alongside Bill Clinton, Prince Andrew, Ehud Barak, and Larry Summers."},

    # === VIP Passenger List - Media ===
    {"canonical_name": "Katie Couric", "entity_type": "person", "aliases": [],
     "description": "TV journalist. Invited to Epstein house warming dinner at NYC mansion August 2010, months after his release from prison. Along with Charlie Rose, George Stephanopoulos, Prince Andrew."},

    {"canonical_name": "Charlie Rose", "entity_type": "person", "aliases": [],
     "description": "TV journalist. Invited to Epstein house warming dinner August 2010. Michael Wolff in 2016 recommended Rose interview Epstein as part of anti-Trump media strategy."},

    {"canonical_name": "George Stephanopoulos", "entity_type": "person", "aliases": [],
     "description": "ABC journalist, former Clinton aide. Invited to Epstein house warming dinner at NYC mansion August 2010, months after his prison release."},

    # === Epstein Staff - Named Co-Conspirators ===
    {"canonical_name": "Lesley Groff", "entity_type": "person", "aliases": [],
     "description": "Epstein executive assistant. Named co-conspirator in Non Prosecution Agreement. Per Daily Beast: 'Ensured appointment book for twice- or thrice-daily massages was stocked with fresh recruits.'"},

    # === Additional Legal Team ===
    {"canonical_name": "Guy Lewis", "entity_type": "person", "aliases": [],
     "description": "Epstein defense attorney. Part of legal team including Dershowitz, Lefcourt, Roy Black, Kenneth Starr, and Martin Weinberger."},

    # === Witnesses/Sources ===
    {"canonical_name": "Conchita Sarnoff", "entity_type": "person", "aliases": [],
     "description": "Daily Beast journalist. Wrote major expose on Epstein naming VIP passengers including Clinton, Prince Andrew, Barak, Richardson, and Summers."},

    {"canonical_name": "Dr. Stephen Alexander", "entity_type": "person", "aliases": [],
     "description": "Palm Beach psychologist. Provided Epstein's psychological evaluation under special arrangement - Epstein 'was allowed to submit a report by his private psychologist.'"},

    {"canonical_name": "Alfredo Rodriguez", "entity_type": "person", "aliases": [],
     "description": "Epstein household staff member. Gave deposition testimony about operations. Testified that maid Lupita 'wept when she complained about cleaning up after the massage sessions.'"},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 5: LARRY SUMMERS / EHUD BARAK / VIP PASSENGER NETWORK")
    print("Major Discovery: Larry Summers in email contact with Epstein March 2019")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH5_ENTITIES:
        # Check if entity already exists
        existing = await db.find_entity_by_name(entity_data["canonical_name"])

        if existing:
            # Update description if ours is more detailed
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

        # Check aliases
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

        # Create new entity
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
    print(f"Total processed: {len(BATCH5_ENTITIES)}")


if __name__ == "__main__":
    asyncio.run(main())
