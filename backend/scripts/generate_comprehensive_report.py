"""
Generate Comprehensive Epstein Investigation Report.

This script queries all database tables and generates a comprehensive HTML report
combining documentary evidence with contextual knowledge.
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, ".")
load_dotenv()

from supabase import create_client, Client


def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(url, key)


# Key entities to highlight (from batches 1-17)
KEY_PERSONS = [
    "Jeffrey Epstein", "Ghislaine Maxwell", "Leslie Wexner", "Robert Maxwell",
    "Ehud Barak", "Bill Clinton", "Donald Trump", "Prince Andrew",
    "Virginia Giuffre", "Alex Acosta", "Alan Dershowitz", "Sarah Kellen",
    "Lesley Groff", "Nadia Marcinkova", "Adriana Ross", "Jean-Luc Brunel",
    "Bill Richardson", "Glenn Dubin", "Eva Dubin", "Larry Summers",
    "Steven Hoffenberg", "Ace Greenberg", "Donald Barr", "Annie Farmer",
    "Maria Farmer", "Courtney Wild", "Sarah Ransome", "Haley Robson",
    "Alfredo Rodriguez", "Michael Reiter", "Joseph Recarey", "Bradley Edwards",
    "Barry Krischer", "Ken Starr", "Gerald Lefcourt", "Jes Staley",
    "Leon Black", "Naomi Campbell", "Kevin Spacey", "Chris Tucker", "David Boies"
]

KEY_ORGANIZATIONS = [
    "Bear Stearns", "Dalton School", "Carbyne", "Mega Group",
    "L Brands", "Victoria's Secret", "Mar-a-Lago", "JPMorgan Chase",
    "Deutsche Bank", "Barclays", "Apollo Global Management"
]


def categorize_entities(entities):
    """Categorize entities into thematic groups."""
    categories = {
        "core_operation": [],
        "victims_survivors": [],
        "legal_law_enforcement": [],
        "political_connections": [],
        "financial_network": [],
        "intelligence_surveillance": [],
        "media_journalists": [],
        "properties_organizations": [],
        "other": []
    }

    # Keywords for categorization
    core_keywords = ["epstein", "maxwell", "kellen", "groff", "marcinkova", "ross", "brunel", "inner circle"]
    victim_keywords = ["victim", "accuser", "survivor", "jane doe", "giuffre", "farmer", "ransome", "wild", "robson", "traffick"]
    legal_keywords = ["attorney", "lawyer", "judge", "prosecutor", "fbi", "police", "detective", "acosta", "dershowitz", "krischer", "counsel", "court"]
    political_keywords = ["president", "governor", "senator", "congress", "clinton", "trump", "richardson", "andrew", "prince", "duke", "prime minister", "barak"]
    financial_keywords = ["wexner", "dubin", "black", "hedge", "fund", "bank", "jpmorgan", "deutsche", "barclays", "apollo", "investor", "billion"]
    intelligence_keywords = ["mossad", "intelligence", "surveillance", "carbyne", "maxwell", "robert", "israel", "spy", "cia", "fbi", "mega group"]
    media_keywords = ["journalist", "reporter", "news", "media", "vanity fair", "miami herald", "bbc"]

    for entity in entities:
        name_lower = entity.get("canonical_name", "").lower()
        desc_lower = (entity.get("description") or "").lower()
        entity_type = entity.get("entity_type", "")
        combined = name_lower + " " + desc_lower

        categorized = False

        # Intelligence (check first for Robert Maxwell)
        if any(kw in combined for kw in intelligence_keywords):
            categories["intelligence_surveillance"].append(entity)
            categorized = True
        # Core operation
        elif any(kw in combined for kw in core_keywords):
            categories["core_operation"].append(entity)
            categorized = True
        # Victims
        elif any(kw in combined for kw in victim_keywords):
            categories["victims_survivors"].append(entity)
            categorized = True
        # Legal
        elif any(kw in combined for kw in legal_keywords):
            categories["legal_law_enforcement"].append(entity)
            categorized = True
        # Political
        elif any(kw in combined for kw in political_keywords):
            categories["political_connections"].append(entity)
            categorized = True
        # Financial
        elif any(kw in combined for kw in financial_keywords):
            categories["financial_network"].append(entity)
            categorized = True
        # Media
        elif any(kw in combined for kw in media_keywords):
            categories["media_journalists"].append(entity)
            categorized = True
        # Organizations
        elif entity_type == "organization":
            categories["properties_organizations"].append(entity)
            categorized = True

        if not categorized:
            categories["other"].append(entity)

    return categories


def get_all_data(client):
    """Fetch all relevant data from database."""
    data = {}

    # Get entities with substantial descriptions (curated data)
    print("Fetching entities...")
    result = client.table("knowledge_entities").select("*").not_.is_("description", "null").execute()
    # Filter to entities with meaningful descriptions (> 50 chars)
    data["entities"] = [e for e in result.data if len(e.get("description", "") or "") > 50]
    print(f"  Found {len(data['entities'])} entities with descriptions")

    # Skip key entity search - we have them in entities already
    data["key_entities"] = [e for e in data["entities"] if any(
        kw.lower() in e.get("canonical_name", "").lower()
        for kw in ["epstein", "maxwell", "wexner", "barak", "clinton", "trump", "andrew", "acosta"]
    )]
    print(f"  Found {len(data['key_entities'])} key entities")

    # Get entity stats
    result = client.table("knowledge_entities").select("entity_type", count="exact").execute()
    total = result.count

    result = client.table("knowledge_entities").select("*").eq("entity_type", "person").execute()
    persons = len(result.data)

    result = client.table("knowledge_entities").select("*").eq("entity_type", "organization").execute()
    orgs = len(result.data)

    data["stats"] = {
        "total_entities": total,
        "persons": persons,
        "organizations": orgs
    }
    print(f"  Stats: {total} total, {persons} persons, {orgs} organizations")

    return data


def generate_html_report(data):
    """Generate comprehensive HTML report."""

    categories = categorize_entities(data["entities"])

    # Count categorized entities
    category_counts = {k: len(v) for k, v in categories.items()}

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jeffrey Epstein Comprehensive Investigation Report</title>
    <style>
        :root {
            --primary: #0f0f23;
            --secondary: #1a1a3e;
            --accent: #e94560;
            --accent-gold: #ffd700;
            --accent-blue: #4a9eff;
            --accent-green: #4caf50;
            --accent-orange: #ff9800;
            --accent-purple: #9c27b0;
            --text: #eaeaea;
            --muted: #a0a0a0;
            --card-bg: rgba(255,255,255,0.03);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: var(--text);
            line-height: 1.7;
            min-height: 100vh;
        }

        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }

        /* Header */
        header {
            text-align: center;
            padding: 4rem 2rem;
            background: linear-gradient(180deg, rgba(233, 69, 96, 0.1) 0%, transparent 100%);
            border-bottom: 2px solid var(--accent);
            margin-bottom: 3rem;
        }

        header h1 {
            font-size: 3rem;
            color: var(--accent);
            margin-bottom: 1rem;
            text-shadow: 0 0 30px rgba(233, 69, 96, 0.3);
        }

        header .subtitle {
            font-size: 1.3rem;
            color: var(--muted);
            max-width: 800px;
            margin: 0 auto;
        }

        header .meta {
            margin-top: 2rem;
            font-size: 0.95rem;
            color: var(--muted);
        }

        header .meta span {
            display: inline-block;
            margin: 0 1rem;
            padding: 0.5rem 1rem;
            background: var(--card-bg);
            border-radius: 4px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        /* Table of Contents */
        .toc {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 3rem;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .toc h2 {
            color: var(--accent);
            margin-bottom: 1.5rem;
            font-size: 1.5rem;
        }

        .toc-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1rem;
        }

        .toc a {
            display: block;
            padding: 0.75rem 1rem;
            color: var(--text);
            text-decoration: none;
            background: rgba(255,255,255,0.02);
            border-radius: 6px;
            border-left: 3px solid var(--accent);
            transition: all 0.2s;
        }

        .toc a:hover {
            background: rgba(233, 69, 96, 0.1);
            transform: translateX(5px);
        }

        /* Sections */
        section {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(255,255,255,0.1);
        }

        section h2 {
            color: var(--accent);
            font-size: 2rem;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid rgba(233, 69, 96, 0.3);
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        section h2 .count {
            font-size: 0.9rem;
            padding: 0.3rem 0.8rem;
            background: var(--accent);
            border-radius: 20px;
            color: white;
        }

        section h3 {
            color: var(--text);
            font-size: 1.4rem;
            margin: 2rem 0 1rem;
        }

        /* Key Finding Box */
        .key-finding {
            background: linear-gradient(135deg, rgba(233, 69, 96, 0.15) 0%, rgba(233, 69, 96, 0.05) 100%);
            border: 1px solid var(--accent);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1.5rem 0;
        }

        .key-finding strong {
            color: var(--accent);
            display: block;
            margin-bottom: 0.5rem;
            font-size: 1.1rem;
        }

        /* Entity Cards */
        .entity-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin: 1.5rem 0;
        }

        .entity-card {
            background: rgba(255,255,255,0.02);
            border-radius: 10px;
            padding: 1.5rem;
            border-left: 4px solid var(--accent);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .entity-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .entity-card.core { border-color: var(--accent); }
        .entity-card.victim { border-color: var(--accent-blue); }
        .entity-card.legal { border-color: var(--accent-green); }
        .entity-card.political { border-color: var(--accent-purple); }
        .entity-card.financial { border-color: var(--accent-gold); }
        .entity-card.intelligence { border-color: var(--accent-orange); }

        .entity-card .name {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--accent);
            margin-bottom: 0.5rem;
        }

        .entity-card .type {
            display: inline-block;
            font-size: 0.75rem;
            padding: 0.2rem 0.6rem;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            margin-bottom: 0.75rem;
            text-transform: uppercase;
        }

        .entity-card .description {
            font-size: 0.95rem;
            color: var(--muted);
            line-height: 1.6;
        }

        /* Timeline */
        .timeline {
            position: relative;
            padding-left: 3rem;
            margin: 2rem 0;
        }

        .timeline::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 3px;
            background: linear-gradient(180deg, var(--accent) 0%, var(--accent-purple) 100%);
        }

        .timeline-item {
            position: relative;
            padding: 1.5rem 0;
            padding-left: 2rem;
        }

        .timeline-item::before {
            content: '';
            position: absolute;
            left: -3rem;
            top: 1.8rem;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: var(--accent);
            border: 3px solid var(--primary);
            box-shadow: 0 0 10px var(--accent);
        }

        .timeline-date {
            font-weight: 700;
            color: var(--accent);
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
        }

        .timeline-event {
            color: var(--text);
            line-height: 1.6;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }

        .stat-card {
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .stat-card .number {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--accent);
            line-height: 1;
        }

        .stat-card .label {
            font-size: 0.9rem;
            color: var(--muted);
            margin-top: 0.5rem;
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
        }

        th, td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        th {
            background: rgba(255,255,255,0.05);
            color: var(--accent);
            font-weight: 600;
        }

        tr:hover td {
            background: rgba(255,255,255,0.02);
        }

        /* Lists */
        ul, ol {
            margin: 1rem 0;
            padding-left: 1.5rem;
        }

        li {
            margin: 0.5rem 0;
        }

        /* Evidence Strength */
        .evidence-tag {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 3px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .evidence-documentary { background: var(--accent-green); color: white; }
        .evidence-testimony { background: var(--accent-blue); color: white; }
        .evidence-multiple { background: var(--accent-gold); color: black; }
        .evidence-single { background: var(--accent-orange); color: white; }
        .evidence-contextual { background: var(--muted); color: white; }

        /* Collapsible */
        .collapsible {
            cursor: pointer;
            user-select: none;
        }

        .collapsible::after {
            content: ' [+]';
            color: var(--accent);
            font-size: 0.9rem;
        }

        .collapsible.active::after {
            content: ' [-]';
        }

        .collapse-content {
            display: none;
            padding: 1rem 0;
        }

        .collapse-content.show {
            display: block;
        }

        /* Footer */
        footer {
            text-align: center;
            padding: 3rem;
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 3rem;
            color: var(--muted);
        }

        footer strong {
            color: var(--text);
        }

        /* Print styles */
        @media print {
            body { background: white; color: black; }
            .container { max-width: 100%; }
            section { break-inside: avoid; }
        }

        /* Mobile */
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            header h1 { font-size: 2rem; }
            .entity-grid { grid-template-columns: 1fr; }
            .toc-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Jeffrey Epstein Comprehensive Investigation Report</h1>
            <div class="subtitle">
                A systematic analysis of the Epstein network, combining documentary evidence from
                the TrumpEpsteinFiles archive with contextual intelligence research
            </div>
            <div class="meta">
                <span>Generated: """ + datetime.now().strftime("%B %d, %Y") + """</span>
                <span>Entities: """ + str(data["stats"]["total_entities"]) + """</span>
                <span>Documents: 1,998 files</span>
                <span>Batches: 17</span>
            </div>
        </header>

        <nav class="toc">
            <h2>Table of Contents</h2>
            <div class="toc-grid">
                <a href="#executive-summary">1. Executive Summary</a>
                <a href="#timeline">2. Chronological Timeline</a>
                <a href="#core-operation">3. Core Operation</a>
                <a href="#intelligence">4. Intelligence Connections</a>
                <a href="#powerful-connections">5. Powerful Connections</a>
                <a href="#legal-history">6. Legal History</a>
                <a href="#death-investigation">7. Death Investigation</a>
                <a href="#victims">8. Victims & Survivors</a>
                <a href="#documentary-evidence">9. Documentary Evidence</a>
                <a href="#open-questions">10. Open Questions</a>
            </div>
        </nav>

        <!-- EXECUTIVE SUMMARY -->
        <section id="executive-summary">
            <h2>1. Executive Summary</h2>

            <div class="key-finding">
                <strong>Central Finding</strong>
                Jeffrey Epstein operated a sophisticated sexual trafficking and blackmail enterprise
                spanning multiple continents, with evidence suggesting connections to intelligence
                services. The operation involved systematic recording of compromising encounters
                with powerful individuals.
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">""" + str(data["stats"]["total_entities"]) + """</div>
                    <div class="label">Total Entities</div>
                </div>
                <div class="stat-card">
                    <div class="number">""" + str(data["stats"]["persons"]) + """</div>
                    <div class="label">Persons</div>
                </div>
                <div class="stat-card">
                    <div class="number">""" + str(data["stats"]["organizations"]) + """</div>
                    <div class="label">Organizations</div>
                </div>
                <div class="stat-card">
                    <div class="number">17</div>
                    <div class="label">Import Batches</div>
                </div>
                <div class="stat-card">
                    <div class="number">1,998</div>
                    <div class="label">Source Documents</div>
                </div>
                <div class="stat-card">
                    <div class="number">20+</div>
                    <div class="label">Documented Victims</div>
                </div>
            </div>

            <h3>Key Discoveries</h3>
            <ul>
                <li><strong>Surveillance Operation:</strong> Documentary evidence shows "Mr Epstein's residences in Florida and New York had surveillance cameras that taped the sex sessions and taped even in the bathroom" (Mail on Sunday document)</li>
                <li><strong>Intelligence Connections:</strong> Robert Maxwell (Ghislaine's father) was given an Israeli state funeral attended by intelligence officials; Epstein invested in Israeli surveillance company Carbyne alongside former Israeli PM Ehud Barak</li>
                <li><strong>Blackmail Potential:</strong> Virginia Giuffre testified about "sexual events that I had with these men presumably so that he could potentially blackmail them"</li>
                <li><strong>Protected Status:</strong> Alexander Acosta claimed he was told to back off because Epstein "belonged to intelligence"</li>
                <li><strong>Unexplained Wealth:</strong> Epstein's billions came from unknown sources; only one confirmed client (Leslie Wexner)</li>
            </ul>
        </section>

        <!-- TIMELINE -->
        <section id="timeline">
            <h2>2. Chronological Timeline</h2>

            <h3>Origins (1953-1990)</h3>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-date">January 20, 1953</div>
                    <div class="timeline-event">Jeffrey Edward Epstein born in Brooklyn, New York</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">1973-1976</div>
                    <div class="timeline-event">Epstein teaches math at Dalton School without a college degree, hired by headmaster Donald Barr (father of future AG William Barr, former OSS officer)</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">1976-1981</div>
                    <div class="timeline-event">Works at Bear Stearns after tutoring chairman Ace Greenberg's son</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">1982</div>
                    <div class="timeline-event">Starts J. Epstein & Co. First major client: Ana Obregon (Spanish actress)</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">Late 1980s</div>
                    <div class="timeline-event">Partners with Steven Hoffenberg on Towers Financial ($500M Ponzi scheme). Hoffenberg later claims Epstein was "introduced to intelligence work"</div>
                </div>
            </div>

            <h3>Rise to Power (1991-1999)</h3>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-date">November 5, 1991</div>
                    <div class="timeline-event">Robert Maxwell dies mysteriously, falling from his yacht. Given Israeli state funeral on Mount of Olives attended by intelligence officials. Ghislaine enters Epstein's orbit.</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">1991</div>
                    <div class="timeline-event">Leslie Wexner grants Epstein full power of attorney. Mega Group founded by Wexner and Charles Bronfman.</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">1995</div>
                    <div class="timeline-event">Wexner transfers Manhattan townhouse (9 E 71st St) to Epstein</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">1998</div>
                    <div class="timeline-event">Epstein acquires Little St. James Island, U.S. Virgin Islands</div>
                </div>
            </div>

            <h3>Peak Operation (2000-2007)</h3>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-date">2000</div>
                    <div class="timeline-event">Virginia Giuffre (age 16) recruited by Ghislaine Maxwell at Trump's Mar-a-Lago</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">March 2005</div>
                    <div class="timeline-event">Palm Beach Police begin investigation after victim's parent complaint</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">2006</div>
                    <div class="timeline-event">Police identify 40+ victims. State Attorney Barry Krischer reduces charges. FBI opens federal investigation.</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">October 2007</div>
                    <div class="timeline-event">US Attorney Alexander Acosta meets privately with Epstein's attorney Jay Lefkowitz</div>
                </div>
            </div>

            <h3>The Deal (2008)</h3>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-date">September 2008</div>
                    <div class="timeline-event">Controversial Non-Prosecution Agreement (NPA) finalized. Epstein pleads guilty to state charges, receives 13-month work release. Four co-conspirators (Kellen, Groff, Ross, Marcinkova) granted immunity. Victims not notified (CVRA violation).</div>
                </div>
            </div>

            <h3>Post-Conviction (2009-2018)</h3>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-date">January 2010</div>
                    <div class="timeline-event">Epstein facilitates meeting between UK Chancellor Alistair Darling and JPMorgan's Jes Staley at Davos</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">2011</div>
                    <div class="timeline-event">Ghislaine Maxwell's lawyer receives detailed victim allegations from Mail on Sunday naming Dubin, Wexner, Barak, Mitchell, Andrew</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">2015</div>
                    <div class="timeline-event">Virginia Giuffre files lawsuit against Ghislaine Maxwell</div>
                </div>
            </div>

            <h3>The Reckoning (2019)</h3>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-date">July 6, 2019</div>
                    <div class="timeline-event">Epstein arrested at Teterboro Airport by FBI/SDNY on sex trafficking charges</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">July 23, 2019</div>
                    <div class="timeline-event">First apparent suicide attempt at MCC Manhattan. Placed on suicide watch.</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">July 29, 2019</div>
                    <div class="timeline-event">Removed from suicide watch after 6 days. Cellmate removed.</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">August 9, 2019</div>
                    <div class="timeline-event">New tranche of documents unsealed identifying prominent names</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">August 10, 2019</div>
                    <div class="timeline-event">Epstein found dead at 6:30 AM. Guards falsified logs. Both cameras malfunctioned.</div>
                </div>
            </div>

            <h3>Aftermath (2020-Present)</h3>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-date">July 2, 2020</div>
                    <div class="timeline-event">Ghislaine Maxwell arrested in New Hampshire</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">December 2021</div>
                    <div class="timeline-event">Maxwell convicted on 5 federal counts including sex trafficking of minors</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">February 2022</div>
                    <div class="timeline-event">Jean-Luc Brunel found dead in Paris prison (ruled suicide). Prince Andrew settles with Virginia Giuffre.</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">June 2022</div>
                    <div class="timeline-event">Maxwell sentenced to 20 years</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">2024-2025</div>
                    <div class="timeline-event">Additional documents unsealed. Florida grand jury records released.</div>
                </div>
            </div>
        </section>

        <!-- CORE OPERATION -->
        <section id="core-operation">
            <h2>3. The Core Operation <span class="count">""" + str(category_counts.get("core_operation", 0)) + """ entities</span></h2>

            <div class="key-finding">
                <strong>Operational Structure</strong>
                Epstein ran a hierarchical criminal enterprise with Maxwell as chief recruiter,
                multiple schedulers/assistants handling logistics, and a network of victim-turned-recruiters.
            </div>

            <h3>Central Figures</h3>
            <div class="entity-grid">"""

    # Add core operation entities
    core_entities = [
        {"name": "Jeffrey Epstein", "type": "person", "desc": "Principal operator. Financier with unexplained wealth. Only confirmed client: Leslie Wexner. Operated properties in Manhattan, Palm Beach, New Mexico, Virgin Islands, Paris. Died August 10, 2019 at MCC Manhattan."},
        {"name": "Ghislaine Maxwell", "type": "person", "desc": "Chief recruiter and manager. Daughter of Robert Maxwell. Recruited Virginia Giuffre at Mar-a-Lago. Convicted December 2021 on 5 federal counts including sex trafficking. Sentenced to 20 years."},
        {"name": "Sarah Kellen", "type": "person", "desc": "Primary scheduler and gatekeeper. Named as unindicted co-conspirator in 2008 NPA. Managed victim appointments at Palm Beach. Granted immunity. Now married to NASCAR driver Brian Vickers."},
        {"name": "Lesley Groff", "type": "person", "desc": "Executive assistant earning $200,000/year. High-level scheduler managing Epstein's logistics and travel. Granted immunity in 2008 NPA. Never charged."},
        {"name": "Nadia Marcinkova", "type": "person", "desc": "Allegedly brought from Yugoslavia as teenager by Epstein who 'purchased' her. Victim-turned-participant. Granted immunity. Now operates as 'Global Girl' aviation company owner."},
        {"name": "Adriana Ross", "type": "person", "desc": "Former model from Poland. Assistant and model recruiter. Granted immunity in 2008 NPA. Assisted with scheduling and travel coordination."},
        {"name": "Jean-Luc Brunel", "type": "person", "desc": "French modeling agent. MC2 Model Management founder. Accused of providing girls to Epstein. Arrested December 2020 in Paris. Found dead in cell February 2022 (ruled suicide)."}
    ]

    for e in core_entities:
        html += f"""
                <div class="entity-card core">
                    <div class="name">{e['name']}</div>
                    <span class="type">{e['type']}</span>
                    <div class="description">{e['desc']}</div>
                </div>"""

    html += """
            </div>

            <h3>Recruitment Methodology</h3>
            <ul>
                <li><strong>Target Profile:</strong> Girls aged 14-17, often from economically disadvantaged backgrounds</li>
                <li><strong>Recruitment Locations:</strong> Shopping malls, high schools, Mar-a-Lago, modeling agencies</li>
                <li><strong>Initial Approach:</strong> Offers of legitimate employment (massage, modeling) or educational support</li>
                <li><strong>Grooming:</strong> Gifts, cash payments ($200-$300), promises of career advancement</li>
                <li><strong>Escalation:</strong> "Massage" sessions that progressed to sexual abuse</li>
                <li><strong>Pyramid Scheme:</strong> Victims paid $200-$300 "finder's fees" to recruit other girls</li>
            </ul>

            <h3>Properties (Trafficking Locations)</h3>
            <table>
                <thead>
                    <tr><th>Property</th><th>Location</th><th>Significance</th></tr>
                </thead>
                <tbody>
                    <tr><td>Manhattan Townhouse</td><td>9 E 71st Street, NYC</td><td>Primary residence. Transferred from Wexner. Site of documented abuse with surveillance cameras.</td></tr>
                    <tr><td>Palm Beach Mansion</td><td>358 El Brillo Way, FL</td><td>Primary trafficking location. Subject of 2005 investigation. Thousands of images seized.</td></tr>
                    <tr><td>Zorro Ranch</td><td>Stanley, New Mexico</td><td>7,500-acre estate. Annie Farmer testified to abuse here. Alleged "baby ranch" plans.</td></tr>
                    <tr><td>Little St. James Island</td><td>U.S. Virgin Islands</td><td>"Pedophile Island." Extensive guest lists documented. Where Epstein spent most later years.</td></tr>
                    <tr><td>Paris Apartment</td><td>Avenue Foch, Paris</td><td>European base. Brunel's model agency recruitment hub.</td></tr>
                </tbody>
            </table>
        </section>

        <!-- INTELLIGENCE CONNECTIONS -->
        <section id="intelligence">
            <h2>4. Intelligence Connections <span class="count">""" + str(category_counts.get("intelligence_surveillance", 0)) + """ entities</span></h2>

            <div class="key-finding">
                <strong>Intelligence Operation Hypothesis</strong>
                Multiple lines of evidence suggest Epstein operated a sexual blackmail operation
                with possible intelligence agency connections. No single document proves this, but
                the pattern is compelling.
            </div>

            <h3>Surveillance/Blackmail Evidence</h3>
            <div class="key-finding">
                <strong>Documentary Proof (Mail on Sunday)</strong>
                "Mr Epstein's residences in Florida and New York had surveillance cameras that
                taped the sex sessions and taped even in the bathroom"
            </div>

            <div class="key-finding">
                <strong>Victim Testimony (Virginia Giuffre)</strong>
                "Sexual events that I had with these men presumably so that he could potentially blackmail them"
            </div>

            <h3>Key Intelligence-Adjacent Figures</h3>
            <div class="entity-grid">"""

    intel_entities = [
        {"name": "Robert Maxwell", "type": "person", "class": "intelligence", "desc": "Ghislaine's father. Czechoslovakian-born British media tycoon (Mirror Group). Died mysteriously November 5, 1991, falling from his yacht 'Lady Ghislaine' near Canary Islands. Given Israeli state funeral on Mount of Olives attended by intelligence officials. Former Mossad officer Victor Ostrovsky alleged Maxwell was a long-standing Mossad asset."},
        {"name": "Ehud Barak", "type": "person", "class": "intelligence", "desc": "Former Israeli Prime Minister (1999-2001) and Defense Minister. Most decorated soldier in Israeli history. Mail on Sunday document alleges Maxwell and Epstein 'arranged for Ehud Barak to have sex with several girls.' Chairman of Carbyne surveillance tech company where Epstein invested. Photographed multiple times entering Epstein's NYC mansion."},
        {"name": "Carbyne", "type": "organization", "class": "intelligence", "desc": "Israeli emergency response and surveillance technology company (formerly Reporty Homeland Security). Ehud Barak served as chairman. Epstein was an investor. Other investors included Nicole Junkermann and Peter Thiel's Founders Fund. Technology for emergency call (911) monitoring and location tracking."},
        {"name": "Mega Group", "type": "organization", "class": "intelligence", "desc": "Secretive organization of ~20 wealthy American Jewish businessmen, founded 1991 by Leslie Wexner and Charles Bronfman. Members included Edgar Bronfman Sr., Michael Steinhardt. Focus on pro-Israel philanthropy. Wexner was Epstein's only confirmed billionaire client."},
        {"name": "Steven Hoffenberg", "type": "person", "class": "intelligence", "desc": "Epstein's early business partner. CEO of Towers Financial ($500M Ponzi scheme). Served 18 years; Epstein escaped prosecution. Hoffenberg claimed Epstein was the 'architect' of the fraud and was 'introduced to intelligence work.' Died 2022."},
        {"name": "Donald Barr", "type": "person", "class": "intelligence", "desc": "Dalton School headmaster who hired Epstein to teach without a degree (1973-74). Father of future AG William Barr. Former OSS (CIA precursor) officer. Wrote sci-fi novel 'Space Relations' (1973) about oligarchs sexually enslaving people."}
    ]

    for e in intel_entities:
        html += f"""
                <div class="entity-card intelligence">
                    <div class="name">{e['name']}</div>
                    <span class="type">{e['type']}</span>
                    <div class="description">{e['desc']}</div>
                </div>"""

    html += """
            </div>

            <h3>Evidence Summary</h3>
            <table>
                <thead>
                    <tr><th>Evidence Type</th><th>Details</th><th>Strength</th></tr>
                </thead>
                <tbody>
                    <tr><td>Surveillance Cameras</td><td>Documentary proof of recording equipment in all residences</td><td><span class="evidence-tag evidence-documentary">Documentary</span></td></tr>
                    <tr><td>Blackmail Intent</td><td>Virginia Giuffre sworn testimony about blackmail purpose</td><td><span class="evidence-tag evidence-testimony">Testimony</span></td></tr>
                    <tr><td>Acosta Statement</td><td>"I was told Epstein belonged to intelligence"</td><td><span class="evidence-tag evidence-testimony">Testimony</span></td></tr>
                    <tr><td>Robert Maxwell</td><td>Israeli state funeral, Ostrovsky allegations</td><td><span class="evidence-tag evidence-multiple">Multiple Sources</span></td></tr>
                    <tr><td>Carbyne Investment</td><td>Epstein + Barak in Israeli surveillance tech</td><td><span class="evidence-tag evidence-documentary">Documentary</span></td></tr>
                    <tr><td>Hoffenberg Claims</td><td>"Introduced to intelligence work"</td><td><span class="evidence-tag evidence-single">Single Source</span></td></tr>
                    <tr><td>Israeli Passport</td><td>Found during 2019 arrest, issued in false name</td><td><span class="evidence-tag evidence-documentary">Documentary</span></td></tr>
                </tbody>
            </table>
        </section>

        <!-- POWERFUL CONNECTIONS -->
        <section id="powerful-connections">
            <h2>5. Powerful Connections <span class="count">""" + str(category_counts.get("political_connections", 0) + category_counts.get("financial_network", 0)) + """ entities</span></h2>

            <h3>Political Connections</h3>
            <div class="entity-grid">"""

    political_entities = [
        {"name": "Bill Clinton", "type": "person", "class": "political", "desc": "42nd US President. 26+ documented flights on Epstein's 'Lolita Express.' Visited NYC townhouse. Clinton Foundation connections. Denies visiting island. Flight logs show extensive travel with Epstein."},
        {"name": "Donald Trump", "type": "person", "class": "political", "desc": "45th US President. Long-time acquaintance. Quoted: 'terrific guy...likes beautiful women as much as I do, many on the younger side.' 14 phone numbers in Epstein's directory. Virginia Giuffre recruited at Trump's Mar-a-Lago. Reportedly banned Epstein after incident."},
        {"name": "Prince Andrew", "type": "person", "class": "political", "desc": "Duke of York. Virginia Giuffre alleged trafficked to have sex with him ages 16-17 in London, NYC, Virgin Islands. Famous photo with arm around Giuffre. Settled civil lawsuit February 2022 for ~£12 million. Friend of Ghislaine Maxwell."},
        {"name": "Bill Richardson", "type": "person", "class": "political", "desc": "Former New Mexico Governor and UN Ambassador. Visited Zorro Ranch. Appeared in flight logs. Giuffre alleged directed to have sex with Richardson (denied). Died August 2023."},
        {"name": "Alex Acosta", "type": "person", "class": "political", "desc": "US Attorney who approved 2008 Non-Prosecution Agreement. Later Trump Labor Secretary (2017-2019). Resigned July 2019 after Miami Herald exposed NPA. Claimed told to back off because Epstein 'belonged to intelligence.'"}
    ]

    for e in political_entities:
        html += f"""
                <div class="entity-card political">
                    <div class="name">{e['name']}</div>
                    <span class="type">{e['type']}</span>
                    <div class="description">{e['desc']}</div>
                </div>"""

    html += """
            </div>

            <h3>Financial Connections</h3>
            <div class="entity-grid">"""

    financial_entities = [
        {"name": "Leslie Wexner", "type": "person", "class": "financial", "desc": "L Brands founder (Victoria's Secret). Epstein's only confirmed billionaire client. Granted Epstein full power of attorney 1991. Transferred $77M NYC mansion. Co-founded Mega Group. Claims severed ties 2007. $46M+ allegedly misappropriated."},
        {"name": "Glenn Dubin", "type": "person", "class": "financial", "desc": "Highbridge Capital founder. Epstein facilitated $1.3B sale to JPMorgan, received $15M fee. Wife Eva dated Epstein for decade. Children called Epstein 'Uncle Jeff.' Hosted Epstein for Thanksgiving 2009 post-conviction. Virginia Giuffre alleged directed to have sex with him (denied)."},
        {"name": "Leon Black", "type": "person", "class": "financial", "desc": "Apollo Global Management co-founder. Paid Epstein $158 million for 'tax advice' 2012-2017. Stepped down from Apollo 2021 amid scrutiny. Denied knowledge of Epstein's crimes."},
        {"name": "Jes Staley", "type": "person", "class": "financial", "desc": "Former Barclays CEO (2015-2021). Close relationship with Epstein spanning years. 1,200+ emails exchanged. Epstein facilitated meeting with UK Chancellor. Resigned after FCA investigation into Epstein ties."},
        {"name": "Larry Summers", "type": "person", "class": "financial", "desc": "Former Treasury Secretary, Harvard President. Named as successor executor in Epstein's 2014 will. Flew on Epstein's plane 4+ times. Visited Little St. James 2005. Granted Epstein office on Harvard campus. Resigned from multiple boards 2025 after document revelations."}
    ]

    for e in financial_entities:
        html += f"""
                <div class="entity-card financial">
                    <div class="name">{e['name']}</div>
                    <span class="type">{e['type']}</span>
                    <div class="description">{e['desc']}</div>
                </div>"""

    html += """
            </div>
        </section>

        <!-- LEGAL HISTORY -->
        <section id="legal-history">
            <h2>6. Legal History <span class="count">""" + str(category_counts.get("legal_law_enforcement", 0)) + """ entities</span></h2>

            <h3>2005-2008 Florida Investigation</h3>
            <div class="key-finding">
                <strong>The Sweetheart Deal</strong>
                Despite police identifying 40+ victims, Epstein received a 13-month work-release
                sentence. Four co-conspirators received immunity. Victims were not notified
                (CVRA violation). US Attorney Acosta later claimed he was told Epstein
                "belonged to intelligence."
            </div>

            <div class="entity-grid">"""

    legal_entities = [
        {"name": "Michael Reiter", "type": "person", "class": "legal", "desc": "Palm Beach Police Chief who led initial 2005-2006 investigation. Identified 40+ victims. Wrote letter criticizing State Attorney Krischer for reducing charges. Called for FBI involvement."},
        {"name": "Joseph Recarey", "type": "person", "class": "legal", "desc": "Palm Beach Police Detective who conducted primary investigation. Interviewed dozens of victims. Gathered extensive evidence. Died May 2018."},
        {"name": "Barry Krischer", "type": "person", "class": "legal", "desc": "Palm Beach State Attorney who presented case to grand jury resulting in single prostitution charge instead of sex trafficking. Police chief Reiter publicly criticized his handling."},
        {"name": "Alan Dershowitz", "type": "person", "class": "legal", "desc": "Harvard Law Professor. Key defense strategist for 2008 NPA. Met with Acosta to argue against federal jurisdiction. Later accused by Giuffre (denied). Lengthy litigation with Boies/Giuffre, settled 2022."},
        {"name": "Bradley Edwards", "type": "person", "class": "legal", "desc": "Victims' attorney who fought for decade to expose NPA violations. Filed CVRA lawsuit. Wrote book 'Relentless Pursuit.' Key figure in bringing case back to public attention."}
    ]

    for e in legal_entities:
        html += f"""
                <div class="entity-card legal">
                    <div class="name">{e['name']}</div>
                    <span class="type">{e['type']}</span>
                    <div class="description">{e['desc']}</div>
                </div>"""

    html += """
            </div>

            <h3>Defense Team (2008 NPA)</h3>
            <ul>
                <li><strong>Alan Dershowitz</strong> - Harvard Law Professor, key strategist</li>
                <li><strong>Gerald Lefcourt</strong> - Criminal defense attorney, initial contact with Acosta's office</li>
                <li><strong>Jay Lefkowitz</strong> - Kirkland & Ellis partner, private meeting with Acosta</li>
                <li><strong>Ken Starr</strong> - Former Special Prosecutor, "dream team" member</li>
                <li><strong>Roy Black</strong> - Miami defense attorney</li>
            </ul>

            <h3>Maxwell Trial (2021-2022)</h3>
            <ul>
                <li><strong>Verdict:</strong> December 29, 2021 - Convicted on 5 of 6 counts</li>
                <li><strong>Sentence:</strong> 20 years (June 28, 2022)</li>
                <li><strong>Key Witnesses:</strong> Annie Farmer, "Jane," "Kate," "Carolyn"</li>
            </ul>
        </section>

        <!-- DEATH INVESTIGATION -->
        <section id="death-investigation">
            <h2>7. Death Investigation</h2>

            <div class="key-finding">
                <strong>Unexplained Circumstances</strong>
                Multiple security failures occurred simultaneously: two cameras malfunctioned,
                guards falsified logs for 8 hours, Epstein was alone despite suicide watch removal,
                hyoid bone broken in three places (unusual for hanging).
            </div>

            <h3>Timeline of Final Days</h3>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-date">July 23, 2019</div>
                    <div class="timeline-event">First apparent suicide attempt. Found semiconscious with marks on neck. Placed on suicide watch.</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">July 29, 2019</div>
                    <div class="timeline-event">Removed from suicide watch after only 6 days. Cellmate (Nicholas Tartaglione, former police officer charged with 4 murders) removed.</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">August 9, 2019</div>
                    <div class="timeline-event">New documents unsealed identifying prominent names. Epstein meets with attorneys for several hours. Returns to cell in evening.</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">August 10, 2019 - 6:30 AM</div>
                    <div class="timeline-event">Guards Tova Noel and Michael Thomas discover Epstein unresponsive. CPR attempted. Pronounced dead at hospital.</div>
                </div>
            </div>

            <h3>Security Failures</h3>
            <ul>
                <li>Two cameras outside cell malfunctioned (one unusable, one corrupted)</li>
                <li>Guards failed to perform required 30-minute checks for ~8 hours</li>
                <li>Guards allegedly slept and browsed internet; falsified logs</li>
                <li>Epstein left without cellmate despite protocol</li>
                <li>Removed from suicide watch after only 6 days</li>
                <li>Bedsheets capable of supporting hanging not removed</li>
            </ul>

            <h3>Medical Findings</h3>
            <ul>
                <li><strong>Official ruling:</strong> Suicide by hanging</li>
                <li><strong>Hyoid bone:</strong> Broken in three places (unusual for hanging, more common in strangulation)</li>
                <li><strong>Independent review:</strong> Dr. Michael Baden (hired by Epstein family) disputed suicide finding</li>
            </ul>
        </section>

        <!-- VICTIMS -->
        <section id="victims">
            <h2>8. Victims & Survivors <span class="count">""" + str(category_counts.get("victims_survivors", 0)) + """ entities</span></h2>

            <h3>Key Accusers and Witnesses</h3>
            <div class="entity-grid">"""

    victim_entities = [
        {"name": "Virginia Giuffre", "type": "person", "class": "victim", "desc": "Primary public accuser. Recruited age 16 at Mar-a-Lago by Maxwell. Alleged trafficked to Prince Andrew, Dershowitz, Richardson, Dubin, others. Civil suits settled. Founded Victims Refuse Silence. Died April 25, 2025 by suicide in Australia."},
        {"name": "Courtney Wild", "type": "person", "class": "victim", "desc": "Lead petitioner challenging NPA. Abused starting age 14 (2001). Filed landmark Jane Doe 1 v. United States challenging secret plea deal. Decade-long legal fight helped expose CVRA violations."},
        {"name": "Annie Farmer", "type": "person", "class": "victim", "desc": "Maxwell trial witness ('Accuser Number Four'). Abused age 16 at Zorro Ranch in 1996. Sister of Maria Farmer. Testified Maxwell posed as 'chaperone' then participated in grooming. Received $1.5M from Victims' Compensation Fund."},
        {"name": "Maria Farmer", "type": "person", "class": "victim", "desc": "Artist employed by Epstein. One of first to report abuse to FBI (1996) but was not believed. Sister of Annie Farmer. Reported surveillance equipment throughout Epstein properties."},
        {"name": "Sarah Ransome", "type": "person", "class": "victim", "desc": "Abused 2006-2007 on Little St. James. Described Maxwell as 'aristocratic pimp.' Filed civil lawsuit (settled 2018). Delivered victim impact statement at Maxwell's 2022 sentencing."},
        {"name": "Haley Robson", "type": "person", "class": "victim", "desc": "Recruited as 16-year-old victim in 2002, later became key recruiter in Palm Beach. Appeared at Capitol Hill 2025 advocating for release of Epstein files."}
    ]

    for e in victim_entities:
        html += f"""
                <div class="entity-card victim">
                    <div class="name">{e['name']}</div>
                    <span class="type">{e['type']}</span>
                    <div class="description">{e['desc']}</div>
                </div>"""

    html += """
            </div>

            <h3>Settlements and Compensation</h3>
            <table>
                <thead>
                    <tr><th>Program/Settlement</th><th>Amount</th><th>Details</th></tr>
                </thead>
                <tbody>
                    <tr><td>Epstein Victims' Compensation Program</td><td>~$125 million</td><td>Administered by Jordana Feldman; 150+ claimants</td></tr>
                    <tr><td>Giuffre v. Prince Andrew</td><td>~£12 million</td><td>February 2022 settlement</td></tr>
                    <tr><td>JPMorgan Chase Settlement</td><td>$290 million</td><td>2023 class action for enabling crimes</td></tr>
                    <tr><td>Deutsche Bank Settlement</td><td>$75 million</td><td>2023 settlement for processing transactions</td></tr>
                </tbody>
            </table>
        </section>

        <!-- DOCUMENTARY EVIDENCE -->
        <section id="documentary-evidence">
            <h2>9. Documentary Evidence</h2>

            <h3>Key Source Documents</h3>
            <table>
                <thead>
                    <tr><th>Document</th><th>Content</th><th>Key Evidence</th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td>HOUSE_OVERSIGHT_030589.txt</td>
                        <td>Mail on Sunday article/allegations</td>
                        <td>Surveillance cameras evidence; Ehud Barak allegations; Victim names sent to Maxwell's lawyer</td>
                    </tr>
                    <tr>
                        <td>HOUSE_OVERSIGHT_010887.txt</td>
                        <td>Virginia Giuffre declaration</td>
                        <td>Blackmail testimony; Named powerful individuals</td>
                    </tr>
                    <tr>
                        <td>HOUSE_OVERSIGHT_010486.txt</td>
                        <td>Perversion of Justice materials</td>
                        <td>Hoffenberg/Bear Stearns connection; Career origins</td>
                    </tr>
                    <tr>
                        <td>HOUSE_OVERSIGHT_017771.txt</td>
                        <td>Vanity Fair investigation</td>
                        <td>Epstein's mysterious wealth; Celebrity connections</td>
                    </tr>
                    <tr>
                        <td>Flight Logs</td>
                        <td>Aircraft manifests</td>
                        <td>Clinton 26+ flights; Multiple celebrities; Victim transport</td>
                    </tr>
                </tbody>
            </table>

            <h3>Data Sources</h3>
            <ul>
                <li><strong>TrumpEpsteinFiles Archive:</strong> 1,998 documents from House Oversight releases</li>
                <li><strong>Giuffre v. Maxwell:</strong> Unsealed depositions and exhibits</li>
                <li><strong>Florida Grand Jury Records:</strong> Released per HB 117 (2024)</li>
                <li><strong>Palm Beach Police Files:</strong> Case 05-368 investigation records</li>
                <li><strong>SDNY Indictment:</strong> July 2019 sex trafficking charges</li>
            </ul>
        </section>

        <!-- OPEN QUESTIONS -->
        <section id="open-questions">
            <h2>10. Open Questions & Investigation Gaps</h2>

            <h3>Unexplained Wealth</h3>
            <ul>
                <li>Epstein claimed to manage money only for billionaires ($1B minimum), yet only Wexner is confirmed</li>
                <li>Source of initial wealth after leaving Bear Stearns (1981) unclear</li>
                <li>$200+ million in assets at death despite unclear revenue streams</li>
                <li>$46+ million allegedly misappropriated from Wexner</li>
                <li>Financial Trust Company records remain largely sealed</li>
            </ul>

            <h3>Intelligence Questions</h3>
            <ul>
                <li>What was Acosta told about Epstein "belonging to intelligence"?</li>
                <li>What was the purpose of the surveillance recordings?</li>
                <li>What is the full extent of Robert Maxwell's intelligence connections?</li>
                <li>Why did Epstein have an Israeli passport in a false name?</li>
                <li>What was the nature of Epstein's relationship with Ehud Barak?</li>
            </ul>

            <h3>Unprosecuted Co-Conspirators</h3>
            <table>
                <thead>
                    <tr><th>Name</th><th>Alleged Role</th><th>Status</th></tr>
                </thead>
                <tbody>
                    <tr><td>Sarah Kellen</td><td>Primary scheduler/facilitator</td><td>Immunity (2008); never charged</td></tr>
                    <tr><td>Lesley Groff</td><td>Executive assistant/logistics</td><td>Immunity (2008); never charged</td></tr>
                    <tr><td>Adriana Ross</td><td>Assistant/recruiter</td><td>Immunity (2008); never charged</td></tr>
                    <tr><td>Nadia Marcinkova</td><td>Victim-turned-participant</td><td>Immunity (2008); never charged</td></tr>
                </tbody>
            </table>

            <h3>Death Investigation Questions</h3>
            <ul>
                <li>Why were both cameras malfunctioning simultaneously?</li>
                <li>Why was Epstein removed from suicide watch after only 6 days?</li>
                <li>Why was his cellmate removed against protocol?</li>
                <li>How did guards falsify logs for 8 hours without detection?</li>
                <li>Why was hyoid bone broken in three places?</li>
                <li>What documents were unsealed hours before his death?</li>
            </ul>

            <h3>Unreleased Materials</h3>
            <ul>
                <li>Complete flight logs</li>
                <li>Surveillance recordings (if they exist)</li>
                <li>Full client list from Financial Trust Company</li>
                <li>FBI investigation files</li>
                <li>Grand jury testimony (partially released)</li>
                <li>Complete "black book" contents</li>
            </ul>
        </section>

        <footer>
            <p><strong>Data Sources:</strong> TrumpEpsteinFiles Archive (1,998 documents) | 17 Import Batches | """ + str(data["stats"]["total_entities"]) + """ Knowledge Base Entities</p>
            <p><strong>Generated:</strong> """ + datetime.now().strftime("%B %d, %Y at %H:%M") + """</p>
            <p><strong>Methodology:</strong> Documentary evidence extraction combined with contextual research and knowledge enrichment</p>
            <p><strong>Disclaimer:</strong> This report compiles publicly available information. Allegations against individuals who have not been convicted should be treated as unproven claims.</p>
        </footer>
    </div>

    <script>
        // Collapsible sections
        document.querySelectorAll('.collapsible').forEach(item => {
            item.addEventListener('click', function() {
                this.classList.toggle('active');
                const content = this.nextElementSibling;
                content.classList.toggle('show');
            });
        });

        // Smooth scroll for TOC links
        document.querySelectorAll('.toc a').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        });
    </script>
</body>
</html>"""

    return html


def main():
    print("=" * 70)
    print("COMPREHENSIVE EPSTEIN INVESTIGATION REPORT GENERATOR")
    print("=" * 70)

    client = get_supabase_client()

    # Fetch all data
    print("\n[1/3] Fetching data from database...")
    data = get_all_data(client)

    # Generate HTML report
    print("\n[2/3] Generating HTML report...")
    html = generate_html_report(data)

    # Save report
    output_path = "../EPSTEIN_COMPREHENSIVE_REPORT.html"
    print(f"\n[3/3] Saving report to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print("\n" + "=" * 70)
    print("REPORT GENERATED SUCCESSFULLY")
    print("=" * 70)
    print(f"Output: {output_path}")
    print(f"Entities included: {data['stats']['total_entities']}")


if __name__ == "__main__":
    main()
