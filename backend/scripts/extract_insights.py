"""Extract Key Insights from Perspectives and Findings.

This script identifies and tags "hidden gems" - insights that are not obvious
at first glance but emerged from deep research analysis.
"""

import os
import sys
import json
import re
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase = create_client(url, key)


# Keywords that indicate important/hidden insights
IMPORTANCE_INDICATORS = {
    'critical': [
        'power of attorney', 'fraud', 'criminal', 'illegal',
        'money laundering', 'ponzi', 'embezzlement', 'trafficking',
        'blackmail', 'conspiracy'
    ],
    'significant': [
        'million', 'billion', 'offshore', 'shell company',
        'secret', 'hidden', 'concealed', 'undisclosed',
        'suspicious', 'unusual', 'unprecedented'
    ],
    'notable': [
        'connection', 'relationship', 'linked', 'associated',
        'pattern', 'timeline', 'coincidence'
    ]
}

# Keywords for categorization
CATEGORY_INDICATORS = {
    'financial_connection': [
        'payment', 'transaction', 'transfer', 'account', 'bank',
        'investment', 'fund', 'money', 'million', 'billion', 'financial'
    ],
    'temporal_pattern': [
        'timeline', 'sequence', 'before', 'after', 'during',
        'year', 'month', 'date', 'period', 'coincide'
    ],
    'network_link': [
        'relationship', 'connection', 'associate', 'partner',
        'friend', 'client', 'employee', 'introduced'
    ],
    'power_structure': [
        'control', 'authority', 'power of attorney', 'director',
        'trustee', 'board', 'president', 'ceo', 'ownership'
    ],
    'document_correlation': [
        'document', 'record', 'evidence', 'file', 'testimony',
        'deposition', 'court', 'filing'
    ],
    'behavioral_pattern': [
        'pattern', 'repeated', 'systematic', 'regularly',
        'consistently', 'always', 'often'
    ]
}

# Key entities to look for
KEY_ENTITIES = [
    'jeffrey epstein', 'epstein', 'ghislaine maxwell', 'maxwell',
    'les wexner', 'wexner', 'steven hoffenberg', 'hoffenberg',
    'bill clinton', 'donald trump', 'prince andrew', 'alan dershowitz',
    'jean-luc brunel', 'victoria\'s secret', 'towers financial',
    'bear stearns', 'j. epstein', 'deutsche bank', 'jpmorgan',
    'little saint james', 'zorro ranch', 'palm beach'
]


def classify_importance(text: str) -> str:
    """Determine importance level based on content."""
    text_lower = text.lower()

    for level, keywords in IMPORTANCE_INDICATORS.items():
        if any(kw in text_lower for kw in keywords):
            return level

    return 'minor'


def classify_category(text: str) -> str:
    """Determine insight category based on content."""
    text_lower = text.lower()

    # Count matches per category
    scores = {}
    for category, keywords in CATEGORY_INDICATORS.items():
        scores[category] = sum(1 for kw in keywords if kw in text_lower)

    # Return highest scoring category
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)

    return 'other'


def classify_discoverability(text: str, source_type: str) -> str:
    """Estimate how hard this insight was to find."""
    text_lower = text.lower()

    # Hidden gem indicators
    hidden_gem_phrases = [
        'not widely known', 'overlooked', 'hidden', 'secret',
        'unreported', 'undisclosed', 'buried in', 'obscure'
    ]

    if any(phrase in text_lower for phrase in hidden_gem_phrases):
        return 'hidden_gem'

    # Deep analysis indicators (cross-referencing)
    deep_phrases = [
        'cross-reference', 'multiple sources', 'pattern across',
        'connecting', 'correlating', 'timeline shows'
    ]

    if any(phrase in text_lower for phrase in deep_phrases):
        return 'deep'

    # If from perspective analysis, likely moderate
    if source_type == 'perspective':
        return 'moderate'

    return 'surface'


def extract_entities(text: str) -> List[str]:
    """Extract key entities mentioned in text."""
    text_lower = text.lower()
    found = []

    for entity in KEY_ENTITIES:
        if entity in text_lower:
            # Normalize to title case
            found.append(entity.title())

    return list(set(found))


