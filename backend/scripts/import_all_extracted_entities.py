"""
Import all entities discovered from deep Epstein files extraction.
Combines entities from batch 1, batch 2, and Leon Black analysis.
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


# All entities from deep extraction
ALL_ENTITIES = [
    # === BATCH 1: FBI/Court Documents ===
    {"canonical_name": "Steven Hoffenberg", "entity_type": "person", "aliases": ["Steve Hoffenberg"],
     "description": "Convicted Ponzi scheme operator. Ran Tower Financial $460M fraud. Employed Epstein 1987-1993."},

    {"canonical_name": "Robert Meister", "entity_type": "person", "aliases": [],
     "description": "Aon Corporation Vice Chairman. Introduced Epstein to Leslie Wexner in 1989."},

    {"canonical_name": "Wendy Meister", "entity_type": "person", "aliases": [],
     "description": "Robert Meister's wife. Called Epstein 'the virus' when he infiltrated their social circle."},

    {"canonical_name": "Ana Obregón", "entity_type": "person", "aliases": ["Ana Obregon"],
     "description": "Spanish actress. Epstein's first major client (1982). He recovered her father's money from Drysdale collapse."},

    {"canonical_name": "Eva Andersson-Dubin", "entity_type": "person", "aliases": ["Eva Andersson", "Miss Sweden 1980"],
     "description": "Miss Sweden 1980, physician. Dated Epstein, later married Glenn Dubin. Remained close to Epstein."},

    {"canonical_name": "Glenn Dubin", "entity_type": "person", "aliases": [],
     "description": "Hedge fund manager, Highbridge Capital. Married Eva Andersson. Close associate of Epstein."},

    {"canonical_name": "Jean-Luc Brunel", "entity_type": "person", "aliases": ["JL Brunel"],
     "description": "MC2 Modeling Agency owner. Epstein invested $1M. Accused of supplying underage models."},

    {"canonical_name": "Maritza Vasquez", "entity_type": "person", "aliases": [],
     "description": "MC2 Modeling finances 2003-2006. Testified about $1M Epstein investment and model apartment housing."},

    {"canonical_name": "Juan Alessi", "entity_type": "person", "aliases": [],
     "description": "Epstein household employee. Testified Dershowitz visited 'four or five times a year' staying 2-3 days."},

    {"canonical_name": "Alfredo Rodriguez", "entity_type": "person", "aliases": [],
     "description": "Epstein household employee. Kept secret journal as 'insurance policy'. Convicted for trying to sell it."},

    {"canonical_name": "Maria Farmer", "entity_type": "person", "aliases": [],
     "description": "Epstein employee at 9 E 71st St mansion. 'Manned the front door' and witnessed underage girls."},

    {"canonical_name": "Joe Recarey", "entity_type": "person", "aliases": ["Detective Recarey"],
     "description": "Palm Beach Police Detective. Lead investigator on Epstein case."},

    {"canonical_name": "Haley Robson", "entity_type": "person", "aliases": [],
     "description": "Victim recruiter. Described as 'like a Heidi Fleiss'. Paid to bring underage girls."},

    {"canonical_name": "R. Alexander Acosta", "entity_type": "person", "aliases": ["Alex Acosta"],
     "description": "US Attorney who signed Epstein NPA. Later Trump's Labor Secretary (resigned 2019)."},

    {"canonical_name": "Marie Villafana", "entity_type": "person", "aliases": ["A. Marie Villafana"],
     "description": "AUSA who handled Epstein case in Southern District of Florida."},

    {"canonical_name": "Kenneth Starr", "entity_type": "person", "aliases": ["Ken Starr"],
     "description": "Former Solicitor General, Independent Counsel. Part of Epstein's legal team."},

    {"canonical_name": "Jay Lefkowitz", "entity_type": "person", "aliases": ["Jay P. Lefkowitz"],
     "description": "Kirkland & Ellis attorney. Lead negotiator for Epstein's NPA."},

    {"canonical_name": "Roy Black", "entity_type": "person", "aliases": [],
     "description": "Defense attorney (Rush Limbaugh, WK Smith). Part of Epstein's legal team."},

    {"canonical_name": "Barry Krischer", "entity_type": "person", "aliases": [],
     "description": "Palm Beach State Attorney. Criticized for lenient treatment of Epstein case."},

    {"canonical_name": "Michael Reiter", "entity_type": "person", "aliases": [],
     "description": "Palm Beach Police Chief. Pushed for stronger prosecution of Epstein."},

    # === Organizations from Batch 1 ===
    {"canonical_name": "MC2 Modeling Agency", "entity_type": "organization", "aliases": ["MC2", "MC2 Model Management"],
     "description": "Jean-Luc Brunel's modeling agency. Epstein invested $1M. Supplied young models, some housed at 301 E 66th St."},

    {"canonical_name": "Tower Financial Corporation", "entity_type": "organization", "aliases": ["Tower Financial"],
     "description": "Steven Hoffenberg's company. $460M Ponzi scheme. Epstein worked there 1987-1993."},

    {"canonical_name": "Drysdale Securities", "entity_type": "organization", "aliases": ["Drysdale Government Securities", "DGS"],
     "description": "Collapsed 1982 with $160M default. Epstein recovered money for Spanish investors from Cayman Islands."},

    {"canonical_name": "Kirkland & Ellis LLP", "entity_type": "organization", "aliases": ["Kirkland & Ellis"],
     "description": "Law firm. Jay Lefkowitz represented Epstein in NPA negotiations."},

    {"canonical_name": "Podhurst Orseck Josefsberg", "entity_type": "organization", "aliases": ["Podhurst Josefsberg"],
     "description": "Law firm selected to represent 34 Epstein victims in federal compensation process."},

    # === BATCH 2: Additional Documents ===
    {"canonical_name": "Doug Band", "entity_type": "person", "aliases": ["Douglas Band"],
     "description": "Bill Clinton's assistant. 21 phone numbers for Clinton in Epstein's directory listed under 'Doug Bands'."},

    {"canonical_name": "Larry Visoski", "entity_type": "person", "aliases": [],
     "description": "Epstein's longtime personal pilot. Flew the Gulfstream and Boeing 727 ('Lolita Express')."},

    {"canonical_name": "Adriana Ross", "entity_type": "person", "aliases": ["Adrianna Ross"],
     "description": "Epstein employee. Took Fifth on questions about arranging minors. Flew with Clinton on Epstein's plane."},

    {"canonical_name": "Nadia Marcinkova", "entity_type": "person", "aliases": [],
     "description": "Described as Epstein's 'live-in sex slave'. Brought from Yugoslavia. Became pilot. Co-conspirator in NPA."},

    {"canonical_name": "Sarah Kellen", "entity_type": "person", "aliases": ["Sarah Kensington", "Sarah Kellen Vickers"],
     "description": "Epstein's personal assistant. Co-conspirator in NPA. Married NASCAR driver Brian Vickers."},

    {"canonical_name": "Eduardo Robles", "entity_type": "person", "aliases": [],
     "description": "Dubai architect (Creative Kingdom). Contacted by Epstein Dec 2016 for island development."},

    {"canonical_name": "Sultan Suleiman", "entity_type": "person", "aliases": [],
     "description": "Dubai contact. 'Great friends' with Epstein. Introduced architect Eduardo Robles."},

    {"canonical_name": "Brian Vickers", "entity_type": "person", "aliases": [],
     "description": "NASCAR driver. Married Sarah Kellen (Epstein's assistant/co-conspirator)."},

    {"canonical_name": "Scott Rothstein", "entity_type": "person", "aliases": [],
     "description": "Florida attorney, Ponzi scheme operator. Photo with Governor Charlie Crist in his office."},

    {"canonical_name": "Charlie Crist", "entity_type": "person", "aliases": [],
     "description": "Florida Governor. Autographed photo to Scott Rothstein: 'You are amazing!'"},

    {"canonical_name": "Burman Critton Luttier & Coleman LLP", "entity_type": "organization", "aliases": [],
     "description": "Epstein's West Palm Beach law firm. Handled Jane Doe case service of process."},

    {"canonical_name": "Robert D. Critton Jr.", "entity_type": "person", "aliases": [],
     "description": "Attorney at Burman Critton. Handled Epstein legal matters."},

    {"canonical_name": "Creative Kingdom", "entity_type": "organization", "aliases": [],
     "description": "Dubai architecture/design firm. Business Bay. Contacted for Epstein island development."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("IMPORTING ALL EXTRACTED ENTITIES FROM EPSTEIN FILES")
    print("=" * 70)

    created = 0
    skipped = 0
    updated = 0

    for entity_data in ALL_ENTITIES:
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
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Total processed: {len(ALL_ENTITIES)}")


if __name__ == "__main__":
    asyncio.run(main())
