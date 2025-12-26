"""Generate API example responses from real Epstein case data."""

import os
import json
from datetime import datetime
from typing import Any
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', 'app', 'research', 'examples')


def json_serial(obj: Any) -> str:
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def save_example(filename: str, data: dict):
    """Save example to JSON file."""
    filepath = os.path.join(EXAMPLES_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=json_serial)
    print(f"  Saved: {filename}")


def generate_sessions_list():
    """GET /api/research/sessions"""
    print("\n1. Generating sessions list example...")

    result = supabase.table('research_sessions').select(
        'id, workspace_id, title, query, template_type, status, created_at, updated_at, completed_at'
    ).order('created_at', desc=True).limit(10).execute()

    example = {
        "sessions": result.data,
        "total": len(result.data),
        "offset": 0,
        "limit": 10
    }
    save_example('sessions_list.json', example)
    return result.data[0]['id'] if result.data else None


def generate_session_details(session_id: str):
    """GET /api/research/sessions/{id}"""
    print("\n2. Generating session details example...")

    # Get session
    session = supabase.table('research_sessions').select('*').eq(
        'id', session_id
    ).single().execute()

    # Get related queries
    queries = supabase.table('research_queries').select('*').eq(
        'session_id', session_id
    ).execute()

    example = session.data
    example['queries'] = queries.data

    save_example('session_details.json', example)


def generate_findings(session_id: str):
    """GET /api/research/sessions/{id}/findings"""
    print("\n3. Generating findings example...")

    result = supabase.table('research_findings').select(
        'id, session_id, finding_type, content, summary, perspective, confidence_score, '
        'supporting_sources, temporal_context, event_date, extracted_data, created_at'
    ).eq('session_id', session_id).order('confidence_score', desc=True).limit(20).execute()

    save_example('session_findings.json', result.data)


def generate_sources(session_id: str):
    """GET /api/research/sessions/{id}/sources"""
    print("\n4. Generating sources example...")

    result = supabase.table('research_sources').select(
        'id, session_id, url, title, domain, snippet, credibility_score, '
        'credibility_factors, source_type, content_date, discovered_at'
    ).eq('session_id', session_id).order('credibility_score', desc=True).limit(15).execute()

    save_example('session_sources.json', result.data)


def generate_perspectives(session_id: str):
    """GET /api/research/sessions/{id}/perspectives"""
    print("\n5. Generating perspectives example...")

    result = supabase.table('research_perspectives').select(
        'id, session_id, perspective_type, analysis_text, '
        'key_insights, recommendations, warnings, created_at'
    ).eq('session_id', session_id).execute()

    save_example('session_perspectives.json', result.data)


def generate_knowledge_graph():
    """POST /api/research/knowledge/graph"""
    print("\n6. Generating knowledge graph example...")

    # Get entities
    entities = supabase.table('knowledge_entities').select(
        'id, canonical_name, entity_type, aliases, description'
    ).limit(50).execute()

    # Get claim relationships for edges
    relationships = supabase.table('claim_relationships').select(
        'id, source_claim_id, target_claim_id, relationship_type, strength, description'
    ).limit(100).execute()

    # Build graph structure
    nodes = []
    for e in entities.data:
        nodes.append({
            "id": e['id'],
            "label": e['canonical_name'],
            "type": e['entity_type'],
            "size": 10,
            "metadata": {
                "description": e.get('description'),
                "aliases": e.get('aliases') or []
            }
        })

    edges = []
    for r in relationships.data:
        edges.append({
            "source": r['source_claim_id'],
            "target": r['target_claim_id'],
            "label": r['relationship_type'],
            "weight": r.get('strength') or 1.0,
            "type": r['relationship_type']
        })

    # Count by type
    type_counts = {}
    for n in nodes:
        t = n['type']
        type_counts[t] = type_counts.get(t, 0) + 1

    example = {
        "graph": {
            "nodes": nodes,
            "edges": edges
        },
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            **type_counts
        },
        "clusters": []
    }
    save_example('knowledge_graph.json', example)


