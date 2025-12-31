"""
Import Batch 3 entities: Kathy Ruemmler, Michael Wolff, and political network.
Major discovery: Obama White House Counsel maintained personal relationship with Epstein.
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


BATCH3_ENTITIES = [
    # === MAJOR DISCOVERY: Kathy Ruemmler ===
    {"canonical_name": "Kathy Ruemmler", "entity_type": "person", "aliases": ["Kathryn Ruemmler", "Kathryn H. Ruemmler"],
     "description": "Obama White House Counsel 2011-2014. Later Latham & Watkins partner. Personal friend of Epstein post-conviction. Regular email correspondent 2015-2016. Part of Epstein's legal/media response team. Told Epstein 'Trump is living proof of the adage that it is better to be lucky than smart.'"},

    # === Michael Wolff - Fire and Fury Author ===
    {"canonical_name": "Michael Wolff", "entity_type": "person", "aliases": [],
     "description": "Journalist, author of 'Fire and Fury' (2018) and 'Siege' (2019). Epstein advisor 2016-2019. Advised Epstein in March 2016 to use Trump as 'counter narrative' for 'political cover'. Epstein facilitated Wolff-Ken Starr connection for Siege research."},

    # === Dubai Connection ===
    {"canonical_name": "Sultan Bin Sulayem", "entity_type": "person", "aliases": ["Sultan Ahmed Bin Sulayem"],
     "description": "Chairman DP World and Dubai World Group. Regular email contact with Epstein. Forwarded anti-Trump Clinton speech to Epstein June 2016. Previously introduced architect Eduardo Robles for island development."},

    # === Media Investigators ===
    {"canonical_name": "Matthew Mosk", "entity_type": "person", "aliases": [],
     "description": "ABC News investigative producer. January 2016 requested meeting with Epstein attorney about Trump and Clinton connections to Epstein case."},

    {"canonical_name": "Melanie Hicken", "entity_type": "person", "aliases": [],
     "description": "CNN reporter. October 2016 investigated whether Trump/Clinton had 'sexual relations with minors' on Epstein's island. Contacted Epstein's pilot via LinkedIn."},

    {"canonical_name": "Blake Ellis", "entity_type": "person", "aliases": [],
     "description": "CNN reporter. October 2016 investigated Trump/Clinton island allegations with Melanie Hicken."},

    # === Epstein Legal Team ===
    {"canonical_name": "Martin Weinberg", "entity_type": "person", "aliases": ["Martin G. Weinberg"],
     "description": "Epstein defense attorney. Part of inner circle handling media inquiries and Patterson book response. CC'd with Ruemmler on Wolff strategy emails."},

    # === Political Bundlers ===
    {"canonical_name": "Woody Johnson", "entity_type": "person", "aliases": ["Robert Wood Johnson IV"],
     "description": "NY Jets owner, Johnson & Johnson heir. Major Trump bundler. US Ambassador to UK 2017-2021. Discussed in Epstein emails regarding White House Fellowship appointments."},

    {"canonical_name": "Suzanne Johnson", "entity_type": "person", "aliases": [],
     "description": "Woody Johnson's wife. Discussed in Epstein emails regarding White House Fellowship appointments through their political bundling."},

    {"canonical_name": "Jonathan Farkas", "entity_type": "person", "aliases": [],
     "description": "Epstein associate. May 2017 discussed White House Fellowship appointments with Epstein. Epstein warned him about unnamed woman: 'careful she is nottrustworthy at ALLL'."},

    # === Publishing ===
    {"canonical_name": "Stephen Rubin", "entity_type": "person", "aliases": [],
     "description": "Henry Holt & Company publisher. Invited Epstein (BCC'd) to Michael Wolff 'Siege' book launch party June 2019 at 15 West 67th Street."},

    {"canonical_name": "John Connolly", "entity_type": "person", "aliases": [],
     "description": "Vanity Fair journalist. Actual author of Patterson's 'Filthy Rich' book. Wolff told Epstein that Vanity Fair 'refused to allow him to write about Epstein'. Described as having 'developed an obsession with Epstein'."},

    # === Organizations ===
    {"canonical_name": "Latham & Watkins LLP", "entity_type": "organization", "aliases": ["Latham & Watkins", "Latham"],
     "description": "Major law firm where Kathy Ruemmler was partner after leaving Obama White House. Ruemmler represented Emirates NBD in California trial 2016."},

    {"canonical_name": "Henry Holt and Company", "entity_type": "organization", "aliases": ["Henry Holt", "Henry Holt & Company"],
     "description": "Publisher of Michael Wolff's 'Fire and Fury' and 'Siege'. Stephen Rubin was publisher. Epstein BCC'd on book launch invitations."},

    {"canonical_name": "DP World", "entity_type": "organization", "aliases": ["Dubai Ports World"],
     "description": "Major global ports operator. Sultan Bin Sulayem is Chairman. Part of Dubai World Group. Sulayem in regular contact with Epstein."},

    {"canonical_name": "Dubai World Group", "entity_type": "organization", "aliases": ["Dubai World"],
     "description": "Dubai sovereign wealth investment company. Parent of DP World. Sultan Bin Sulayem associated. Email disclaimer appears on Sulayem-Epstein correspondence."},
]


BATCH3_RELATIONSHIPS = [
    # Ruemmler relationships
    {
        "source": "Kathy Ruemmler",
        "target": "Jeffrey Epstein",
        "type": "personal_friend",
        "description": "Regular personal correspondent 2015-2016+. Visited Epstein in NY. Part of legal/media response team. Discussed Trump strategy.",
        "evidence": "HOUSE_OVERSIGHT_032222-032259"
    },
    {
        "source": "Kathy Ruemmler",
        "target": "Latham & Watkins LLP",
        "type": "partner",
        "description": "Partner at Latham & Watkins after serving as Obama White House Counsel 2011-2014.",
        "evidence": "HOUSE_OVERSIGHT_012037"
    },
    # Wolff relationships
    {
        "source": "Michael Wolff",
        "target": "Jeffrey Epstein",
        "type": "media_advisor",
        "description": "Advised Epstein on media strategy 2016-2019. Recommended using Trump as 'counter narrative'. Epstein facilitated Wolff-Starr connection.",
        "evidence": "HOUSE_OVERSIGHT_033589"
    },
    {
        "source": "Jeffrey Epstein",
        "target": "Kenneth Starr",
        "type": "introduced",
        "description": "Epstein introduced Michael Wolff to Ken Starr in May 2018 for research on 'Siege' book about Trump legal troubles.",
        "evidence": "HOUSE_OVERSIGHT_033564"
    },
    {
        "source": "Michael Wolff",
        "target": "Henry Holt and Company",
        "type": "author",
        "description": "Published Fire and Fury (2018) and Siege (2019) through Henry Holt.",
        "evidence": "HOUSE_OVERSIGHT_033360"
    },
    # Sultan Bin Sulayem
    {
        "source": "Sultan Bin Sulayem",
        "target": "Jeffrey Epstein",
        "type": "business_contact",
        "description": "Regular email correspondent. Forwarded political news. Previously introduced architect for island development.",
        "evidence": "HOUSE_OVERSIGHT_033586, HOUSE_OVERSIGHT_032398"
    },
    {
        "source": "Sultan Bin Sulayem",
        "target": "DP World",
        "type": "chairman",
        "description": "Chairman of DP World global ports operator.",
        "evidence": "HOUSE_OVERSIGHT_033586"
    },
    # White House Fellowship connection
    {
        "source": "Woody Johnson",
        "target": "Donald Trump",
        "type": "political_bundler",
        "description": "Major Trump campaign bundler. Later appointed US Ambassador to UK. Discussed in Epstein emails regarding White House Fellowship appointments.",
        "evidence": "HOUSE_OVERSIGHT_033490"
    },
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 3: KATHY RUEMMLER / MICHAEL WOLFF NETWORK")
    print("Major Discovery: Obama White House Counsel relationship with Epstein")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH3_ENTITIES:
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
    print("CREATING RELATIONSHIPS")
    print("=" * 70)

    rel_created = 0
    for rel in BATCH3_RELATIONSHIPS:
        try:
            source = await db.find_entity_by_name(rel["source"])
            target = await db.find_entity_by_name(rel["target"])

            if not source:
                print(f"SKIP: Source not found - {rel['source']}")
                continue
            if not target:
                print(f"SKIP: Target not found - {rel['target']}")
                continue

            # Check if relationship exists
            existing = db.client.table("entity_relationships").select("*").eq(
                "source_entity_id", str(source.id)
            ).eq(
                "target_entity_id", str(target.id)
            ).eq(
                "relationship_type", rel["type"]
            ).execute()

            if existing.data:
                print(f"SKIP (exists): {rel['source']} -> {rel['target']} ({rel['type']})")
                continue

            # Create relationship
            db.client.table("entity_relationships").insert({
                "source_entity_id": str(source.id),
                "target_entity_id": str(target.id),
                "relationship_type": rel["type"],
                "description": rel["description"],
                "evidence_sources": [rel.get("evidence", "batch3_extraction")],
                "workspace_id": "default"
            }).execute()

            print(f"CREATED: {rel['source']} -> {rel['target']} ({rel['type']})")
            rel_created += 1

        except Exception as e:
            print(f"ERROR: {rel['source']} -> {rel['target']}: {e}")

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)
    print(f"Entities Created: {created}")
    print(f"Entities Updated: {updated}")
    print(f"Entities Skipped: {skipped}")
    print(f"Relationships Created: {rel_created}")
    print(f"Total processed: {len(BATCH3_ENTITIES)}")


if __name__ == "__main__":
    asyncio.run(main())
