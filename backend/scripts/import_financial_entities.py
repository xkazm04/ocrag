"""
Import new financial entities discovered from Epstein files extraction.
Also merges duplicate entities.
"""

import asyncio
import os
import sys
sys.path.insert(0, ".")

from uuid import UUID
from supabase import create_client, Client
from app.research.db import SupabaseResearchDB
from app.research.schemas import KnowledgeEntityCreate


def get_supabase_client() -> Client:
    """Create Supabase client from environment."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

    return create_client(url, key)


NEW_ENTITIES = [
    {
        "canonical_name": "Gratitude America Ltd",
        "entity_type": "organization",
        "aliases": ["Gratitude America"],
        "description": "501(c)(3) nonprofit formed in Virgin Islands in 2012, used by Epstein for financial contributions. Received $10M+ in documented transfers.",
    },
    {
        "canonical_name": "Financial Trust Company",
        "entity_type": "organization",
        "aliases": ["FTC", "Financial Trust Co"],
        "description": "Trust company that received $20M+ from Epstein in April 2015 and additional scheduled payments.",
    },
    {
        "canonical_name": "Great St. Jim LLC",
        "entity_type": "organization",
        "aliases": ["Great St. Jim", "GSJ LLC"],
        "description": "Shell company organized by Erika Kellerhals on Oct 26, 2015 to purchase Great St. James Island for $22.5M.",
    },
    {
        "canonical_name": "GSJ Properties Corp",
        "entity_type": "organization",
        "aliases": [],
        "description": "Virgin Islands corporation that transferred 81.22 acres (12 parcels) on Great St. James to Great St. Jim LLC for $5M in Jan 2016.",
    },
    {
        "canonical_name": "Poplar Inc",
        "entity_type": "organization",
        "aliases": [],
        "description": "Virgin Islands corporation formed in 2011. Officers: Jeffrey Epstein (President), Darren Indyke (VP/Secretary), Richard Kahn (Treasurer). Used for island development.",
    },
    {
        "canonical_name": "Epstein Interests",
        "entity_type": "organization",
        "aliases": [],
        "description": "Defunct corporation with officers Erika Kellerhals, Darren Indyke, and Richard Kahn.",
    },
    {
        "canonical_name": "C.O.U.Q. Foundation",
        "entity_type": "organization",
        "aliases": ["COUQ Foundation"],
        "description": "Defunct nonprofit run by Epstein, with officers Erika Kellerhals, Darren Indyke, and Richard Kahn.",
    },
    {
        "canonical_name": "J. Epstein Virgin Islands Foundation",
        "entity_type": "organization",
        "aliases": ["J. Epstein VI Foundation", "Epstein VI Foundation"],
        "description": "Defunct nonprofit foundation in Virgin Islands, run by Epstein with officers Kellerhals, Indyke, and Kahn.",
    },
    {
        "canonical_name": "International Assets Group",
        "entity_type": "organization",
        "aliases": ["IAG"],
        "description": "Epstein's first company after leaving Bear Stearns (1982-1983), initially run from his apartment. Used to recover funds from Drysdale Securities collapse.",
    },
    {
        "canonical_name": "Erika Kellerhals",
        "entity_type": "person",
        "aliases": [],
        "description": "St. Thomas attorney who organized multiple Epstein shell companies including Great St. Jim LLC. Sole member of Great St. Jim LLC.",
    },
    {
        "canonical_name": "Brett Geary",
        "entity_type": "person",
        "aliases": [],
        "description": "Business consultant who helped organize Poplar Inc in 2011. Operates Business Basics VI LLC, resident agent for Epstein entities.",
    },
    {
        "canonical_name": "Gregory Ferguson",
        "entity_type": "person",
        "aliases": [],
        "description": "Attorney in Kellerhals firm who helped organize Poplar Inc in 2011.",
    },
    {
        "canonical_name": "Business Basics VI LLC",
        "entity_type": "organization",
        "aliases": [],
        "description": "Brett Geary's company serving as resident agent for Epstein entities in Virgin Islands.",
    },
    {
        "canonical_name": "Melanie Spinella",
        "entity_type": "person",
        "aliases": [],
        "description": "Executive assistant who received financial communications from Richard Kahn regarding Epstein's finances in 2015.",
    },
]


# Duplicate entities to merge
DUPLICATES_TO_MERGE = [
    {
        "target_name": "Darren Indyke",
        "source_names": ["Darren K. Indyke"],
        "description": "Longtime Epstein attorney, Co-Executor of Estate. VP/Secretary of Poplar Inc, officer of multiple shell companies."
    },
    {
        "target_name": "Richard D. Kahn",
        "source_names": [],  # Just update description
        "description": "Treasurer/Financial advisor for Epstein. Co-Executor of Estate. Treasurer of Poplar Inc. Handled $50M+ in documented transfers."
    }
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 60)
    print("IMPORTING NEW FINANCIAL ENTITIES")
    print("=" * 60)

    created = 0
    skipped = 0

    for entity_data in NEW_ENTITIES:
        # Check if entity already exists
        existing = await db.find_entity_by_name(entity_data["canonical_name"])

        if existing:
            print(f"SKIP (exists): {entity_data['canonical_name']}")
            skipped += 1
            continue

        # Also check aliases
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
            print(f"ERROR creating {entity_data['canonical_name']}: {e}")

    print(f"\nCreated: {created}, Skipped: {skipped}")

    # Merge duplicates
    print("\n" + "=" * 60)
    print("MERGING DUPLICATE ENTITIES")
    print("=" * 60)

    for merge_info in DUPLICATES_TO_MERGE:
        target_name = merge_info["target_name"]
        source_names = merge_info["source_names"]
        new_description = merge_info.get("description")

        # Find target entity
        target = await db.find_entity_by_name(target_name)
        if not target:
            # Try search
            results = await db.search_entities(target_name, limit=5)
            if results:
                target = results[0]

        if not target:
            print(f"SKIP (target not found): {target_name}")
            continue

        # Find source entities to merge
        source_ids = []
        for source_name in source_names:
            source = await db.find_entity_by_name(source_name)
            if not source:
                results = await db.search_entities(source_name, limit=5)
                for r in results:
                    if r.canonical_name == source_name and r.id != target.id:
                        source = r
                        break

            if source and source.id != target.id:
                source_ids.append(source.id)
                print(f"  Will merge: {source.canonical_name} -> {target.canonical_name}")

        # Perform merge if we have sources
        if source_ids:
            try:
                merged = await db.merge_entities(target.id, source_ids)
                print(f"MERGED: {len(source_ids)} entities into {merged.canonical_name}")
            except Exception as e:
                print(f"ERROR merging into {target_name}: {e}")

        # Update description if provided
        if new_description:
            try:
                # Update entity description
                db.client.table("knowledge_entities").update({
                    "description": new_description
                }).eq("id", str(target.id)).execute()
                print(f"UPDATED description: {target_name}")
            except Exception as e:
                print(f"ERROR updating {target_name}: {e}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
