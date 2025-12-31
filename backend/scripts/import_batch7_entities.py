"""
Import Batch 7 entities: Glenn/Eva Dubin, Boris Nikolic, victim allegation names.
Major discovery: March 2011 Mail on Sunday victim allegations naming Dubin, Wexner, Mitchell, Kosslyn, Barak.
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


BATCH7_ENTITIES = [
    # === Glenn & Eva Dubin ===
    {"canonical_name": "Glenn Dubin", "entity_type": "person", "aliases": [],
     "description": "Highbridge Capital co-founder, hedge fund manager. Named in March 2011 Mail on Sunday victim allegations as someone victim was 'required to have sex' with. 55 documents in Epstein archive. April 2018 sent Epstein Michael Cohen/Trump New Yorker article. Eva Andersson Dubin was Epstein's girlfriend before marrying Glenn."},

    {"canonical_name": "Eva Dubin", "entity_type": "person", "aliases": ["Eva Andersson", "Eva Andersson-Dubin"],
     "description": "Swedish model, Glenn Dubin's wife. Former Epstein girlfriend 1980s. Regular email correspondent with Epstein through 2016. Nov 4, 2016 Epstein emailed her 'told you, the case was a fake' about Trump lawsuit dismissal (4 days before election)."},

    # === Boris Nikolic - Gates Connection ===
    {"canonical_name": "Boris Nikolic", "entity_type": "person", "aliases": [],
     "description": "Bill Gates' former science advisor, Biomatics Capital founder. March 2011 defended Epstein after Vicky Ward article: 'What is this??? When this will stop. This is crazy.' Named as backup executor in Epstein's August 2019 will."},

    # === Harvard Psychologist ===
    {"canonical_name": "Stephen Kosslyn", "entity_type": "person", "aliases": ["Stephen M. Kosslyn"],
     "description": "Harvard psychologist, later Minerva Schools founding dean. Named in March 2011 Mail on Sunday victim allegations as someone victim was 'required to have sex' with. On Epstein's June 2019 Bannon list."},

    # === Senator George Mitchell ===
    {"canonical_name": "George Mitchell", "entity_type": "person", "aliases": ["George J. Mitchell"],
     "description": "Former US Senator (D-Maine), Senate Majority Leader 1989-1995. Named in March 2011 Mail on Sunday victim allegations. On Epstein's June 2019 Bannon list."},

    # === Media Mogul ===
    {"canonical_name": "Mort Zuckerman", "entity_type": "person", "aliases": ["Mortimer Zuckerman"],
     "description": "Media mogul, NY Daily News owner, US News & World Report, Boston Properties founder. 70 documents in Epstein archive. Quoted in March 2011 Vanity Fair: 'Jeffrey knows a good deal about most subjects.' Described as financier who 'hangs out' with Epstein."},

    # === Journalists ===
    {"canonical_name": "Vicky Ward", "entity_type": "person", "aliases": [],
     "description": "Journalist. Wrote 2003 Vanity Fair 'The Talented Mr. Epstein' and March 2011 follow-up 'Jeffrey and Ghislaine: Notes on New York's Oddest Alliance'. Named Wexner, Cayne, Hoffenberg as associates."},

    {"canonical_name": "Annette Witheridge", "entity_type": "person", "aliases": [],
     "description": "Mail on Sunday journalist. March 2011 sent detailed victim allegations to Ghislaine Maxwell's lawyer naming Glenn Dubin, Les Wexner, Ehud Barak, George Mitchell, Stephen Kosslyn, Prince Andrew."},

    # === Bear Stearns ===
    {"canonical_name": "Jimmy Cayne", "entity_type": "person", "aliases": ["James Cayne"],
     "description": "Bear Stearns CEO 1993-2008. Named as early Epstein associate in 2003 Vanity Fair article. Epstein worked at Bear Stearns before leaving in 1981."},

    # === Epstein Mentor ===
    {"canonical_name": "Steven Jude Hoffenberg", "entity_type": "person", "aliases": ["Steve Hoffenberg"],
     "description": "Towers Financial fraudster, serving 20-year sentence for $450M fraud. Claimed to be Epstein's mentor. Named in Vanity Fair 2003 as someone who was 'above all' close to Epstein."},

    # === Maxwell Lawyer ===
    {"canonical_name": "Mark Cohen", "entity_type": "person", "aliases": [],
     "description": "Attorney for Ghislaine Maxwell. March 2011 received Mail on Sunday victim allegations inquiry from Annette Witheridge. Forwarded to Maxwell who forwarded to Epstein and lawyers."},

    # === Organizations ===
    {"canonical_name": "Highbridge Capital", "entity_type": "organization", "aliases": ["Highbridge Capital Management"],
     "description": "Hedge fund co-founded by Glenn Dubin. One of largest alternative asset managers."},

    {"canonical_name": "Biomatics Capital", "entity_type": "organization", "aliases": [],
     "description": "Healthcare venture capital firm founded by Boris Nikolic (Bill Gates' former science advisor)."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 7: DUBIN / BORIS NIKOLIC / VICTIM ALLEGATION NAMES")
    print("Major Discovery: March 2011 Mail on Sunday victim allegations")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH7_ENTITIES:
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
    print(f"Total processed: {len(BATCH7_ENTITIES)}")


if __name__ == "__main__":
    asyncio.run(main())
