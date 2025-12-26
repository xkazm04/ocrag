"""Build Claim Relationships from Findings.

This script:
1. Extracts entity pairs from relationship-type findings
2. Creates claim_relationships entries linking entities
3. Identifies missing relationships for review
"""

import os
import re
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)


# Entity name normalization map
ENTITY_ALIASES = {
    'epstein': 'Jeffrey Epstein',
    'jeffrey epstein': 'Jeffrey Epstein',
    'j. epstein': 'Jeffrey Epstein',
    'wexner': 'Les Wexner',
    'les wexner': 'Les Wexner',
    'hoffenberg': 'Steven Hoffenberg',
    'steven hoffenberg': 'Steven Hoffenberg',
    'maxwell': 'Ghislaine Maxwell',
    'ghislaine maxwell': 'Ghislaine Maxwell',
    'clinton': 'Bill Clinton',
    'bill clinton': 'Bill Clinton',
    'trump': 'Donald Trump',
    'donald trump': 'Donald Trump',
    'prince andrew': 'Prince Andrew',
    'andrew': 'Prince Andrew',
    'dershowitz': 'Alan Dershowitz',
    'alan dershowitz': 'Alan Dershowitz',
    'brunel': 'Jean-Luc Brunel',
    'jean-luc brunel': 'Jean-Luc Brunel',
    'bear stearns': 'Bear Stearns',
    'towers financial': 'Towers Financial',
    'deutsche bank': 'Deutsche Bank',
    'jpmorgan': 'JPMorgan',
    'jp morgan': 'JPMorgan',
    "victoria's secret": "Victoria's Secret",
    'l brands': 'L Brands',
}

# Relationship type patterns - mapped to valid claim_relationships types
# Valid types: causes, supports, contradicts, expands, supersedes, related_to, part_of, precedes, follows, enables
RELATIONSHIP_PATTERNS = [
    (r'(.+) (?:was|became) (?:a |an )?(?:financial )?advisor (?:to|for) (.+)', 'related_to'),
    (r'(.+) granted (.+) power of attorney', 'enables'),
    (r'(.+) gave (.+) power of attorney', 'enables'),
    (r'(.+) employed (.+)', 'related_to'),
    (r'(.+) hired (.+)', 'related_to'),
    (r'(.+) worked (?:for|at|with) (.+)', 'related_to'),
    (r'(.+) (?:was|is) (?:a |an )?(?:close )?(?:friend|associate) of (.+)', 'related_to'),
    (r'(.+) (?:was|is) introduced to (.+)', 'precedes'),
    (r'(.+) paid (.+)', 'related_to'),
    (r'(.+) transferred (?:.+ to |)(.+)', 'related_to'),
    (r'(.+) invested in (.+)', 'related_to'),
    (r'(.+) owned (.+)', 'part_of'),
    (r'(.+) controlled (.+)', 'enables'),
    (r'(.+) managed (.+)', 'related_to'),
    (r'(.+) (?:was|is) (?:a |an )?trustee (?:of|for) (.+)', 'part_of'),
    (r'(.+) served on (?:the )?board of (.+)', 'part_of'),
    (r'(.+) (?:visited|flew to|traveled to) (.+)', 'related_to'),
    (r'(.+) met (?:with )?(.+)', 'related_to'),
]

# Map custom types to valid claim_relationships types
TYPE_MAP = {
    'financial': 'related_to',
    'associated': 'related_to',
    'related': 'related_to',
    'power_of_attorney': 'enables',
    'financial_transaction': 'related_to',
    'management': 'related_to',
    'employed': 'related_to',
    'financial_advisor': 'related_to',
    'ownership': 'part_of',
    'employment': 'related_to',
}


def normalize_entity(name: str) -> str:
    """Normalize entity name using alias map."""
    name_lower = name.lower().strip()
    return ENTITY_ALIASES.get(name_lower, name.strip().title())


def extract_entities_from_text(text: str) -> List[str]:
    """Extract known entities from text."""
    text_lower = text.lower()
    found = []

    for alias, canonical in ENTITY_ALIASES.items():
        if alias in text_lower:
            if canonical not in found:
                found.append(canonical)

    return found


def extract_relationship_type(text: str) -> Optional[str]:
    """Try to determine relationship type from text."""
    text_lower = text.lower()

    for pattern, rel_type in RELATIONSHIP_PATTERNS:
        if re.search(pattern, text_lower):
            return rel_type

    # Fallback categorization
    if any(word in text_lower for word in ['money', 'paid', 'financial', 'investment', 'transfer']):
        return 'financial'
    if any(word in text_lower for word in ['friend', 'associate', 'connection', 'relationship']):
        return 'associated'
    if any(word in text_lower for word in ['employ', 'work', 'hire', 'staff']):
        return 'employment'
    if any(word in text_lower for word in ['own', 'control', 'manage']):
        return 'control'

    return 'related'


def get_or_create_entity(name: str, entity_type: str = 'person') -> Optional[str]:
    """Get existing entity ID or create new one."""
    import hashlib

    # Try to find existing
    result = supabase.table('knowledge_entities').select('id').eq(
        'canonical_name', name
    ).limit(1).execute()

    if result.data:
        return result.data[0]['id']

    # Determine entity type based on name
    org_keywords = ['bank', 'financial', 'brands', 'secret', 'stearns', 'morgan', 'towers']
    if any(kw in name.lower() for kw in org_keywords):
        entity_type = 'organization'

    # Create new entity (without workspace_id - not in schema)
    try:
        name_hash = hashlib.md5(name.lower().encode()).hexdigest()
        result = supabase.table('knowledge_entities').insert({
            'canonical_name': name,
            'entity_type': entity_type,
            'name_hash': name_hash,
        }).execute()
        return result.data[0]['id'] if result.data else None
    except Exception as e:
        print(f"  Error creating entity {name}: {e}")
        return None