def analyze_perspective_insights(perspective: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract insights from a perspective's key_insights field."""
    insights = []
    key_insights = perspective.get('key_insights') or []
    perspective_id = perspective.get('id')
    perspective_type = perspective.get('perspective_type', 'unknown')

    for insight_text in key_insights:
        if not insight_text or len(insight_text) < 20:
            continue

        importance = classify_importance(insight_text)
        category = classify_category(insight_text)
        discoverability = classify_discoverability(insight_text, 'perspective')
        entities = extract_entities(insight_text)

        # Generate summary (first 150 chars or first sentence)
        summary = insight_text[:150]
        if '.' in summary:
            summary = summary.split('.')[0] + '.'

        insights.append({
            'perspective_id': perspective_id,
            'insight_text': insight_text,
            'insight_summary': summary,
            'insight_category': category,
            'importance_level': importance,
            'discoverability': discoverability,
            'related_entities': entities,
            'source_perspective_type': perspective_type,
        })

    return insights


def analyze_finding_insights(finding: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyze a finding to see if it qualifies as a key insight."""
    content = finding.get('content', '')
    finding_type = finding.get('finding_type', '')
    confidence = finding.get('confidence_score', 0) or 0

    # Only consider high-confidence findings of certain types
    if confidence < 0.7:
        return None

    if finding_type not in ['relationship', 'pattern', 'evidence', 'gap']:
        return None

    importance = classify_importance(content)

    # Only extract as insight if notable or higher
    if importance == 'minor':
        return None

    category = classify_category(content)
    discoverability = classify_discoverability(content, 'finding')
    entities = extract_entities(content)

    summary = content[:150]
    if '.' in summary:
        summary = summary.split('.')[0] + '.'

    return {
        'finding_id': finding.get('id'),
        'insight_text': content,
        'insight_summary': summary,
        'insight_category': category,
        'importance_level': importance,
        'discoverability': discoverability,
        'related_entities': entities,
        'source_finding_type': finding_type,
    }


def extract_all_insights(dry_run: bool = True) -> Tuple[List[Dict], List[Dict]]:
    """Extract insights from all perspectives and relevant findings."""
    print("=" * 70)
    print("KEY INSIGHT EXTRACTION")
    print("=" * 70)

    # Get all perspectives
    perspectives = supabase.table('research_perspectives').select(
        'id, perspective_type, key_insights, analysis_text'
    ).execute()

    print(f"\nAnalyzing {len(perspectives.data)} perspectives...")

    perspective_insights = []
    for p in perspectives.data:
        insights = analyze_perspective_insights(p)
        perspective_insights.extend(insights)

    print(f"  Found {len(perspective_insights)} insights from perspectives")

    # Get high-value findings
    findings = supabase.table('research_findings').select(
        'id, finding_type, content, confidence_score'
    ).in_('finding_type', ['relationship', 'pattern', 'evidence', 'gap']).gte(
        'confidence_score', 0.7
    ).execute()

    print(f"\nAnalyzing {len(findings.data)} high-value findings...")

    finding_insights = []
    for f in findings.data:
        insight = analyze_finding_insights(f)
        if insight:
            finding_insights.append(insight)

    print(f"  Found {len(finding_insights)} insights from findings")

    all_insights = perspective_insights + finding_insights

    # Categorize by importance
    by_importance = defaultdict(list)
    for i in all_insights:
        by_importance[i['importance_level']].append(i)

    print(f"\n--- Insights by Importance ---")
    for level in ['critical', 'significant', 'notable', 'minor']:
        count = len(by_importance.get(level, []))
        print(f"  {level}: {count}")

    # Categorize by category
    by_category = defaultdict(list)
    for i in all_insights:
        by_category[i['insight_category']].append(i)

    print(f"\n--- Insights by Category ---")
    for cat, items in sorted(by_category.items(), key=lambda x: -len(x[1])):
        print(f"  {cat}: {len(items)}")

    # Categorize by discoverability
    by_discover = defaultdict(list)
    for i in all_insights:
        by_discover[i['discoverability']].append(i)

    print(f"\n--- Insights by Discoverability ---")
    for disc in ['hidden_gem', 'deep', 'moderate', 'surface']:
        count = len(by_discover.get(disc, []))
        print(f"  {disc}: {count}")

    # Show sample hidden gems
    hidden_gems = by_discover.get('hidden_gem', [])
    if hidden_gems:
        print(f"\n--- Sample Hidden Gems ({len(hidden_gems)} total) ---")
        for gem in hidden_gems[:5]:
            print(f"\n  [{gem['importance_level'].upper()}] {gem['insight_category']}")
            print(f"  {gem['insight_summary']}")
            if gem['related_entities']:
                print(f"  Entities: {', '.join(gem['related_entities'][:5])}")

    # Show critical insights
    critical = by_importance.get('critical', [])
    if critical:
        print(f"\n--- Critical Insights ({len(critical)} total) ---")
        for c in critical[:5]:
            print(f"\n  [{c['insight_category']}]")
            print(f"  {c['insight_summary']}")

    return perspective_insights, finding_insights


def save_insights(insights: List[Dict[str, Any]], dry_run: bool = True) -> int:
    """Save insights to database."""
    if dry_run:
        print(f"\n[DRY RUN] Would save {len(insights)} insights")
        return 0

    saved = 0
    for insight in insights:
        data = {
            'insight_text': insight['insight_text'],
            'insight_summary': insight.get('insight_summary'),
            'insight_category': insight['insight_category'],
            'importance_level': insight['importance_level'],
            'discoverability': insight['discoverability'],
            'related_entities': insight.get('related_entities', []),
        }

        if insight.get('perspective_id'):
            data['perspective_id'] = insight['perspective_id']
        if insight.get('finding_id'):
            data['finding_id'] = insight['finding_id']

        try:
            supabase.table('key_insights').insert(data).execute()
            saved += 1
        except Exception as e:
            print(f"  Error saving insight: {e}")

    print(f"\nSaved {saved}/{len(insights)} insights")
    return saved


def interactive_review(insights: List[Dict[str, Any]]):
    """Interactive review mode for manual tagging."""
    print("\n" + "=" * 70)
    print("INTERACTIVE INSIGHT REVIEW")
    print("=" * 70)
    print("\nCommands: [y]es save, [n]o skip, [e]dit importance, [c]ategory, [q]uit")

    to_save = []

    for i, insight in enumerate(insights):
        print(f"\n--- Insight {i+1}/{len(insights)} ---")
        print(f"Category: {insight['insight_category']}")
        print(f"Importance: {insight['importance_level']}")
        print(f"Discoverability: {insight['discoverability']}")
        print(f"Entities: {', '.join(insight.get('related_entities', [])[:5])}")
        print(f"\n{insight['insight_text'][:500]}")

        cmd = input("\n> ").lower().strip()

        if cmd == 'q':
            break
        elif cmd == 'y':
            to_save.append(insight)
            print("  -> Marked for save")
        elif cmd == 'n':
            print("  -> Skipped")
        elif cmd == 'e':
            new_imp = input("  New importance (critical/significant/notable/minor): ").strip()
            if new_imp in ['critical', 'significant', 'notable', 'minor']:
                insight['importance_level'] = new_imp
                to_save.append(insight)
                print(f"  -> Updated to {new_imp}, marked for save")
        elif cmd == 'c':
            print("  Categories: financial_connection, temporal_pattern, network_link,")
            print("             power_structure, document_correlation, behavioral_pattern, other")
            new_cat = input("  New category: ").strip()
            if new_cat:
                insight['insight_category'] = new_cat
                to_save.append(insight)
                print(f"  -> Updated to {new_cat}, marked for save")

    return to_save


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Extract Key Insights')
    parser.add_argument('--extract', action='store_true', help='Extract insights')
    parser.add_argument('--execute', action='store_true', help='Save to database')
    parser.add_argument('--interactive', action='store_true', help='Interactive review')
    parser.add_argument('--hidden-gems', action='store_true', help='Show only hidden gems')
    parser.add_argument('--critical', action='store_true', help='Show only critical')

    args = parser.parse_args()

    if args.extract:
        perspective_insights, finding_insights = extract_all_insights(dry_run=not args.execute)
        all_insights = perspective_insights + finding_insights

        if args.hidden_gems:
            all_insights = [i for i in all_insights if i['discoverability'] == 'hidden_gem']

        if args.critical:
            all_insights = [i for i in all_insights if i['importance_level'] == 'critical']

        if args.interactive:
            to_save = interactive_review(all_insights)
            if to_save and input(f"\nSave {len(to_save)} insights? [y/N]: ").lower() == 'y':
                save_insights(to_save, dry_run=False)
        elif args.execute:
            save_insights(all_insights, dry_run=False)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
