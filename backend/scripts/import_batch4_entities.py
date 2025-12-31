"""
Import Batch 4 entities: Celebrity/PR network, victim discrediting campaign.
Major discovery: Peggy Siegal's role organizing Epstein social events post-conviction.
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


BATCH4_ENTITIES = [
    # === Peggy Siegal - Major PR Figure ===
    {"canonical_name": "Peggy Siegal", "entity_type": "person", "aliases": [],
     "description": "Hollywood publicist, 'PR Doyenne'. Organized Epstein social events post-conviction including Yom Kippur Break Fast (120 guests with children, 2010). Epstein asked her to contact Arianna Huffington to attack Virginia Roberts. Still arranging his attendance at 2017 Gotham Awards."},

    # === UK Political Connection ===
    {"canonical_name": "Peter Mandelson", "entity_type": "person", "aliases": ["Lord Mandelson"],
     "description": "Labour politician, European Commissioner, Blair ally. Email contact with Epstein March 2011. Epstein forwarded BBC interview request about Prince Andrew to him. Mandelson replied 'No!!'"},

    # === Media Figures ===
    {"canonical_name": "Arianna Huffington", "entity_type": "person", "aliases": ["Ariana Huffington"],
     "description": "Huffington Post founder. Epstein wanted Peggy Siegal to contact her in July 2011 to attack Virginia Roberts as 'a fraud' and 'total liar' similar to DSK accuser."},

    {"canonical_name": "Kirsty MacKenzie", "entity_type": "person", "aliases": [],
     "description": "BBC Today Programme Interviews Editor. March 2011 requested interview with Epstein about Prince Andrew stories. Request forwarded to Peggy Siegal and Peter Mandelson."},

    {"canonical_name": "Jesse Kornbluth", "entity_type": "person", "aliases": [],
     "description": "NY Times journalist. April 2011 investigated why rich people don't shun Epstein. Asked Peggy Siegal why she continued to host his events post-conviction."},

    # === Reputation Management ===
    {"canonical_name": "Tyler Shears", "entity_type": "person", "aliases": [],
     "description": "SEO/reputation management consultant. January 2014 worked to 'clean up' Epstein's Google search results. Promised 'clean first page' in 45 days. Dealt with foundation site hack."},

    # === Business Associates ===
    {"canonical_name": "David Mitchell", "entity_type": "person", "aliases": [],
     "description": "Mitchell Holdings LLC (745 Fifth Avenue). January 2019 sent Epstein article about Trump-Deutsche Bank House Intelligence Committee investigation."},

    {"canonical_name": "Steven Pfeiffer", "entity_type": "person", "aliases": [],
     "description": "Independent Filmmaker Project Associate Director of Development. November 2017 coordinated Epstein's $10,000 Gotham Awards donation through Peggy Siegal and Richard Kahn."},

    # === Organizations ===
    {"canonical_name": "Independent Filmmaker Project", "entity_type": "organization", "aliases": ["IFP"],
     "description": "Film organization. November 2017 Epstein bought $10,000 table at Gotham Awards honoring Al Gore (Humanitarian Tribute). Peggy Siegal facilitated."},

    {"canonical_name": "BBC Today Programme", "entity_type": "organization", "aliases": ["Today Programme", "BBC Today"],
     "description": "BBC flagship morning news show. March 2011 Kirsty MacKenzie requested Epstein interview about Prince Andrew. Named Bill Gates, Stephen Hawking among past guests."},

    {"canonical_name": "Mitchell Holdings LLC", "entity_type": "organization", "aliases": [],
     "description": "Company at 745 Fifth Avenue, New York. David Mitchell CEO. Sent Epstein Trump-Deutsche Bank news January 2019."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 4: CELEBRITY/PR NETWORK & VICTIM DISCREDITING CAMPAIGN")
    print("Major Discovery: Peggy Siegal organized Epstein events post-conviction")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH4_ENTITIES:
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
    print(f"Total processed: {len(BATCH4_ENTITIES)}")


if __name__ == "__main__":
    asyncio.run(main())
