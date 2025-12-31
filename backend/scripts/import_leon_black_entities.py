"""
Import Leon Black / Epstein financial entities discovered from deep extraction.
These entities document Epstein's management of Leon Black's $6B family office.
"""

import asyncio
import os
import sys
sys.path.insert(0, ".")

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
    # Key People
    {
        "canonical_name": "Leon Black",
        "entity_type": "person",
        "aliases": ["Leon David Black"],
        "description": "Billionaire investor, Apollo Global Management co-founder. Epstein managed his $6B family office from 2014-2016. Paid Epstein $20M+ in consulting fees. Achieved $600M in tax savings through Epstein's strategies.",
    },
    {
        "canonical_name": "Debra Black",
        "entity_type": "person",
        "aliases": ["Debra Ressler Black"],
        "description": "Wife of Leon Black. Discussed in estate planning documents regarding tenants in common agreement with children.",
    },
    {
        "canonical_name": "Brad Wechsler",
        "entity_type": "person",
        "aliases": [],
        "description": "Leon Black's family office manager. Worked under Epstein's guidance from 2014-2016. Described by Epstein as 'highly unsuited for the job'.",
    },
    {
        "canonical_name": "Eileen Alexandersson",
        "entity_type": "person",
        "aliases": [],
        "description": "Former manager of Leon Black's accounting, legal, investments, reporting, and trusts. Described by Epstein as 'incompetent'. Managed 100+ bank accounts.",
    },
    {
        "canonical_name": "Alan Halperin",
        "entity_type": "person",
        "aliases": ["Alan S. Halperin"],
        "description": "Trust attorney for Leon Black. Epstein mentioned he had 'conflicts of interest that should be addressed'.",
    },
    {
        "canonical_name": "Ada Clapp",
        "entity_type": "person",
        "aliases": [],
        "description": "Trust and GRAT administrator for Leon Black's family office. Oversaw execution of trust paperwork.",
    },
    {
        "canonical_name": "Richard Joslin",
        "entity_type": "person",
        "aliases": [],
        "description": "Financial advisor in Leon Black's family office. Took instructions from Eileen Alexandersson. Epstein described his work as 'totally incomprehensible'.",
    },
    {
        "canonical_name": "Joe Avantario",
        "entity_type": "person",
        "aliases": [],
        "description": "Staff member in Leon Black's family office. Involved in loan calculations and transaction processing.",
    },
    {
        "canonical_name": "Barry J. Cohen",
        "entity_type": "person",
        "aliases": [],
        "description": "Advisor involved in trust reviews for Leon Black. Requested to attend meetings with Epstein.",
    },
    {
        "canonical_name": "Brad Karp",
        "entity_type": "person",
        "aliases": [],
        "description": "Paul Weiss attorney. Negotiated Epstein's fee reduction from $50-60M to $20M for family office work.",
    },
    {
        "canonical_name": "Heather Gray",
        "entity_type": "person",
        "aliases": [],
        "description": "Staff member who met with Epstein on Leon Black family office matters.",
    },
    {
        "canonical_name": "Larry Delson",
        "entity_type": "person",
        "aliases": [],
        "description": "Proposed by Epstein as CEO of Leon Black's family office. 'Everyone would report to him.'",
    },
    # Organizations
    {
        "canonical_name": "Apollo Global Management",
        "entity_type": "organization",
        "aliases": ["Apollo", "Apollo Management"],
        "description": "Private equity firm co-founded by Leon Black in 1990. Coordinated with family office on tax matters. In-house counsel involved in accounting oversight.",
    },
    {
        "canonical_name": "Phaidon Press",
        "entity_type": "organization",
        "aliases": ["Phaidon"],
        "description": "Publishing company owned by Leon Black. Epstein structured transaction for $24M+ tax savings. Note payoff calculated at 33% of $1.8 billion.",
    },
    {
        "canonical_name": "Gagosian Gallery",
        "entity_type": "organization",
        "aliases": ["Gagosian"],
        "description": "Art dealer that received $100M+ overseas transfers from Leon Black without written contract. Epstein flagged as suspicious: 'on the tax dept radar'.",
    },
    {
        "canonical_name": "Athene Holding",
        "entity_type": "organization",
        "aliases": ["Athene"],
        "description": "Insurance/annuity company related to Apollo. Transaction discussed with '$2 billion in taxes' implications.",
    },
    {
        "canonical_name": "Regan Arts",
        "entity_type": "organization",
        "aliases": [],
        "description": "Publishing company. Leon Black invested $9.8M. No P&L ever produced. COO fired after 3 months. 'Construction project run amok.'",
    },
    {
        "canonical_name": "Art Space",
        "entity_type": "organization",
        "aliases": ["ArtSpace"],
        "description": "Leon Black's art-related entity. Took $3M deductions with 'ZERO benefit'. Financials described as 'total mess'.",
    },
    {
        "canonical_name": "Elysium Office",
        "entity_type": "organization",
        "aliases": ["Elysium"],
        "description": "Leon Black's family office. Epstein proposed budget of $3-5M per year with CEO at $1M.",
    },
    # Trusts and Legal Structures
    {
        "canonical_name": "APO-1 Trust",
        "entity_type": "trust",
        "aliases": ["APO1", "APOL"],
        "description": "Trust structure for Leon Black. Bank account opened at Bank of America December 2015.",
    },
    {
        "canonical_name": "APO-01 Trust",
        "entity_type": "trust",
        "aliases": ["APO-O1"],
        "description": "New trust formed for decanting from APO-1. Part of $600M tax savings structure.",
    },
    {
        "canonical_name": "Judy Black Trust",
        "entity_type": "trust",
        "aliases": [],
        "description": "Family trust. Epstein recommended 'get rid of' this trust in estate restructuring.",
    },
    {
        "canonical_name": "E Trust",
        "entity_type": "trust",
        "aliases": [],
        "description": "Trust mentioned in Leon Black estate planning discussions with Epstein.",
    },
    {
        "canonical_name": "J Black Trust",
        "entity_type": "trust",
        "aliases": [],
        "description": "Trust mentioned in Leon Black estate planning discussions with Epstein.",
    },
]


