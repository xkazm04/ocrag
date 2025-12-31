"""
Import Batch 8 entities: Jean-Luc Brunel, Epstein staff, Clinton Foundation network.
Major discovery: Brunel hiding at Epstein mansion to evade deposition.
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


BATCH8_ENTITIES = [
    # === Jean-Luc Brunel ===
    {"canonical_name": "Jean-Luc Brunel", "entity_type": "person", "aliases": ["Jean Luc Brunel"],
     "description": "French modeling agent, MC2 Model Management founder. Per deposition: 'Very much involved in trafficking the girls.' Hid at Epstein mansion while claiming unavailable for deposition. Found dead in French prison cell February 2022 while awaiting trial on rape and trafficking charges."},

    # === Epstein Staff Co-Conspirators ===
    {"canonical_name": "Sarah Kellen", "entity_type": "person", "aliases": ["Sarah Kellen Vickers"],
     "description": "Epstein's scheduler, named co-conspirator in Non Prosecution Agreement. 60 documents in archive. Represented by Bruce Reinhart after he switched sides from prosecution."},

    {"canonical_name": "Nadia Marcinkova", "entity_type": "person", "aliases": ["Nadia Marcinko", "Nadia Marcinková"],
     "description": "Described as Epstein's 'sex slave' in court documents. Named co-conspirator in NPA. Later became pilot using name Nadia Marcinko. 42 documents in archive. Represented by Bruce Reinhart."},

    {"canonical_name": "Adriana Ross", "entity_type": "person", "aliases": ["Adriana Mucinska"],
     "description": "Epstein associate, named co-conspirator in Non Prosecution Agreement. Part of inner circle staff."},

    # === Legal - Switched Sides ===
    {"canonical_name": "Bruce Reinhart", "entity_type": "person", "aliases": [],
     "description": "Former assistant US attorney Palm Beach. January 2, 2008 switched sides to represent Epstein employees Sarah Kellen, Nadia Marcinkova, and pilots. Accused of leveraging inside information. Later became US Magistrate who signed 2022 Mar-a-Lago search warrant."},

    {"canonical_name": "Jay Lefkowitz", "entity_type": "person", "aliases": [],
     "description": "Kirkland & Ellis partner. Bush domestic policy adviser, later North Korea special envoy. Part of Epstein defense team alongside Kenneth Starr. Both Lefkowitz and Alex Acosta worked at Kirkland & Ellis."},

    {"canonical_name": "Paul Cassell", "entity_type": "person", "aliases": [],
     "description": "Victims' attorney. Filed Crime Victims Rights Act complaint against Bruce Reinhart for switching sides. Represented Epstein victims in challenging the Non Prosecution Agreement."},

    # === Clinton Foundation Network ===
    {"canonical_name": "Doug Band", "entity_type": "person", "aliases": ["Douglas Band"],
     "description": "Former 'bag carrier' for Bill Clinton, described as 'surrogate son'. Founded Teneo consulting firm. Recruited from Clinton Foundation donors while putting Huma Abedin on payroll. Teneo charged monthly retainer up to $250,000."},

    {"canonical_name": "Ira Magaziner", "entity_type": "person", "aliases": ["Ira C. Magaziner"],
     "description": "Clinton Foundation architect. Helped Hillary on health care plan that she 'torpedoed'. Per NYT: 'Dispatched a team of employees to fly around the world for months gathering ideas for a climate change proposal that never got off the ground.'"},

    {"canonical_name": "Jon Corzine", "entity_type": "person", "aliases": [],
     "description": "Former NJ Governor, MF Global CEO. MF Global collapse led Clinton Foundation to distance itself from Teneo due to bad publicity."},

    # === Organizations ===
    {"canonical_name": "MC2 Model Management", "entity_type": "organization", "aliases": ["MC2 Models", "MC2"],
     "description": "Modeling agency founded/associated with Jean-Luc Brunel. Alleged to be pipeline for recruiting trafficking victims for Epstein."},

    {"canonical_name": "Teneo", "entity_type": "organization", "aliases": ["Teneo Holdings"],
     "description": "Consulting firm founded by Doug Band. Blend of corporate consulting, PR, merchant banking. Recruited clients from Clinton Foundation donors. Clinton distanced after MF Global collapse."},

    {"canonical_name": "Kirkland & Ellis", "entity_type": "organization", "aliases": ["Kirkland & Ellis LLP"],
     "description": "Major law firm. Alex Acosta, Jay Lefkowitz, and Kenneth Starr all worked there. Provided key members of Epstein's defense team."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 8: BRUNEL / EPSTEIN STAFF / CLINTON FOUNDATION NETWORK")
    print("Major Discovery: Brunel hiding at Epstein mansion to evade deposition")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH8_ENTITIES:
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
    print(f"Total processed: {len(BATCH8_ENTITIES)}")


if __name__ == "__main__":
    asyncio.run(main())