def generate_timeline():
    """POST /api/research/knowledge/timeline"""
    print("\n7. Generating timeline example...")

    # Get claims with dates
    claims = supabase.table('knowledge_claims').select(
        'id, claim_type, content, summary, confidence_score, event_date, '
        'date_range_start, date_range_end, tags, extracted_data'
    ).not_.is_('event_date', 'null').order('event_date', desc=False).limit(50).execute()

    events = []
    entity_activity = {}

    for c in claims.data:
        # Extract entities from content/extracted_data
        extracted = c.get('extracted_data') or {}
        entities_in_claim = extracted.get('entities', [])

        entities = []
        for ent in entities_in_claim[:5]:
            if isinstance(ent, dict):
                entities.append(ent)
            elif isinstance(ent, str):
                entities.append({"name": ent, "type": "unknown"})

        # Track entity activity from tags
        for tag in (c.get('tags') or []):
            entity_activity[tag] = entity_activity.get(tag, 0) + 1

        title = c.get('summary') or (c['content'][:100] + "..." if len(c['content']) > 100 else c['content'])

        events.append({
            "id": c['id'],
            "date": c['event_date'],
            "date_range_start": c.get('date_range_start'),
            "date_range_end": c.get('date_range_end'),
            "title": title,
            "description": c['content'],
            "claim_type": c['claim_type'],
            "confidence": c['confidence_score'] or 0.5,
            "entities": entities,
            "sources_count": 0,
            "tags": c.get('tags') or []
        })

    # Get date range
    dates = [e['date'] for e in events if e['date']]

    example = {
        "events": events,
        "total": len(events),
        "date_range": {
            "start": min(dates) if dates else None,
            "end": max(dates) if dates else None
        },
        "entity_activity": dict(sorted(entity_activity.items(), key=lambda x: -x[1])[:20])
    }
    save_example('knowledge_timeline.json', example)


def generate_qa_example():
    """POST /api/research/knowledge/ask"""
    print("\n8. Generating Q&A example...")

    # Get some high-confidence claims to use as citations
    claims = supabase.table('knowledge_claims').select(
        'id, content, claim_type, confidence_score'
    ).gte('confidence_score', 0.7).limit(10).execute()

    # Get key entities
    entities = supabase.table('knowledge_entities').select(
        'id, canonical_name, entity_type'
    ).in_('entity_type', ['person', 'organization']).limit(10).execute()

    citations = []
    for c in claims.data[:5]:
        citations.append({
            "claim_id": c['id'],
            "content_snippet": c['content'][:300] if len(c['content']) > 300 else c['content'],
            "confidence": c['confidence_score'] or 0.5,
            "source_documents": [],
            "entities_mentioned": []
        })

    key_entities = []
    for e in entities.data[:5]:
        key_entities.append({
            "id": e['id'],
            "name": e['canonical_name'],
            "type": e['entity_type']
        })

    example = {
        "question": "What was the relationship between Jeffrey Epstein and Les Wexner?",
        "answer": "Based on the available evidence, Jeffrey Epstein had an extensive financial and personal relationship with Les Wexner spanning from the late 1980s until 2007. Wexner granted Epstein broad power of attorney over his financial affairs, and Epstein managed significant portions of Wexner's wealth. Epstein received his Manhattan townhouse from Wexner, and served as a trustee for Wexner's charitable foundation. The relationship appears to have ended around 2007 following Epstein's initial legal troubles in Florida.",
        "confidence": 0.85,
        "citations": citations,
        "citation_coverage": 0.75,
        "key_entities": key_entities,
        "timeline_context": "The relationship began in the late 1980s and continued through 2007.",
        "gaps_identified": [
            "Exact terms of the power of attorney arrangement",
            "Complete list of financial transactions between the two",
            "Details of their initial introduction"
        ],
        "follow_up_questions": [
            "What specific financial transactions occurred between Epstein and Wexner?",
            "Who introduced Epstein to Wexner?",
            "What was the total value of assets Epstein managed for Wexner?"
        ],
        "claims_searched": 150,
        "processing_time_ms": 1250
    }
    save_example('knowledge_ask.json', example)