RELATIONSHIPS = [
    # Epstein - Leon Black
    {
        "source": "Jeffrey Epstein",
        "target": "Leon Black",
        "type": "financial_advisor",
        "description": "Epstein managed Leon Black's $6B family office from 2014-2016, achieving $600M in tax savings. Paid $20M+ in consulting fees.",
        "evidence": "HOUSE_OVERSIGHT_023208.txt"
    },
    # Leon Black - Apollo
    {
        "source": "Leon Black",
        "target": "Apollo Global Management",
        "type": "founder",
        "description": "Co-founded Apollo Global Management in 1990. Family office coordinated with Apollo on tax matters.",
        "evidence": "HOUSE_OVERSIGHT_023208.txt"
    },
    # Leon Black - Phaidon
    {
        "source": "Leon Black",
        "target": "Phaidon Press",
        "type": "owner",
        "description": "Owns Phaidon Press. Epstein structured note payoff transaction for $600M tax savings.",
        "evidence": "HOUSE_OVERSIGHT_023208.txt"
    },
    # Leon Black - Gagosian
    {
        "source": "Leon Black",
        "target": "Gagosian Gallery",
        "type": "art_client",
        "description": "Transferred $100M+ overseas to Gagosian without written contract. Flagged by Epstein as suspicious.",
        "evidence": "HOUSE_OVERSIGHT_023208.txt"
    },
    # Epstein - Gratitude America
    {
        "source": "Jeffrey Epstein",
        "target": "Gratitude America Ltd",
        "type": "directed_payment",
        "description": "Epstein directed $10M payment from Leon Black to Gratitude America (501c3) on April 15, 2015.",
        "evidence": "HOUSE_OVERSIGHT_023208.txt - '10m paid today to gratitude america, a 501 c 3'"
    },
    # Epstein - FTC
    {
        "source": "Jeffrey Epstein",
        "target": "Financial Trust Company",
        "type": "directed_payment",
        "description": "Epstein directed $20M payment to FTC on April 15, 2015, plus scheduled payments totaling $20M more.",
        "evidence": "HOUSE_OVERSIGHT_023208.txt - '20 million paid today ftc'"
    },
    # Brad Karp - Paul Weiss
    {
        "source": "Brad Karp",
        "target": "Paul Weiss",
        "type": "partner",
        "description": "Paul Weiss partner who negotiated Epstein's fee reduction for Leon Black work.",
        "evidence": "HOUSE_OVERSIGHT_023208.txt"
    },
]


async def main():
    client = get_supabase_client()
    db = SupabaseResearchDB(client=client, workspace_id="default")

    print("=" * 60)
    print("IMPORTING LEON BLACK / EPSTEIN FINANCIAL ENTITIES")
    print("Source: HOUSE_OVERSIGHT_023208.txt deep extraction")
    print("=" * 60)

    created = 0
    skipped = 0

    for entity_data in NEW_ENTITIES:
        # Check if entity already exists
        existing = await db.find_entity_by_name(entity_data["canonical_name"])

        if existing:
            print(f"SKIP (exists): {entity_data['canonical_name']}")
            # Update description if more detailed
            if len(entity_data.get("description", "")) > len(existing.description or ""):
                try:
                    db.client.table("knowledge_entities").update({
                        "description": entity_data["description"]
                    }).eq("id", str(existing.id)).execute()
                    print(f"  -> Updated description")
                except Exception as e:
                    print(f"  -> Error updating: {e}")
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

    print(f"\nEntities - Created: {created}, Skipped: {skipped}")

    # Create relationships
    print("\n" + "=" * 60)
    print("CREATING RELATIONSHIPS")
    print("=" * 60)

    rel_created = 0
    for rel in RELATIONSHIPS:
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
                "evidence_sources": [rel.get("evidence", "deep_extraction")],
                "workspace_id": "default"
            }).execute()

            print(f"CREATED: {rel['source']} -> {rel['target']} ({rel['type']})")
            rel_created += 1

        except Exception as e:
            print(f"ERROR: {rel['source']} -> {rel['target']}: {e}")

    print(f"\nRelationships created: {rel_created}")
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
