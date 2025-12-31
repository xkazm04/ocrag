"""
Import Batch 14 entities: Victims and accusers.
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


BATCH14_ENTITIES = [
    {"canonical_name": "Virginia Giuffre", "entity_type": "person", "aliases": ["Virginia Roberts", "Jane Doe 102", "Virginia Roberts Giuffre"],
     "description": "Primary Epstein accuser. Trafficked by Epstein and Maxwell 2000-2002, starting at age 15. Recruited by Ghislaine Maxwell at Mar-a-Lago. Filed lawsuits against Alan Dershowitz and Prince Andrew. Forced to have sex with Epstein's associates including royalty, politicians, and academics. Fled to Australia September 2002 to escape trafficking."},

    {"canonical_name": "Courtney Wild", "entity_type": "person", "aliases": [],
     "description": "FBI-identified Epstein victim. One of 36+ underage victims. Brought at least 60 girls to Epstein's Palm Beach estate. Filed Crime Victims Rights Act lawsuit against federal government claiming prosecutors deliberately kept victims in the dark about NPA."},

    {"canonical_name": "Sarah Ransome", "entity_type": "person", "aliases": [],
     "description": "Epstein accuser who provided sworn testimony. Alleged she was recruited and trafficked for sex. Reports Epstein lent her to Dershowitz. Now lives in Barcelona. Identified by Dershowitz as one of his 'perjuring accusers'."},

    {"canonical_name": "Maria Farmer", "entity_type": "person", "aliases": [],
     "description": "Epstein employee who was sexually assaulted by both Epstein and Maxwell. Worked 'manning the front desk'. Provided sworn testimony (Exhibit 12 in Giuffre v. Dershowitz). Early accuser who reported abuse to FBI in 1996."},

    {"canonical_name": "Chauntae Davies", "entity_type": "person", "aliases": [],
     "description": "Epstein victim and former flight attendant on Epstein's plane. Recently showed photos documenting Clinton's regular visits with Epstein."},

    {"canonical_name": "Haley Robson", "entity_type": "person", "aliases": [],
     "description": "Recruiter for Epstein. 18-20 year old Palm Beach student at Royal Palm Beach High School. Paid $200 per underage girl brought to Epstein. Described as 'integral player in Epstein's Florida scheme'. Later sued by victims."},

    {"canonical_name": "Annie Farmer", "entity_type": "person", "aliases": [],
     "description": "Epstein accuser. Sister of Maria Farmer. Testified that Epstein sexually abused her when she was 16 years old at Zorro Ranch in New Mexico."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 14: VICTIMS AND ACCUSERS")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH14_ENTITIES:
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