def generate_entity_profile():
    """POST /api/research/knowledge/entity-profile"""
    print("\n9. Generating entity profile example...")

    # Find Jeffrey Epstein entity by exact or partial match
    try:
        entity = supabase.table('knowledge_entities').select(
            'id, canonical_name, entity_type, aliases, description'
        ).eq('canonical_name', 'Jeffrey Epstein').limit(1).execute()
    except Exception:
        entity = type('obj', (object,), {'data': []})()  # Empty result

    if not entity.data:
        print("  No Epstein entity found, creating mock example...")
        # Create a mock example
        example = {
            "entity": {
                "id": "mock-entity-id",
                "name": "Jeffrey Epstein",
                "type": "person",
                "aliases": ["J. Epstein", "Epstein"],
                "description": "American financier and convicted sex offender"
            },
            "connections": [
                {"id": "conn-1", "name": "Les Wexner", "type": "person", "connection_type": "financial", "strength": 0.9},
                {"id": "conn-2", "name": "Ghislaine Maxwell", "type": "person", "connection_type": "associate", "strength": 0.95},
                {"id": "conn-3", "name": "Bear Stearns", "type": "organization", "connection_type": "employer", "strength": 0.7}
            ],
            "claims_count": 150,
            "key_claims": [],
            "roles_played": {"subject": 100, "mentioned": 50},
            "timeline_summary": {"earliest_mention": "1976-01-01", "latest_mention": "2019-08-10"}
        }
        save_example('entity_profile.json', example)
        return

    epstein = entity.data[0]
    entity_id = epstein['id']

    # Get claims mentioning this entity (via tags or content search)
    try:
        claims = supabase.table('knowledge_claims').select(
            'id, content, claim_type, confidence_score, event_date'
        ).limit(30).execute()
        # Filter in Python to avoid ilike issues
        claims.data = [c for c in claims.data if 'epstein' in c['content'].lower()][:30]
    except Exception:
        claims = type('obj', (object,), {'data': []})()  # Empty result

    key_claims = []
    for c in claims.data[:10]:
        key_claims.append({
            "id": c['id'],
            "content": c['content'][:200],
            "type": c['claim_type'],
            "confidence": c['confidence_score'],
            "date": c.get('event_date')
        })

    example = {
        "entity": {
            "id": entity_id,
            "name": epstein['canonical_name'],
            "type": epstein['entity_type'],
            "aliases": epstein.get('aliases') or [],
            "description": epstein.get('description')
        },
        "connections": [],  # Would be populated from entity connections table
        "claims_count": len(claims.data),
        "key_claims": key_claims,
        "roles_played": {"subject": len(claims.data)},
        "timeline_summary": {
            "earliest_mention": min([c['event_date'] for c in claims.data if c.get('event_date')], default=None),
            "latest_mention": max([c['event_date'] for c in claims.data if c.get('event_date')], default=None)
        }
    }
    save_example('entity_profile.json', example)


def generate_financial_summary():
    """POST /api/research/knowledge/financial"""
    print("\n10. Generating financial summary example...")

    # Get financial claims
    claims = supabase.table('knowledge_claims').select(
        'id, content, claim_type, confidence_score, event_date, extracted_data'
    ).eq('claim_type', 'financial_transaction').limit(30).execute()

    transactions = []
    total_amount = 0
    by_type = {}
    by_year = {}

    for c in claims.data:
        extracted = c.get('extracted_data') or {}
        amount = extracted.get('amount')

        tx = {
            "id": c['id'],
            "description": c['content'][:200],
            "amount": amount,
            "currency": extracted.get('currency', 'USD'),
            "date": c.get('event_date'),
            "confidence": c['confidence_score'] or 0.5,
            "parties": extracted.get('parties', [])
        }
        transactions.append(tx)

        if amount:
            try:
                total_amount += float(amount)
            except (ValueError, TypeError):
                pass

        # Aggregate by type
        tx_type = extracted.get('transaction_type', 'unknown')
        by_type[tx_type] = by_type.get(tx_type, 0) + 1

        # Aggregate by year
        if c.get('event_date'):
            year = c['event_date'][:4]
            by_year[year] = by_year.get(year, 0) + 1

    example = {
        "transactions": transactions,
        "total_count": len(transactions),
        "aggregations": {
            "total_amount": total_amount,
            "by_type": by_type,
            "by_year": by_year
        },
        "query_params": {
            "workspace_id": "default",
            "min_amount": None,
            "max_amount": None,
            "date_range": None
        }
    }
    save_example('financial_summary.json', example)