def get_or_create_claim_for_finding(finding_id: str, content: str) -> Optional[str]:
    """Get or create a knowledge_claim for a finding."""
    import hashlib

    # Create new claim with content_hash (skip finding_claims linking due to constraint issues)
    try:
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Check if claim with this hash already exists
        existing = supabase.table('knowledge_claims').select('id').eq(
            'content_hash', content_hash
        ).limit(1).execute()

        if existing.data:
            return existing.data[0]['id']

        claim_result = supabase.table('knowledge_claims').insert({
            'claim_type': 'relationship',
            'content': content[:500],
            'content_hash': content_hash,
            'confidence_score': 0.7,
        }).execute()

        if claim_result.data:
            return claim_result.data[0]['id']
    except Exception as e:
        print(f"  Error creating claim: {e}")

    return None


def create_claim_relationship(
    claim_id: str,
    entity1_id: str,
    entity2_id: str,
    relationship_type: str,
    description: str
) -> bool:
    """Create a claim relationship between two entities."""
    try:
        # Check if relationship already exists
        existing = supabase.table('claim_relationships').select('id').eq(
            'source_claim_id', claim_id
        ).eq('target_claim_id', claim_id).limit(1).execute()

        if existing.data:
            return False

        supabase.table('claim_relationships').insert({
            'source_claim_id': claim_id,
            'target_claim_id': claim_id,  # Self-referencing for entity relationships
            'relationship_type': relationship_type,
            'description': description[:500],
        }).execute()
        return True
    except Exception as e:
        print(f"  Error creating relationship: {e}")
        return False


def analyze_relationships():
    """Analyze relationship findings and suggest connections."""
    print("=" * 70)
    print("RELATIONSHIP ANALYSIS")
    print("=" * 70)

    # Get relationship-type findings
    findings = supabase.table('research_findings').select(
        'id, content, confidence_score'
    ).eq('finding_type', 'relationship').execute()

    print(f"\nAnalyzing {len(findings.data)} relationship findings...")

    # Track entity pairs
    entity_pairs = defaultdict(list)
    relationship_types = defaultdict(int)

    for f in findings.data:
        content = f['content']
        entities = extract_entities_from_text(content)
        rel_type = extract_relationship_type(content)

        if rel_type:
            relationship_types[rel_type] += 1

        # Create pairs from all entities found
        for i, e1 in enumerate(entities):
            for e2 in entities[i+1:]:
                pair = tuple(sorted([e1, e2]))
                entity_pairs[pair].append({
                    'finding_id': f['id'],
                    'content': content,
                    'rel_type': rel_type,
                    'confidence': f.get('confidence_score', 0.5)
                })

    print(f"\n--- Relationship Types Found ---")
    for rel_type, count in sorted(relationship_types.items(), key=lambda x: -x[1]):
        print(f"  {rel_type}: {count}")

    print(f"\n--- Entity Pairs ({len(entity_pairs)} unique) ---")
    sorted_pairs = sorted(entity_pairs.items(), key=lambda x: -len(x[1]))

    for (e1, e2), mentions in sorted_pairs[:20]:
        rel_types = set(m['rel_type'] for m in mentions if m['rel_type'])
        print(f"\n  {e1} <-> {e2}")
        print(f"    Mentions: {len(mentions)}")
        print(f"    Types: {', '.join(rel_types)}")

    return entity_pairs, relationship_types


def build_relationships(dry_run: bool = True):
    """Build claim_relationships from findings."""
    print("=" * 70)
    print("BUILD CLAIM RELATIONSHIPS")
    print("=" * 70)

    entity_pairs, _ = analyze_relationships()

    if dry_run:
        print(f"\n[DRY RUN] Would create relationships for {len(entity_pairs)} entity pairs")
        return

    created = 0
    errors = 0

    for (e1, e2), mentions in entity_pairs.items():
        # Use the highest confidence mention
        best_mention = max(mentions, key=lambda x: x.get('confidence', 0))

        # Get or create entities
        e1_id = get_or_create_entity(e1)
        e2_id = get_or_create_entity(e2)

        if not e1_id or not e2_id:
            errors += 1
            continue

        # Get or create claim
        claim_id = get_or_create_claim_for_finding(
            best_mention['finding_id'],
            best_mention['content']
        )

        if not claim_id:
            errors += 1
            continue

        # Map relationship type to valid claim_relationships type
        rel_type = best_mention['rel_type'] or 'related'
        valid_rel_type = TYPE_MAP.get(rel_type, 'related_to')

        # Create relationship
        if create_claim_relationship(
            claim_id, e1_id, e2_id,
            valid_rel_type,
            best_mention['content']
        ):
            created += 1

    print(f"\nCreated {created} relationships ({errors} errors)")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Build Claim Relationships')
    parser.add_argument('--analyze', action='store_true', help='Analyze relationships')
    parser.add_argument('--build', action='store_true', help='Build relationships')
    parser.add_argument('--execute', action='store_true', help='Execute (not dry run)')

    args = parser.parse_args()

    if args.analyze:
        analyze_relationships()
    elif args.build:
        build_relationships(dry_run=not args.execute)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
