"""Data Review and Cleanup Script for Epstein Investigation.

This script helps:
1. Identify and remove duplicate findings
2. Review perspectives and key insights
3. Identify missing relationships
"""

import os
import sys
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)


def get_all_findings():
    """Fetch all findings from database."""
    result = supabase.table('research_findings').select('*').execute()
    return result.data


def find_duplicates(findings):
    """Find duplicate findings based on content similarity."""
    content_groups = defaultdict(list)

    for f in findings:
        # Normalize: lowercase, strip whitespace, first 150 chars
        normalized = f['content'][:150].lower().strip()
        content_groups[normalized].append(f)

    duplicates = {k: v for k, v in content_groups.items() if len(v) > 1}
    return duplicates


def deduplicate_findings(dry_run=True):
    """Remove duplicate findings, keeping highest confidence."""
    print("=" * 70)
    print("FINDING DEDUPLICATION")
    print("=" * 70)

    findings = get_all_findings()
    print(f"\nTotal findings: {len(findings)}")

    duplicates = find_duplicates(findings)
    print(f"Duplicate groups found: {len(duplicates)}")

    if not duplicates:
        print("No duplicates to remove!")
        return

    ids_to_delete = []

    for i, (content_prefix, items) in enumerate(duplicates.items(), 1):
        print(f"\n--- Group {i}: {len(items)} duplicates ---")
        print(f"Content: {content_prefix[:80]}...")

        # Sort by confidence (desc), then by created_at (asc to keep oldest)
        sorted_items = sorted(
            items,
            key=lambda x: (-(x.get('confidence_score') or 0), x.get('created_at', ''))
        )

        # Keep the first (highest confidence), delete the rest
        keep = sorted_items[0]
        delete = sorted_items[1:]

        print(f"  KEEP: {keep['id'][:8]}... (confidence: {keep.get('confidence_score', 'N/A')})")
        for d in delete:
            print(f"  DELETE: {d['id'][:8]}... (confidence: {d.get('confidence_score', 'N/A')})")
            ids_to_delete.append(d['id'])

    print(f"\n{'='*70}")
    print(f"Total findings to delete: {len(ids_to_delete)}")

    if dry_run:
        print("\n[DRY RUN] No changes made. Run with --execute to apply.")
    else:
        print("\nDeleting duplicates...")
        for fid in ids_to_delete:
            supabase.table('research_findings').delete().eq('id', fid).execute()
        print(f"Deleted {len(ids_to_delete)} duplicate findings.")

    return ids_to_delete


def review_perspectives():
    """Display perspectives with their key insights for review."""
    print("=" * 70)
    print("PERSPECTIVES REVIEW")
    print("=" * 70)

    perspectives = supabase.table('research_perspectives').select(
        'id,perspective_type,analysis_text,key_insights,recommendations,warnings'
    ).execute()

    print(f"\nTotal perspectives: {len(perspectives.data)}")

    for p in perspectives.data:
        print(f"\n{'='*50}")
        print(f"[{p['perspective_type'].upper()}] ID: {p['id'][:8]}...")
        print("-" * 50)

        # Analysis summary
        analysis = p.get('analysis_text', '')[:300]
        print(f"Analysis: {analysis}...")

        # Key insights
        insights = p.get('key_insights') or []
        print(f"\nKey Insights ({len(insights)}):")
        for i, insight in enumerate(insights, 1):
            print(f"  {i}. {insight}")

        # Recommendations
        recs = p.get('recommendations') or []
        if recs:
            print(f"\nRecommendations ({len(recs)}):")
            for r in recs[:3]:
                print(f"  - {r}")

        # Warnings
        warnings = p.get('warnings') or []
        if warnings:
            print(f"\nWarnings ({len(warnings)}):")
            for w in warnings:
                print(f"  ! {w}")


def find_entity_mentions(findings):
    """Find common entities mentioned across findings."""
    from collections import Counter

    # Common entity patterns to look for
    entities = Counter()

    key_names = [
        'jeffrey epstein', 'epstein', 'ghislaine maxwell', 'maxwell',
        'les wexner', 'wexner', 'steven hoffenberg', 'hoffenberg',
        'bill clinton', 'clinton', 'donald trump', 'trump',
        'prince andrew', 'andrew', 'alan dershowitz', 'dershowitz',
        'jean-luc brunel', 'brunel', 'victoria\'s secret',
        'towers financial', 'bear stearns', 'j. epstein',
        'deutsche bank', 'jpmorgan', 'jp morgan',
        'little saint james', 'zorro ranch', 'palm beach',
        'lolita express', 'new york', 'virgin islands'
    ]

    for f in findings:
        content = f['content'].lower()
        for name in key_names:
            if name in content:
                entities[name] += 1

    return entities


def suggest_relationships(findings):
    """Suggest potential relationships between findings."""
    print("=" * 70)
    print("RELATIONSHIP SUGGESTIONS")
    print("=" * 70)

    entities = find_entity_mentions(findings)

    print("\nTop mentioned entities:")
    for entity, count in entities.most_common(20):
        print(f"  {entity}: {count} mentions")

    # Group findings by entity
    entity_findings = defaultdict(list)
    for f in findings:
        content = f['content'].lower()
        for entity in ['jeffrey epstein', 'les wexner', 'steven hoffenberg',
                       'ghislaine maxwell', 'bill clinton', 'towers financial',
                       'bear stearns', 'deutsche bank', 'jpmorgan']:
            if entity in content:
                entity_findings[entity].append(f)

    print("\nFindings by key entity:")
    for entity, flist in sorted(entity_findings.items(), key=lambda x: -len(x[1])):
        print(f"\n  {entity.title()}: {len(flist)} findings")
        # Show finding types
        types = defaultdict(int)
        for f in flist:
            types[f['finding_type']] += 1
        print(f"    Types: {dict(types)}")


def review_knowledge_claims():
    """Review knowledge claims for relationship building."""
    print("=" * 70)
    print("KNOWLEDGE CLAIMS SAMPLE")
    print("=" * 70)

    # Get sample claims by type
    for claim_type in ['fact', 'event', 'relationship', 'financial']:
        claims = supabase.table('knowledge_claims').select(
            'id,claim_type,content,confidence_score,extracted_data'
        ).eq('claim_type', claim_type).limit(5).execute()

        print(f"\n[{claim_type.upper()}] Sample claims:")
        for c in claims.data:
            print(f"  - {c['content'][:100]}...")
            if c.get('extracted_data'):
                print(f"    Data: {str(c['extracted_data'])[:80]}...")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Data Review Script')
    parser.add_argument('--dedupe', action='store_true', help='Find duplicates')
    parser.add_argument('--execute', action='store_true', help='Execute deduplication')
    parser.add_argument('--perspectives', action='store_true', help='Review perspectives')
    parser.add_argument('--relationships', action='store_true', help='Suggest relationships')
    parser.add_argument('--claims', action='store_true', help='Review knowledge claims')
    parser.add_argument('--all', action='store_true', help='Run all reviews')

    args = parser.parse_args()

    if args.all or args.dedupe:
        deduplicate_findings(dry_run=not args.execute)

    if args.all or args.perspectives:
        review_perspectives()

    if args.all or args.relationships:
        findings = get_all_findings()
        suggest_relationships(findings)

    if args.all or args.claims:
        review_knowledge_claims()

    if not any([args.dedupe, args.perspectives, args.relationships, args.claims, args.all]):
        parser.print_help()


if __name__ == '__main__':
    main()