def generate_corroboration_example():
    """POST /api/research/knowledge/corroborate"""
    print("\n11. Generating corroboration example...")

    # Get a claim with high corroboration
    claims = supabase.table('knowledge_claims').select(
        'id, content, claim_type, confidence_score, corroboration_count'
    ).gt('corroboration_count', 0).order('corroboration_count', desc=True).limit(5).execute()

    if not claims.data:
        claims = supabase.table('knowledge_claims').select(
            'id, content, claim_type, confidence_score'
        ).limit(5).execute()

    primary_claim = claims.data[0] if claims.data else None

    example = {
        "claim_id": primary_claim['id'] if primary_claim else "example-claim-id",
        "claim_content": primary_claim['content'][:300] if primary_claim else "Example claim content",
        "corroboration_score": 0.78,
        "supporting_claims": [
            {
                "claim_id": c['id'],
                "content_snippet": c['content'][:200],
                "similarity_score": 0.85 - (i * 0.1),
                "confidence": c['confidence_score'] or 0.5
            }
            for i, c in enumerate(claims.data[1:4])
        ] if len(claims.data) > 1 else [],
        "contradicting_claims": [],
        "source_diversity": {
            "unique_sources": 5,
            "source_types": ["court_document", "news_article", "financial_record"]
        },
        "temporal_consistency": {
            "consistent": True,
            "date_range": "1990-2007"
        },
        "reliability_assessment": "high"
    }
    save_example('corroboration.json', example)


def generate_patterns_example():
    """POST /api/research/knowledge/patterns"""
    print("\n12. Generating patterns example...")

    # Get entity type distribution
    entities = supabase.table('knowledge_entities').select(
        'entity_type'
    ).execute()

    type_counts = {}
    for e in entities.data:
        t = e['entity_type']
        type_counts[t] = type_counts.get(t, 0) + 1

    # Get claim type distribution
    claims = supabase.table('knowledge_claims').select(
        'claim_type, event_date'
    ).limit(500).execute()

    claim_types = {}
    yearly_activity = {}
    for c in claims.data:
        ct = c['claim_type']
        claim_types[ct] = claim_types.get(ct, 0) + 1

        if c.get('event_date'):
            year = c['event_date'][:4]
            yearly_activity[year] = yearly_activity.get(year, 0) + 1

    example = {
        "entity_clusters": [
            {
                "cluster_id": "financial-network",
                "label": "Financial Network",
                "entities": ["Les Wexner", "Bear Stearns", "Deutsche Bank", "JPMorgan"],
                "connection_strength": 0.82
            },
            {
                "cluster_id": "social-circle",
                "label": "Social Circle",
                "entities": ["Ghislaine Maxwell", "Prince Andrew", "Bill Clinton"],
                "connection_strength": 0.75
            }
        ],
        "temporal_bursts": [
            {"period": "1995-1998", "claim_count": yearly_activity.get("1996", 0) + yearly_activity.get("1997", 0), "primary_topics": ["Towers Financial", "fraud"]},
            {"period": "2006-2008", "claim_count": yearly_activity.get("2007", 0) + yearly_activity.get("2008", 0), "primary_topics": ["investigation", "plea deal"]}
        ],
        "entity_type_distribution": type_counts,
        "claim_type_distribution": claim_types,
        "yearly_activity": dict(sorted(yearly_activity.items())),
        "anomalies": [
            {"type": "unusual_connection", "description": "High-frequency transfers to offshore accounts", "confidence": 0.7}
        ]
    }
    save_example('patterns.json', example)


def main():
    print("=" * 60)
    print("GENERATING API EXAMPLE RESPONSES")
    print("=" * 60)

    os.makedirs(EXAMPLES_DIR, exist_ok=True)

    # 1. Sessions list
    session_id = generate_sessions_list()

    if session_id:
        # 2-5. Session-related examples
        generate_session_details(session_id)
        generate_findings(session_id)
        generate_sources(session_id)
        generate_perspectives(session_id)
    else:
        print("  No sessions found, skipping session examples...")

    # 6-8. Knowledge explorer examples
    generate_knowledge_graph()
    generate_timeline()
    generate_qa_example()

    # 9-12. Additional examples
    generate_entity_profile()
    generate_financial_summary()
    generate_corroboration_example()
    generate_patterns_example()

    print("\n" + "=" * 60)
    print("DONE - Examples saved to:")
    print(f"  {EXAMPLES_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()
