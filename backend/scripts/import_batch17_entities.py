"""
Import Batch 17 entities: Israeli connections, intelligence context, and surveillance network.

This batch combines documentary evidence from TrumpEpsteinFiles with broader contextual
knowledge about the alleged intelligence/surveillance operation.
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


BATCH17_ENTITIES = [
    # Israeli/Intelligence Connections
    {"canonical_name": "Robert Maxwell", "entity_type": "person", "aliases": ["Jan Ludvik Hyman Binyamin Hoch", "Captain Bob"],
     "description": "Ghislaine Maxwell's father. Czechoslovakian-born British media tycoon who built Mirror Group Newspapers. Died mysteriously November 5, 1991, falling from his yacht 'Lady Ghislaine' near the Canary Islands. Given a state funeral in Israel on the Mount of Olives attended by Israeli intelligence officials. Former Mossad officer Victor Ostrovsky alleged in 'The Other Side of Deception' that Maxwell was a long-standing Mossad asset used for influence operations and arms deals. His death came after he reportedly threatened to expose Israeli intelligence operations. Ghislaine allegedly inherited intelligence connections and tradecraft from her father."},

    {"canonical_name": "Carbyne", "entity_type": "organization", "aliases": ["Reporty Homeland Security", "Carbyne911"],
     "description": "Israeli emergency response and surveillance technology company, formerly called Reporty Homeland Security. Ehud Barak served as chairman. Jeffrey Epstein was an investor. Other investors included Nicole Junkermann and Peter Thiel's Founders Fund. The company develops technology for emergency call (911) monitoring and location tracking. Connection raises questions about Epstein's investment in Israeli surveillance technology alongside former Israeli Defense Minister."},

    {"canonical_name": "Mega Group", "entity_type": "organization", "aliases": ["The Mega Group"],
     "description": "Secretive organization of approximately 20 wealthy American Jewish businessmen, founded in 1991 by Leslie Wexner and Charles Bronfman. Members included Edgar Bronfman Sr., Michael Steinhardt, Laurence Tisch, Lester Crown, and others. Focus on pro-Israel philanthropy and advocacy. Meets twice yearly. Les Wexner, Epstein's primary financial patron, was a co-founder. The group's activities and member list have largely remained private, leading to speculation about its influence."},

    # Epstein Career Origins
    {"canonical_name": "Steven Hoffenberg", "entity_type": "person", "aliases": ["Steve Hoffenberg"],
     "description": "Jeffrey Epstein's early business partner. CEO of Towers Financial Corporation, which ran a $500 million Ponzi scheme defrauding investors in the late 1980s-early 1990s. Hoffenberg served 18 years in federal prison; Epstein escaped prosecution entirely despite being deeply involved. In later interviews, Hoffenberg claimed Epstein was the 'architect' of the fraud and was 'introduced to intelligence work.' Hoffenberg sued Epstein in 2016 before dying in 2022."},

    {"canonical_name": "Ace Greenberg", "entity_type": "person", "aliases": ["Alan C. Greenberg", "Alan Greenberg"],
     "description": "Chairman and CEO of Bear Stearns (1978-1993). His son was tutored by Epstein while Epstein taught at Dalton School. Greenberg gave Epstein his start on Wall Street, hiring him at Bear Stearns in 1976. Epstein worked there until 1981 before starting his own firm. The connection illustrates how Epstein leveraged his Dalton position to access elite financial circles."},

    {"canonical_name": "Donald Barr", "entity_type": "person", "aliases": [],
     "description": "Headmaster of the elite Dalton School in Manhattan who hired Jeffrey Epstein to teach math and physics in 1973-1974, despite Epstein having dropped out of college without a degree. Father of William Barr, who later became US Attorney General under both George H.W. Bush and Donald Trump. Donald Barr was himself a former OSS (Office of Strategic Services, CIA precursor) officer. He wrote a science fiction novel 'Space Relations' (1973) about a planet where oligarchs sexually enslave people."},

    {"canonical_name": "Bear Stearns", "entity_type": "organization", "aliases": [],
     "description": "Major Wall Street investment bank where Jeffrey Epstein worked 1976-1981 after leaving Dalton School. Epstein was hired after tutoring the son of chairman Ace Greenberg. He worked in the special products division. Left to start J. Epstein & Co. in 1982. Bear Stearns collapsed during 2008 financial crisis and was acquired by JPMorgan Chase. Multiple Epstein associates had Bear Stearns connections."},

    {"canonical_name": "Dalton School", "entity_type": "organization", "aliases": ["The Dalton School"],
     "description": "Elite K-12 private school in Manhattan where Jeffrey Epstein taught math and physics from 1973-1976 without a college degree. Headmaster Donald Barr (father of future AG William Barr) hired him. While there, Epstein tutored the children of wealthy families including Ace Greenberg's son, which led to his Wall Street career. The school connection shows Epstein's early pattern of accessing elite circles."},

    # Surveillance Operation Context
    {"canonical_name": "Towers Financial Corporation", "entity_type": "organization", "aliases": ["Towers Financial"],
     "description": "Company run by Steven Hoffenberg that perpetrated a $500 million Ponzi scheme in the late 1980s-early 1990s. Jeffrey Epstein was deeply involved as a consultant and alleged architect of the fraud. When the scheme collapsed, Hoffenberg went to prison for 18 years while Epstein escaped prosecution. The case demonstrates Epstein's ability to evade consequences and possibly suggests protection from powerful interests."},

    # Additional Intelligence-Adjacent Figures
    {"canonical_name": "Nicole Junkermann", "entity_type": "person", "aliases": [],
     "description": "German-British businesswoman and investor. Co-invested with Epstein and Ehud Barak in Carbyne (Israeli surveillance tech company). Connected to global tech and healthcare investment circles. Her investment alongside Epstein in Israeli surveillance technology has drawn scrutiny from investigators examining Epstein's intelligence connections."},

    {"canonical_name": "Louis Freeh", "entity_type": "person", "aliases": [],
     "description": "Former FBI Director (1993-2001). Appears in Epstein documents making FOIA requests to Secret Service about Clinton's travel to Little St. James. Later represented Dershowitz in disputes about Epstein case. His involvement in Epstein-related matters as both former FBI chief and private attorney raises questions about the intersection of law enforcement and Epstein's network."},

    # Update existing entity - Ehud Barak
    {"canonical_name": "Ehud Barak", "entity_type": "person", "aliases": ["Ehud Brog"],
     "description": "Former Israeli Prime Minister (1999-2001) and Defense Minister (2007-2013). Most decorated soldier in Israeli history. Extremely close to Epstein - Mail on Sunday document alleges 'Ms Maxwell and Mr Epstein arranged for Ehud Barak to have sex with several girls, often at Mr Epstein's Palm Beach house.' Served as chairman of Carbyne, Israeli surveillance tech company where Epstein invested. Photographed multiple times entering Epstein's NYC mansion. Received funding connected to Epstein for various ventures. The combination of allegations, business ties, and surveillance tech investment represents the most significant Israeli government connection in the Epstein network."},
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 70)
    print("BATCH 17: ISRAELI CONNECTIONS & INTELLIGENCE CONTEXT")
    print("=" * 70)
    print("\nThis batch combines documentary evidence with contextual knowledge")
    print("about alleged intelligence/surveillance operations.\n")

    created = 0
    skipped = 0
    updated = 0

    for entity_data in BATCH17_ENTITIES:
        existing = await db.find_entity_by_name(entity_data["canonical_name"])

        if existing:
            # For this batch, we want to update with richer descriptions
            if len(entity_data.get("description", "")) > len(existing.description or ""):
                try:
                    db.client.table("knowledge_entities").update({
                        "description": entity_data["description"],
                        "aliases": entity_data.get("aliases", [])
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
    print(f"\nKey themes documented:")
    print("- Robert Maxwell / Mossad allegations")
    print("- Carbyne surveillance technology investment")
    print("- Mega Group / Wexner context")
    print("- Epstein career origins (Dalton, Bear Stearns, Hoffenberg)")
    print("- Surveillance/blackmail operation evidence")


if __name__ == "__main__":
    asyncio.run(main())
