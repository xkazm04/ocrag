"""
Import Batch 6 entities: Jes Staley banking network, Landon Thomas (NYT), Bannon list.
Major discovery: Epstein's 'list for bannon steve' dated June 30, 2019 - 6 days before arrest.
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


BATCH6_ENTITIES = [
    # === MAJOR: Jes Staley ===
    {"canonical_name": "Jes Staley", "entity_type": "person", "aliases": ["James Staley", "James E. Staley"],
     "description": "JPMorgan Chase Private Banking CEO 2009-2013, Barclays CEO 2015-2021. Extensive email correspondence with Epstein 2010-2017. Epstein facilitated his meeting with UK Chancellor Alistair Darling at Davos 2010, CC'd Peter Mandelson on banking policy discussions. Epstein advised him on Treasury Secretary appointments (suggesting Jamie Dimon or Bill Clinton). Resigned from Barclays 2021 over Epstein ties."},

    # === NY Times Reporter ===
    {"canonical_name": "Landon Thomas Jr.", "entity_type": "person", "aliases": ["Landon Thomas"],
     "description": "New York Times Financial Reporter. 166 documents in Epstein email archive. May 11, 2017 asked Epstein 'How are your Trump contacts responding to Comey?' the day after Comey's firing. Regular correspondent discussing Jes Staley's troubles at Barclays."},

    # === CIA Director ===
    {"canonical_name": "George Tenet", "entity_type": "person", "aliases": [],
     "description": "CIA Director 1997-2004. Mentioned in Epstein emails: Jes Staley had dinner with Tenet and 'my military guy from Brookings' in January 2014. Shows intelligence connections in Epstein network."},

    # === UK Chancellor ===
    {"canonical_name": "Alistair Darling", "entity_type": "person", "aliases": ["Lord Darling"],
     "description": "UK Chancellor of the Exchequer 2007-2010. Epstein facilitated meeting between Darling and JPMorgan's Jes Staley at Davos January 2010. Epstein forwarded UK government intelligence about Darling's position on banking reforms to Staley."},

    # === JPMorgan CEO ===
    {"canonical_name": "Jamie Dimon", "entity_type": "person", "aliases": ["James Dimon"],
     "description": "JPMorgan Chase CEO. Epstein recommended him for Treasury Secretary in May 2011 email to Jes Staley: 'I still think that the only really qualified person is Jamie. knowledge of system, derivatives, banking operations.'"},

    # === Barclays Chairman ===
    {"canonical_name": "John McFarlane", "entity_type": "person", "aliases": [],
     "description": "Barclays Chairman. Discussed in Epstein-Landon Thomas emails during May 2017 whistleblower scandal involving Jes Staley."},

    # === Trump Chief Strategist ===
    {"canonical_name": "Steve Bannon", "entity_type": "person", "aliases": ["Stephen Bannon"],
     "description": "Trump Chief Strategist 2017. Recipient of Epstein's contact 'list for bannon steve' dated June 30, 2019 - just 6 days before Epstein's arrest. List included Gates, Thiel, Clinton, Prince Andrew, Chomsky, and many others."},

    # === Tech/Silicon Valley from Bannon List ===
    {"canonical_name": "Joi Ito", "entity_type": "person", "aliases": ["Joichi Ito"],
     "description": "MIT Media Lab Director (resigned 2019 over Epstein ties). On Epstein's 'list for bannon steve' June 2019. Epstein visited MIT Media Lab and arranged funding."},

    {"canonical_name": "Peter Thiel", "entity_type": "person", "aliases": [],
     "description": "PayPal co-founder, Palantir co-founder. On Epstein's 'list for bannon steve' June 30, 2019."},

    {"canonical_name": "Reid Hoffman", "entity_type": "person", "aliases": [],
     "description": "LinkedIn co-founder. On Epstein's 'list for bannon steve' June 30, 2019."},

    # === Academics from Bannon List ===
    {"canonical_name": "Noam Chomsky", "entity_type": "person", "aliases": [],
     "description": "MIT linguist. On Epstein's 'list for bannon steve' June 30, 2019."},

    {"canonical_name": "E.O. Wilson", "entity_type": "person", "aliases": ["Edward O. Wilson"],
     "description": "Harvard biologist. On Epstein's 'list for bannon steve' June 30, 2019."},

    {"canonical_name": "Brian Greene", "entity_type": "person", "aliases": [],
     "description": "Columbia University physicist. On Epstein's 'list for bannon steve' June 30, 2019."},

    {"canonical_name": "John Brockman", "entity_type": "person", "aliases": [],
     "description": "Edge Foundation founder, literary agent for scientists. On Epstein's 'list for bannon steve' June 30, 2019. Organized events bringing scientists to Epstein's properties."},

    # === Organizations ===
    {"canonical_name": "Barclays", "entity_type": "organization", "aliases": ["Barclays Bank", "Barclays PLC"],
     "description": "UK bank. Jes Staley was CEO 2015-2021. Staley resigned after investigation into his Epstein ties. Subject of FCA investigation."},

    {"canonical_name": "JPMorgan Chase", "entity_type": "organization", "aliases": ["JPMorgan", "J.P. Morgan"],
     "description": "US bank. Maintained Epstein accounts despite sex offense conviction. Jes Staley was Private Banking CEO 2009-2013. Subject of lawsuits for Epstein banking relationship."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 6: JES STALEY / LANDON THOMAS / BANNON LIST")
    print("Major Discovery: Epstein's 'list for bannon steve' - June 30, 2019")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH6_ENTITIES:
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
    print(f"Total processed: {len(BATCH6_ENTITIES)}")


if __name__ == "__main__":
    asyncio.run(main())
