"""
Export Epstein Investigation data to CSV files for Hex dashboards.

Creates 5 dataset groups:
1. Network Graph - nodes.csv, edges.csv
2. Financial Flow - transactions.csv, entity_totals.csv, time_series.csv
3. Timeline - events.csv, parallel_tracks.csv
4. Geographic - locations.csv, jurisdictions.csv
5. Evidence Matrix - claims.csv, evidence_gaps.csv, source_reliability.csv
"""

import os
import sys
import csv
import json
import re
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Add project root to path
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent.parent / "hex_datasets"


def get_supabase_client() -> Client:
    """Create Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")


def write_csv(filename: str, rows: List[Dict], fieldnames: List[str]):
    """Write rows to CSV file."""
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Written: {filename} ({len(rows)} rows)")


def categorize_entity(entity_type: str, name: str, description: str = "") -> str:
    """Categorize entity for visualization."""
    name_lower = name.lower()
    desc_lower = (description or "").lower()

    # Core network
    if any(n in name_lower for n in ["epstein", "maxwell", "kellen", "groff", "marcinkova", "ross"]):
        return "core"

    # Intelligence/Defense
    if entity_type == "intelligence_agency" or any(k in desc_lower for k in ["mossad", "cia", "intelligence", "unit 8200", "carbyne", "palantir"]):
        return "intel_defense"

    # Finance
    if entity_type in ["corporation", "shell_company", "trust", "foundation"] or any(k in desc_lower for k in ["wexner", "black", "apollo", "jpmorgan", "deutsche"]):
        return "finance"

    # Legal
    if any(k in desc_lower for k in ["attorney", "prosecutor", "judge", "fbi", "doj", "acosta"]):
        return "legal"

    # Victims
    if any(k in desc_lower for k in ["victim", "accuser", "survivor", "recruited"]):
        return "victim"

    # Political
    if any(k in desc_lower for k in ["president", "governor", "senator", "prince", "prime minister", "politician"]):
        return "political"

    # Property
    if entity_type == "location" or any(k in desc_lower for k in ["island", "mansion", "ranch", "apartment"]):
        return "property"

    return "other"


def extract_financial_data(description: str) -> List[Dict]:
    """Extract financial transactions from entity descriptions."""
    transactions = []

    # Pattern: $XXX million/billion
    amount_pattern = r'\$(\d+(?:\.\d+)?)\s*(million|billion|M|B|m|b)'
    matches = re.findall(amount_pattern, description or "", re.IGNORECASE)

    for amount, unit in matches:
        multiplier = 1_000_000 if unit.lower() in ['million', 'm'] else 1_000_000_000
        value = float(amount) * multiplier
        transactions.append({"amount_usd": value})

    return transactions


def extract_dates(description: str) -> List[Tuple[str, str]]:
    """Extract dates and events from description."""
    events = []

    # Pattern: year mentions
    year_pattern = r'\b(19[5-9]\d|20[0-2]\d)\b'
    years = re.findall(year_pattern, description or "")

    for year in set(years):
        events.append((year, "mentioned"))

    return events


def extract_location_data(entity: Dict) -> Optional[Dict]:
    """Extract location data from entity."""
    description = (entity.get("description") or "").lower()
    name = entity.get("canonical_name", "")

    # Known locations with coordinates
    known_locations = {
        "little st. james": {"lat": 18.2969, "lng": -64.8256, "country": "US Virgin Islands"},
        "great st. james": {"lat": 18.3178, "lng": -64.8547, "country": "US Virgin Islands"},
        "9 east 71st street": {"lat": 40.7715, "lng": -73.9650, "country": "USA", "city": "New York"},
        "358 el brillo way": {"lat": 26.6885, "lng": -80.0384, "country": "USA", "city": "Palm Beach"},
        "zorro ranch": {"lat": 35.0844, "lng": -106.6504, "country": "USA", "city": "Stanley, NM"},
        "paris apartment": {"lat": 48.8566, "lng": 2.3522, "country": "France", "city": "Paris"},
    }

    for loc_name, coords in known_locations.items():
        if loc_name in name.lower() or loc_name in description:
            return {
                "name": name,
                "location_type": "property",
                **coords
            }

    # Jurisdiction detection
    jurisdictions = {
        "virgin islands": {"country": "US Virgin Islands"},
        "british virgin islands": {"country": "British Virgin Islands"},
        "bvi": {"country": "British Virgin Islands"},
        "delaware": {"country": "USA", "state": "Delaware"},
        "new york": {"country": "USA", "state": "New York"},
        "florida": {"country": "USA", "state": "Florida"},
        "new mexico": {"country": "USA", "state": "New Mexico"},
    }

    for jur_name, jur_data in jurisdictions.items():
        if jur_name in description:
            return {
                "name": name,
                "location_type": "jurisdiction",
                **jur_data
            }

    return None


def export_network_graph(client: Client, entities: List[Dict]):
    """Export network graph data (nodes and edges)."""
    print("\n[1/5] Exporting Network Graph datasets...")

    # Nodes
    nodes = []
    entity_ids = {}

    for entity in entities:
        entity_id = entity["id"]
        entity_ids[entity["canonical_name"]] = entity_id

        nodes.append({
            "entity_id": entity_id,
            "name": entity["canonical_name"],
            "entity_type": entity["entity_type"],
            "role_category": categorize_entity(
                entity["entity_type"],
                entity["canonical_name"],
                entity.get("description", "")
            ),
            "mention_count": entity.get("mention_count", 0),
            "finding_count": entity.get("finding_count", 0),
            "description": (entity.get("description") or "")[:500],
            "aliases": "|".join(entity.get("aliases") or []),
            "is_verified": entity.get("is_verified", False),
        })

    write_csv("nodes.csv", nodes, [
        "entity_id", "name", "entity_type", "role_category",
        "mention_count", "finding_count", "description", "aliases", "is_verified"
    ])

    # Edges - from claim_entities (entities linked via same claims)
    print("  Fetching claim-entity links...")
    claim_entities_result = client.table("claim_entities").select("*").execute()

    # Group entities by claim
    claims_to_entities = defaultdict(list)
    for ce in claim_entities_result.data:
        claims_to_entities[ce["claim_id"]].append({
            "entity_id": ce["entity_id"],
            "role": ce.get("role", "mentioned")
        })

    # Create edges between entities that share claims
    edge_counts = defaultdict(lambda: {"count": 0, "roles": set()})

    for claim_id, entities_in_claim in claims_to_entities.items():
        for i, e1 in enumerate(entities_in_claim):
            for e2 in entities_in_claim[i+1:]:
                key = tuple(sorted([e1["entity_id"], e2["entity_id"]]))
                edge_counts[key]["count"] += 1
                edge_counts[key]["roles"].add(e1.get("role", ""))
                edge_counts[key]["roles"].add(e2.get("role", ""))

    edges = []
    for (source_id, target_id), data in edge_counts.items():
        edges.append({
            "source_id": source_id,
            "target_id": target_id,
            "relationship_type": "co_mentioned",
            "strength": min(data["count"] / 10.0, 1.0),  # Normalize
            "co_mention_count": data["count"],
            "roles": "|".join(filter(None, data["roles"])),
        })

    # Also fetch claim_relationships for explicit relationships
    print("  Fetching claim relationships...")
    claim_rels = client.table("claim_relationships").select("*").execute()

    for rel in claim_rels.data:
        edges.append({
            "source_id": rel["source_claim_id"],
            "target_id": rel["target_claim_id"],
            "relationship_type": rel.get("relationship_type", "related"),
            "strength": rel.get("strength", 0.5),
            "co_mention_count": 1,
            "roles": rel.get("description", ""),
        })

    write_csv("edges.csv", edges, [
        "source_id", "target_id", "relationship_type", "strength",
        "co_mention_count", "roles"
    ])

    return entity_ids


def export_financial_flow(client: Client, entities: List[Dict]):
    """Export financial flow data."""
    print("\n[2/5] Exporting Financial Flow datasets...")

    transactions = []
    entity_totals = defaultdict(lambda: {"inflow": 0, "outflow": 0, "count": 0})
    time_series = defaultdict(lambda: {"total_flow": 0, "count": 0})

    # Known major transactions (from our research)
    known_transactions = [
        {"source": "Leslie Wexner", "target": "Jeffrey Epstein", "amount": 77_000_000, "type": "gift", "year": "1991-2007", "purpose": "NYC Mansion + POA", "evidence": "high"},
        {"source": "Leslie Wexner Trusts", "target": "Jeffrey Epstein", "amount": 1_300_000_000, "type": "transfer", "year": "1991-2006", "purpose": "Stock sales under Epstein control", "evidence": "medium"},
        {"source": "Leon Black", "target": "Jeffrey Epstein", "amount": 170_000_000, "type": "fee", "year": "2012-2017", "purpose": "Claimed tax advice", "evidence": "high"},
        {"source": "Jeffrey Epstein", "target": "Carbyne", "amount": 1_500_000, "type": "investment", "year": "2015-2016", "purpose": "Israeli surveillance tech", "evidence": "high"},
        {"source": "Southern Trust", "target": "Rothschild Bank", "amount": 25_000_000, "type": "transfer", "year": "2015", "purpose": "Barak cyber weapons funding", "evidence": "high"},
        {"source": "Steven Hoffenberg", "target": "Jeffrey Epstein", "amount": 25_000, "type": "salary", "year": "1987-1993", "purpose": "Monthly salary + $2M loan", "evidence": "high"},
        {"source": "JPMorgan", "target": "Epstein Entities", "amount": 1_000_000_000, "type": "transfer", "year": "2003-2019", "purpose": "Banking services (SARs filed)", "evidence": "high"},
        {"source": "Deutsche Bank", "target": "Epstein Entities", "amount": 150_000_000, "type": "transfer", "year": "2013-2018", "purpose": "Banking after JPM exit", "evidence": "high"},
        {"source": "Prince Andrew", "target": "Virginia Giuffre", "amount": 12_000_000, "type": "settlement", "year": "2022", "purpose": "Civil settlement", "evidence": "high"},
        {"source": "Epstein Estate", "target": "Victims Compensation", "amount": 125_000_000, "type": "settlement", "year": "2020-2021", "purpose": "Victim compensation fund", "evidence": "high"},
    ]

    for i, tx in enumerate(known_transactions):
        transactions.append({
            "id": f"tx_{i+1:04d}",
            "source_entity": tx["source"],
            "target_entity": tx["target"],
            "amount_usd": tx["amount"],
            "transaction_type": tx["type"],
            "date": tx["year"],
            "purpose": tx["purpose"],
            "evidence_strength": tx["evidence"],
        })

        entity_totals[tx["source"]]["outflow"] += tx["amount"]
        entity_totals[tx["source"]]["count"] += 1
        entity_totals[tx["target"]]["inflow"] += tx["amount"]
        entity_totals[tx["target"]]["count"] += 1

        # Extract year for time series
        year_match = re.search(r'\d{4}', tx["year"])
        if year_match:
            year = year_match.group()
            time_series[year]["total_flow"] += tx["amount"]
            time_series[year]["count"] += 1

    # Extract additional financial mentions from entity descriptions
    for entity in entities:
        desc = entity.get("description") or ""
        name = entity["canonical_name"]

        # Find dollar amounts
        for match in re.finditer(r'\$(\d+(?:\.\d+)?)\s*(million|billion|M|B|m|b)?', desc, re.IGNORECASE):
            amount = float(match.group(1))
            unit = match.group(2)
            if unit:
                if unit.lower() in ['billion', 'b']:
                    amount *= 1_000_000_000
                elif unit.lower() in ['million', 'm']:
                    amount *= 1_000_000

            if amount >= 100_000:  # Only track significant amounts
                transactions.append({
                    "id": f"tx_extracted_{len(transactions)+1:04d}",
                    "source_entity": "Unknown",
                    "target_entity": name,
                    "amount_usd": amount,
                    "transaction_type": "mentioned",
                    "date": "unknown",
                    "purpose": "Extracted from description",
                    "evidence_strength": "low",
                })

    write_csv("transactions.csv", transactions, [
        "id", "source_entity", "target_entity", "amount_usd",
        "transaction_type", "date", "purpose", "evidence_strength"
    ])

    # Entity totals
    totals = []
    for entity_name, data in entity_totals.items():
        totals.append({
            "entity_name": entity_name,
            "total_inflow": data["inflow"],
            "total_outflow": data["outflow"],
            "net_flow": data["inflow"] - data["outflow"],
            "transaction_count": data["count"],
        })

    write_csv("entity_totals.csv", totals, [
        "entity_name", "total_inflow", "total_outflow", "net_flow", "transaction_count"
    ])

    # Time series
    ts_data = []
    for year in sorted(time_series.keys()):
        ts_data.append({
            "year": year,
            "total_flow": time_series[year]["total_flow"],
            "transaction_count": time_series[year]["count"],
            "avg_amount": time_series[year]["total_flow"] / time_series[year]["count"] if time_series[year]["count"] > 0 else 0,
        })

    write_csv("time_series.csv", ts_data, [
        "year", "total_flow", "transaction_count", "avg_amount"
    ])


def export_timeline(client: Client, entities: List[Dict], claims: List[Dict]):
    """Export timeline data."""
    print("\n[3/5] Exporting Timeline datasets...")

    events = []
    parallel_tracks = defaultdict(lambda: {
        "epstein_activity": "",
        "financial_event": "",
        "intel_event": "",
        "legal_response": ""
    })

    # Extract events from claims with dates
    for claim in claims:
        event_date = claim.get("event_date")
        if not event_date:
            # Try to extract from content
            year_match = re.search(r'\b(19[5-9]\d|20[0-2]\d)\b', claim.get("content", ""))
            if year_match:
                event_date = year_match.group()

        if event_date:
            events.append({
                "id": claim["id"],
                "event_date": str(event_date),
                "event_type": claim.get("claim_type", "claim"),
                "title": (claim.get("summary") or claim.get("content", "")[:100]),
                "description": claim.get("content", "")[:500],
                "confidence_score": claim.get("confidence_score", 0.5),
                "tags": "|".join(claim.get("tags") or []),
            })

    # Known major events for parallel tracks
    major_events = [
        {"year": "1953", "epstein": "Jeffrey Epstein born (Brooklyn)", "financial": "", "intel": "", "legal": ""},
        {"year": "1973", "epstein": "Hired at Dalton School by Donald Barr (OSS)", "financial": "", "intel": "Donald Barr: OSS veteran", "legal": ""},
        {"year": "1976", "epstein": "Joins Bear Stearns", "financial": "", "intel": "", "legal": ""},
        {"year": "1981", "epstein": "Leaves Bear Stearns", "financial": "Unknown wealth source begins", "intel": "", "legal": ""},
        {"year": "1987", "epstein": "Joins Towers Financial with Hoffenberg", "financial": "$25K/month + loans", "intel": "", "legal": ""},
        {"year": "1991", "epstein": "Enters Wexner orbit; meets Ghislaine", "financial": "Wexner grants unlimited POA", "intel": "Robert Maxwell dies (Nov)", "legal": ""},
        {"year": "1993", "epstein": "Towers Financial collapses", "financial": "$460M Ponzi exposed", "intel": "", "legal": "Hoffenberg charged; Epstein escapes"},
        {"year": "1996", "epstein": "Receives NYC mansion from Wexner", "financial": "$77M property transfer", "intel": "", "legal": ""},
        {"year": "2005", "epstein": "Palm Beach investigation begins", "financial": "", "intel": "", "legal": "40+ victims identified"},
        {"year": "2008", "epstein": "Pleads guilty to state charges", "financial": "", "intel": "Acosta: 'belonged to intelligence'", "legal": "NPA signed; 13mo work release"},
        {"year": "2012", "epstein": "Leon Black relationship intensifies", "financial": "$170M payments begin", "intel": "", "legal": ""},
        {"year": "2015", "epstein": "Invests in Carbyne", "financial": "$1.5M+ to surveillance tech", "intel": "Carbyne founded; Unit 8200 staff", "legal": ""},
        {"year": "2019", "epstein": "SDNY arrest (Jul 6); Death (Aug 10)", "financial": "JPMorgan files $1B+ SAR", "intel": "Israeli passport found", "legal": "Documents unsealed Aug 9"},
        {"year": "2021", "epstein": "", "financial": "$125M victim fund", "intel": "", "legal": "Ghislaine Maxwell convicted"},
        {"year": "2022", "epstein": "", "financial": "JPMorgan $290M settlement", "intel": "", "legal": "Maxwell: 20 years; Brunel dies"},
    ]

    for event in major_events:
        parallel_tracks[event["year"]] = {
            "year": event["year"],
            "epstein_activity": event["epstein"],
            "financial_event": event["financial"],
            "intel_event": event["intel"],
            "legal_response": event["legal"],
        }

    write_csv("events.csv", events, [
        "id", "event_date", "event_type", "title", "description",
        "confidence_score", "tags"
    ])

    write_csv("parallel_tracks.csv", list(parallel_tracks.values()), [
        "year", "epstein_activity", "financial_event", "intel_event", "legal_response"
    ])


def export_geographic(client: Client, entities: List[Dict]):
    """Export geographic data."""
    print("\n[4/5] Exporting Geographic datasets...")

    locations = []
    jurisdictions = defaultdict(lambda: {"entity_count": 0, "shell_count": 0, "total_value": 0})

    # Known properties
    properties = [
        {"name": "9 East 71st Street", "type": "mansion", "city": "New York", "state": "NY", "country": "USA", "lat": 40.7715, "lng": -73.9650, "value": 77000000, "owner": "Jeffrey Epstein", "purpose": "Primary residence; surveillance documented"},
        {"name": "358 El Brillo Way", "type": "mansion", "city": "Palm Beach", "state": "FL", "country": "USA", "lat": 26.6885, "lng": -80.0384, "value": 12000000, "owner": "Jeffrey Epstein", "purpose": "Trafficking location; 40+ victims"},
        {"name": "Little St. James Island", "type": "island", "city": "St. Thomas", "state": "USVI", "country": "US Virgin Islands", "lat": 18.2969, "lng": -64.8256, "value": 63000000, "owner": "Jeffrey Epstein", "purpose": "Private island; trafficking location"},
        {"name": "Great St. James Island", "type": "island", "city": "St. Thomas", "state": "USVI", "country": "US Virgin Islands", "lat": 18.3178, "lng": -64.8547, "value": 22000000, "owner": "Jeffrey Epstein", "purpose": "Second island purchase"},
        {"name": "Zorro Ranch", "type": "ranch", "city": "Stanley", "state": "NM", "country": "USA", "lat": 35.0844, "lng": -106.6504, "value": 18000000, "owner": "Jeffrey Epstein", "purpose": "8,000 acre ranch; DNA project plans"},
        {"name": "Paris Apartment", "type": "apartment", "city": "Paris", "state": "", "country": "France", "lat": 48.8624, "lng": 2.3308, "value": 8700000, "owner": "Jeffrey Epstein", "purpose": "European base; Brunel connection"},
    ]

    for prop in properties:
        locations.append({
            "id": f"loc_{len(locations)+1:04d}",
            "name": prop["name"],
            "location_type": prop["type"],
            "address": prop["name"],
            "city": prop["city"],
            "state": prop["state"],
            "country": prop["country"],
            "lat": prop["lat"],
            "lng": prop["lng"],
            "owner": prop["owner"],
            "purpose": prop["purpose"],
            "value_usd": prop["value"],
        })

        jurisdictions[prop["country"]]["entity_count"] += 1
        jurisdictions[prop["country"]]["total_value"] += prop["value"]

    # Extract locations from entities
    for entity in entities:
        loc_data = extract_location_data(entity)
        if loc_data:
            locations.append({
                "id": f"loc_{len(locations)+1:04d}",
                **loc_data,
                "owner": entity["canonical_name"],
                "purpose": (entity.get("description") or "")[:200],
                "value_usd": 0,
            })

            country = loc_data.get("country", "Unknown")
            jurisdictions[country]["entity_count"] += 1

            if "shell" in entity.get("entity_type", "").lower():
                jurisdictions[country]["shell_count"] += 1

    write_csv("locations.csv", locations, [
        "id", "name", "location_type", "address", "city", "state", "country",
        "lat", "lng", "owner", "purpose", "value_usd"
    ])

    # Jurisdictions with secrecy scores
    secrecy_scores = {
        "British Virgin Islands": 0.9,
        "US Virgin Islands": 0.7,
        "Switzerland": 0.8,
        "Delaware": 0.6,
        "Panama": 0.85,
        "Cayman Islands": 0.9,
        "Luxembourg": 0.7,
    }

    jur_data = []
    for jur_name, data in jurisdictions.items():
        jur_data.append({
            "jurisdiction": jur_name,
            "entity_count": data["entity_count"],
            "shell_company_count": data["shell_count"],
            "total_value": data["total_value"],
            "secrecy_score": secrecy_scores.get(jur_name, 0.3),
        })

    write_csv("jurisdictions.csv", jur_data, [
        "jurisdiction", "entity_count", "shell_company_count", "total_value", "secrecy_score"
    ])


def export_evidence_matrix(client: Client, claims: List[Dict], entities: List[Dict]):
    """Export evidence matrix data."""
    print("\n[5/5] Exporting Evidence Matrix datasets...")

    # Claims data
    claims_data = []
    topic_stats = defaultdict(lambda: {"count": 0, "total_confidence": 0, "unverified": 0})

    for claim in claims:
        claim_type = claim.get("claim_type", "unknown")
        confidence = claim.get("confidence_score", 0.5)
        verification = claim.get("verification_status", "unverified")

        claims_data.append({
            "id": claim["id"],
            "claim_type": claim_type,
            "summary": (claim.get("summary") or claim.get("content", "")[:200]),
            "content": claim.get("content", "")[:500],
            "confidence_score": confidence,
            "verification_status": verification,
            "event_date": claim.get("event_date", ""),
            "tags": "|".join(claim.get("tags") or []),
            "temporal_context": claim.get("temporal_context", ""),
        })

        topic_stats[claim_type]["count"] += 1
        topic_stats[claim_type]["total_confidence"] += confidence
        if verification == "unverified":
            topic_stats[claim_type]["unverified"] += 1

    write_csv("claims.csv", claims_data, [
        "id", "claim_type", "summary", "content", "confidence_score",
        "verification_status", "event_date", "tags", "temporal_context"
    ])

    # Evidence gaps
    gaps = []
    for topic, stats in topic_stats.items():
        avg_conf = stats["total_confidence"] / stats["count"] if stats["count"] > 0 else 0
        unverified_ratio = stats["unverified"] / stats["count"] if stats["count"] > 0 else 0
        priority = (1 - avg_conf) * 0.5 + unverified_ratio * 0.5  # Higher = needs more investigation

        gaps.append({
            "topic": topic,
            "claims_count": stats["count"],
            "avg_confidence": round(avg_conf, 3),
            "unverified_count": stats["unverified"],
            "unverified_ratio": round(unverified_ratio, 3),
            "investigation_priority": round(priority, 3),
        })

    write_csv("evidence_gaps.csv", gaps, [
        "topic", "claims_count", "avg_confidence", "unverified_count",
        "unverified_ratio", "investigation_priority"
    ])

    # Entity type distribution
    entity_types = defaultdict(lambda: {"count": 0, "total_mentions": 0, "verified": 0})
    for entity in entities:
        etype = entity.get("entity_type", "unknown")
        entity_types[etype]["count"] += 1
        entity_types[etype]["total_mentions"] += entity.get("mention_count", 0)
        if entity.get("is_verified"):
            entity_types[etype]["verified"] += 1

    entity_stats = []
    for etype, stats in entity_types.items():
        entity_stats.append({
            "entity_type": etype,
            "entity_count": stats["count"],
            "total_mentions": stats["total_mentions"],
            "verified_count": stats["verified"],
            "avg_mentions": round(stats["total_mentions"] / stats["count"], 2) if stats["count"] > 0 else 0,
        })

    write_csv("entity_types.csv", entity_stats, [
        "entity_type", "entity_count", "total_mentions", "verified_count", "avg_mentions"
    ])


def fetch_all_paginated(client: Client, table: str, filters: Dict = None, page_size: int = 1000) -> List[Dict]:
    """Fetch all records from a table with pagination."""
    all_data = []
    offset = 0

    while True:
        query = client.table(table).select("*")

        # Apply filters
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        result = query.range(offset, offset + page_size - 1).execute()

        if not result.data:
            break

        all_data.extend(result.data)

        if len(result.data) < page_size:
            break

        offset += page_size

    return all_data


def main():
    """Main export function."""
    print("=" * 60)
    print("Epstein Investigation - Hex Dataset Export")
    print("=" * 60)

    ensure_output_dir()

    client = get_supabase_client()

    # Fetch all entities (paginated)
    print("\nFetching entities from database...")
    entities = fetch_all_paginated(client, "knowledge_entities")
    print(f"  Found {len(entities)} entities")

    # Fetch all claims (paginated)
    print("Fetching claims from database...")
    claims = fetch_all_paginated(client, "knowledge_claims", {"is_current": True})
    print(f"  Found {len(claims)} claims")

    # Export each dataset group
    entity_ids = export_network_graph(client, entities)
    export_financial_flow(client, entities)
    export_timeline(client, entities, claims)
    export_geographic(client, entities)
    export_evidence_matrix(client, claims, entities)

    print("\n" + "=" * 60)
    print("Export complete!")
    print(f"CSV files saved to: {OUTPUT_DIR}")
    print("=" * 60)

    # List all files
    print("\nGenerated files:")
    for f in sorted(OUTPUT_DIR.glob("*.csv")):
        size = f.stat().st_size
        print(f"  {f.name}: {size:,} bytes")


if __name__ == "__main__":
    main()
