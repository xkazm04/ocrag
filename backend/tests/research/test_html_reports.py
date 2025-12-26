"""HTML Report Generation Test with Rich Mock Data.

This test generates HTML reports using OpenRouter Gemini, providing rich structured
data for the LLM to compose beautiful, valuable reports.

Run with: python tests/research/test_html_reports.py
Requires: OPENROUTER_API_KEY environment variable
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, List

# Setup paths
_script_dir = Path(__file__).parent
_backend_dir = _script_dir.parent.parent
_project_root = _backend_dir.parent
_results_dir = _script_dir / "results" / "reports" / "html"
sys.path.insert(0, str(_backend_dir))

# Load .env file
_env_file = _project_root / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_results_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DESIGN SYSTEM - CSS Component Library
# =============================================================================

DESIGN_SYSTEM_CSS = """
/* === DESIGN SYSTEM === */
/* A curated set of reusable CSS patterns for professional reports */

:root {
  /* Theme Colors - Will be overridden per template */
  --ds-primary: #1a365d;
  --ds-accent: #3182ce;
  --ds-success: #38a169;
  --ds-warning: #d69e2e;
  --ds-danger: #e53e3e;
  --ds-bg: #ffffff;
  --ds-bg-subtle: #f7fafc;
  --ds-bg-card: #ffffff;
  --ds-border: #e2e8f0;
  --ds-text: #2d3748;
  --ds-text-muted: #718096;
  --ds-radius: 8px;
  --ds-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
  --ds-shadow-lg: 0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  line-height: 1.6;
  color: var(--ds-text);
  background: var(--ds-bg);
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

/* === TYPOGRAPHY === */
h1, h2, h3, h4 { color: var(--ds-primary); margin-top: 1.5rem; margin-bottom: 0.75rem; font-weight: 600; }
h1 { font-size: 2.25rem; border-bottom: 3px solid var(--ds-accent); padding-bottom: 0.5rem; }
h2 { font-size: 1.75rem; border-bottom: 1px solid var(--ds-border); padding-bottom: 0.25rem; }
h3 { font-size: 1.25rem; }
h4 { font-size: 1.1rem; }
p { margin-bottom: 1rem; }
a { color: var(--ds-accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* === CARDS === */
.ds-card {
  background: var(--ds-bg-card);
  border-radius: var(--ds-radius);
  box-shadow: var(--ds-shadow);
  padding: 1.5rem;
  margin-bottom: 1rem;
}

.ds-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--ds-border);
}

/* === METRIC CARDS === */
.ds-metric-card {
  background: var(--ds-bg-card);
  border-radius: var(--ds-radius);
  box-shadow: var(--ds-shadow);
  padding: 1.25rem 1.5rem;
  text-align: center;
  display: inline-block;
  min-width: 160px;
}
.ds-metric-card .value {
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--ds-accent);
  line-height: 1.2;
}
.ds-metric-card .label {
  font-size: 0.875rem;
  color: var(--ds-text-muted);
  margin-top: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.ds-metric-card .change {
  font-size: 0.875rem;
  font-weight: 500;
  margin-top: 0.5rem;
}
.ds-metric-card .change.positive { color: var(--ds-success); }
.ds-metric-card .change.negative { color: var(--ds-danger); }

/* === BADGES & TAGS === */
.ds-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.ds-badge.success { background: #c6f6d5; color: #22543d; }
.ds-badge.warning { background: #fefcbf; color: #744210; }
.ds-badge.danger { background: #fed7d7; color: #822727; }
.ds-badge.info { background: #bee3f8; color: #2a4365; }
.ds-badge.neutral { background: var(--ds-bg-subtle); color: var(--ds-text-muted); }

.ds-tag {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  background: var(--ds-bg-subtle);
  border-radius: 4px;
  font-size: 0.75rem;
  color: var(--ds-text-muted);
  margin-right: 0.25rem;
}

/* === CONFIDENCE INDICATORS === */
.ds-confidence {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.ds-confidence .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ds-border);
}
.ds-confidence .dot.filled { background: var(--ds-accent); }
.ds-confidence-bar {
  height: 6px;
  background: var(--ds-border);
  border-radius: 3px;
  overflow: hidden;
  width: 100px;
}
.ds-confidence-bar .fill {
  height: 100%;
  background: var(--ds-accent);
  border-radius: 3px;
}

/* === CALLOUTS & ALERTS === */
.ds-callout {
  padding: 1rem 1.25rem;
  border-radius: var(--ds-radius);
  border-left: 4px solid var(--ds-accent);
  background: var(--ds-bg-subtle);
  margin: 1rem 0;
}
.ds-callout.info { border-left-color: var(--ds-accent); background: #ebf8ff; }
.ds-callout.success { border-left-color: var(--ds-success); background: #f0fff4; }
.ds-callout.warning { border-left-color: var(--ds-warning); background: #fffaf0; }
.ds-callout.danger { border-left-color: var(--ds-danger); background: #fff5f5; }
.ds-callout-title {
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--ds-primary);
}

/* === TABLES === */
.ds-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border-radius: var(--ds-radius);
  overflow: hidden;
  box-shadow: var(--ds-shadow);
  margin: 1rem 0;
}
.ds-table th {
  background: var(--ds-primary);
  color: white;
  font-weight: 600;
  padding: 0.875rem 1rem;
  text-align: left;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.ds-table td {
  padding: 0.875rem 1rem;
  border-bottom: 1px solid var(--ds-border);
  background: var(--ds-bg-card);
}
.ds-table tr:last-child td { border-bottom: none; }
.ds-table tr:hover td { background: var(--ds-bg-subtle); }

/* === TIMELINE === */
.ds-timeline {
  position: relative;
  padding-left: 2.5rem;
  margin: 1.5rem 0;
}
.ds-timeline::before {
  content: '';
  position: absolute;
  left: 0.5rem;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(to bottom, var(--ds-accent), var(--ds-border));
}
.ds-timeline-item {
  position: relative;
  padding-bottom: 1.5rem;
}
.ds-timeline-item::before {
  content: '';
  position: absolute;
  left: -2.15rem;
  top: 0.35rem;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--ds-accent);
  border: 3px solid var(--ds-bg);
  box-shadow: 0 0 0 2px var(--ds-accent);
}
.ds-timeline-date {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--ds-accent);
  margin-bottom: 0.25rem;
}
.ds-timeline-title {
  font-weight: 600;
  color: var(--ds-primary);
}
.ds-timeline-content {
  color: var(--ds-text-muted);
  font-size: 0.9375rem;
  margin-top: 0.25rem;
}

/* === PROFILE/ACTOR CARDS === */
.ds-profile {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}
.ds-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--ds-accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.25rem;
  flex-shrink: 0;
}
.ds-profile-info { flex: 1; }
.ds-profile-name {
  font-weight: 600;
  font-size: 1.125rem;
  color: var(--ds-primary);
}
.ds-profile-role {
  color: var(--ds-text-muted);
  font-size: 0.875rem;
}

/* === GRID LAYOUTS === */
.ds-grid { display: grid; gap: 1.5rem; margin: 1rem 0; }
.ds-grid-2 { grid-template-columns: repeat(2, 1fr); }
.ds-grid-3 { grid-template-columns: repeat(3, 1fr); }
.ds-grid-4 { grid-template-columns: repeat(4, 1fr); }
.ds-flex { display: flex; gap: 1rem; flex-wrap: wrap; }

/* === SECTION DIVIDERS === */
.ds-divider {
  border: none;
  height: 1px;
  background: var(--ds-border);
  margin: 2rem 0;
}

/* === STATS ROW === */
.ds-stats-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin: 1.5rem 0;
}

/* === PRINT STYLES === */
@media print {
  body { max-width: 100%; padding: 1rem; background: white; }
  .ds-card, .ds-metric-card { box-shadow: none; border: 1px solid #ddd; }
  .no-print { display: none; }
}

/* === RESPONSIVE === */
@media (max-width: 768px) {
  .ds-grid-2, .ds-grid-3, .ds-grid-4 { grid-template-columns: 1fr; }
  .ds-stats-row { flex-direction: column; }
  body { padding: 1rem; }
}
"""

# =============================================================================
# TEMPLATE THEMES - CSS Variable Overrides
# =============================================================================

TEMPLATE_THEMES = {
    "investigative": """
/* INVESTIGATIVE THEME: Newspaper-inspired, serious, evidence-focused */
:root {
  --ds-primary: #1a202c;
  --ds-accent: #2b6cb0;
  --ds-success: #38a169;
  --ds-warning: #dd6b20;
  --ds-danger: #c53030;
  --ds-bg: #ffffff;
  --ds-bg-subtle: #f7fafc;
  --ds-bg-card: #ffffff;
  --ds-border: #e2e8f0;
  --ds-text: #1a202c;
  --ds-text-muted: #4a5568;
}
body { font-family: 'Georgia', 'Times New Roman', serif; }
h1, h2, h3, h4 { font-family: 'Segoe UI', system-ui, sans-serif; }
""",

    "competitive": """
/* COMPETITIVE THEME: Modern SaaS dashboard, analytical */
:root {
  --ds-primary: #1e3a5f;
  --ds-accent: #4299e1;
  --ds-success: #48bb78;
  --ds-warning: #ed8936;
  --ds-danger: #fc8181;
  --ds-bg: #f8fafc;
  --ds-bg-subtle: #edf2f7;
  --ds-bg-card: #ffffff;
  --ds-border: #e2e8f0;
  --ds-text: #2d3748;
  --ds-text-muted: #718096;
}
""",

    "financial": """
/* FINANCIAL THEME: Bloomberg-inspired, data-dense, dark mode */
:root {
  --ds-primary: #00d4aa;
  --ds-accent: #00d4aa;
  --ds-success: #00d4aa;
  --ds-warning: #f6ad55;
  --ds-danger: #fc8181;
  --ds-bg: #0d1421;
  --ds-bg-subtle: #1a2332;
  --ds-bg-card: #1a2332;
  --ds-border: #2d3748;
  --ds-text: #e2e8f0;
  --ds-text-muted: #a0aec0;
  --ds-shadow: 0 2px 4px rgba(0,0,0,0.3);
}
body { background: #0d1421; }
.ds-table th { background: #2d3748; }
.ds-badge.success { background: #1a4731; color: #9ae6b4; }
.ds-badge.danger { background: #742a2a; color: #feb2b2; }
.ds-badge.warning { background: #744210; color: #fbd38d; }
.ds-badge.info { background: #2a4365; color: #90cdf4; }
.ds-callout { background: #1a2332; }
.ds-callout.info { background: #1a365d; border-left-color: #4299e1; }
.ds-callout.success { background: #1a4731; border-left-color: #48bb78; }
.ds-callout.warning { background: #744210; border-left-color: #ed8936; }
.ds-callout.danger { background: #742a2a; border-left-color: #fc8181; }
""",

    "legal": """
/* LEGAL THEME: Traditional, authoritative, minimal */
:root {
  --ds-primary: #1a1a1a;
  --ds-accent: #8b0000;
  --ds-success: #2f855a;
  --ds-warning: #c05621;
  --ds-danger: #9b2c2c;
  --ds-bg: #ffffff;
  --ds-bg-subtle: #f9f9f9;
  --ds-bg-card: #ffffff;
  --ds-border: #d1d1d1;
  --ds-text: #1a1a1a;
  --ds-text-muted: #4a4a4a;
  --ds-radius: 2px;
  --ds-shadow: none;
}
body { font-family: 'Georgia', 'Times New Roman', serif; max-width: 900px; }
h1, h2, h3, h4 { font-family: 'Georgia', serif; }
.ds-card { border: 1px solid var(--ds-border); box-shadow: none; }
.ds-table { box-shadow: none; border: 1px solid var(--ds-border); }
.ds-table th { background: #f5f5f5; color: var(--ds-text); }
"""
}

# =============================================================================
# VISUAL RECIPES - Concrete HTML patterns for LLM to use
# =============================================================================

VISUAL_RECIPES = """
## VISUAL RECIPES - Use these patterns in your HTML:

### 1. METRIC CARD (for key statistics)
```html
<div class="ds-metric-card">
  <div class="value">$35.1B</div>
  <div class="label">Revenue</div>
  <div class="change positive">▲ +94% YoY</div>
</div>
```

### 2. STATS ROW (multiple metrics in a row)
```html
<div class="ds-stats-row">
  <div class="ds-metric-card">
    <div class="value">156</div>
    <div class="label">Sources</div>
  </div>
  <div class="ds-metric-card">
    <div class="value">47 min</div>
    <div class="label">Duration</div>
  </div>
</div>
```

### 3. BADGE for status/confidence
```html
<span class="ds-badge success">High Confidence</span>
<span class="ds-badge warning">Medium Risk</span>
<span class="ds-badge danger">Critical</span>
<span class="ds-badge info">In Progress</span>
```

### 4. CONFIDENCE DOTS (visual 1-5 rating)
```html
<span class="ds-confidence">
  <span class="dot filled"></span>
  <span class="dot filled"></span>
  <span class="dot filled"></span>
  <span class="dot"></span>
  <span class="dot"></span>
</span>
```

### 5. CALLOUT for key findings/warnings
```html
<div class="ds-callout info">
  <div class="ds-callout-title">Key Finding</div>
  Customer funds totaling $8-10B were secretly transferred to Alameda Research.
</div>
<div class="ds-callout warning">
  <div class="ds-callout-title">Warning</div>
  This finding has medium confidence and requires verification.
</div>
```

### 6. PROFILE/ACTOR CARD
```html
<div class="ds-card">
  <div class="ds-profile">
    <div class="ds-avatar">SBF</div>
    <div class="ds-profile-info">
      <div class="ds-profile-name">Sam Bankman-Fried</div>
      <div class="ds-profile-role">Founder & CEO, FTX</div>
      <div style="margin-top: 0.5rem;">
        <span class="ds-badge danger">Serving 25-year sentence</span>
      </div>
    </div>
  </div>
</div>
```

### 7. TIMELINE for chronological events
```html
<div class="ds-timeline">
  <div class="ds-timeline-item">
    <div class="ds-timeline-date">November 2, 2022</div>
    <div class="ds-timeline-title">CoinDesk Exposé Published</div>
    <div class="ds-timeline-content">Article reveals Alameda's FTT exposure, triggering crisis.</div>
  </div>
  <div class="ds-timeline-item">
    <div class="ds-timeline-date">November 11, 2022</div>
    <div class="ds-timeline-title">FTX Files Bankruptcy</div>
    <div class="ds-timeline-content">FTX and 130 affiliates file Chapter 11.</div>
  </div>
</div>
```

### 8. DATA TABLE
```html
<table class="ds-table">
  <thead>
    <tr>
      <th>Metric</th>
      <th>Value</th>
      <th>Change</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Revenue</td>
      <td>$35.1B</td>
      <td><span class="ds-badge success">+94%</span></td>
    </tr>
  </tbody>
</table>
```

### 9. CARD WITH HEADER
```html
<div class="ds-card">
  <div class="ds-card-header">
    <h3 style="margin:0">Section Title</h3>
    <span class="ds-badge info">4 items</span>
  </div>
  <p>Card content goes here...</p>
</div>
```

### 10. GRID LAYOUT for cards
```html
<div class="ds-grid ds-grid-3">
  <div class="ds-card">Card 1</div>
  <div class="ds-card">Card 2</div>
  <div class="ds-card">Card 3</div>
</div>
```
"""

# Legacy compatibility
BASE_CSS = """
:root {
    --primary: #1a1a2e;
    --secondary: #16213e;
    --accent: #0f3460;
    --success: #4caf50;
    --warning: #ff9800;
    --danger: #f44336;
    --text: #333;
    --text-light: #666;
    --bg: #fff;
    --bg-alt: #f8f9fa;
    --border: #e0e0e0;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    line-height: 1.6;
    color: var(--text);
    background: var(--bg);
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

h1, h2, h3, h4 {
    color: var(--primary);
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
}

h1 { font-size: 2.25rem; border-bottom: 3px solid var(--accent); padding-bottom: 0.5rem; }
h2 { font-size: 1.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.25rem; }
h3 { font-size: 1.25rem; }

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
}

th, td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
}

th {
    background: var(--bg-alt);
    font-weight: 600;
}

.metric-card {
    display: inline-block;
    padding: 1rem 1.5rem;
    background: var(--bg-alt);
    border-radius: 8px;
    margin: 0.5rem;
    text-align: center;
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
}

.metric-label {
    font-size: 0.875rem;
    color: var(--text-light);
}

.confidence-high { color: var(--success); }
.confidence-medium { color: var(--warning); }
.confidence-low { color: var(--danger); }

.callout {
    padding: 1rem;
    border-left: 4px solid var(--accent);
    background: var(--bg-alt);
    margin: 1rem 0;
}

.source-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    background: var(--bg-alt);
}

a { color: var(--accent); }

@media print {
    body { max-width: 100%; padding: 0; }
    .no-print { display: none; }
}
"""


# =============================================================================
# RICH MOCK DATA - Much more detailed for LLM to work with
# =============================================================================

def create_rich_investigative_data() -> Dict[str, Any]:
    """Create highly detailed investigative research data."""
    return {
        "session_id": str(uuid4()),
        "session_title": "FTX Collapse: Complete Timeline and Actor Analysis",
        "session_query": "What led to the collapse of FTX cryptocurrency exchange and who were the key players involved in the fraud?",
        "template_type": "investigative",
        "status": "completed",
        "research_duration_minutes": 47,
        "total_sources_analyzed": 156,
        "parameters": {
            "depth": "comprehensive",
            "time_scope": "2019-2024",
            "geographic_focus": "Bahamas, United States"
        },
        "created_at": datetime.now() - timedelta(hours=3),
        "completed_at": datetime.now(),

        "executive_summary": """This investigation reveals a systematic fraud operation at FTX cryptocurrency exchange that resulted in approximately $8-10 billion in missing customer funds. The collapse, triggered in November 2022, exposed a web of interconnected entities, regulatory failures, and deliberate misrepresentation to investors. Key findings indicate that customer deposits were secretly transferred to Alameda Research, a trading firm also controlled by FTX founder Sam Bankman-Fried, to cover trading losses and fund personal ventures.""",

        "key_timeline_events": [
            {"date": "2017-11-01", "title": "Alameda Research Founded", "description": "Sam Bankman-Fried founds Alameda Research, a quantitative cryptocurrency trading firm.", "significance": "Foundation of the entity that would later receive misappropriated FTX funds", "confidence": 0.99},
            {"date": "2019-05-01", "title": "FTX Exchange Launch", "description": "FTX cryptocurrency derivatives exchange launches, marketed as 'built by traders, for traders'.", "significance": "Beginning of the FTX operation with initial venture funding", "confidence": 0.99},
            {"date": "2021-07-20", "title": "Series B Funding Round", "description": "FTX raises $900 million at $18 billion valuation from Paradigm, Sequoia Capital, and others.", "significance": "Major institutional validation despite lack of traditional oversight", "confidence": 0.97},
            {"date": "2022-01-14", "title": "Series C at $32B Valuation", "description": "FTX raises $400 million, valuing the company at $32 billion.", "significance": "Peak valuation before collapse, invested by sophisticated parties", "confidence": 0.98},
            {"date": "2022-11-02", "title": "CoinDesk Exposé Published", "description": "CoinDesk publishes article revealing Alameda Research's balance sheet heavily weighted with FTT tokens.", "significance": "First public exposure of the FTX-Alameda interconnection risks", "confidence": 0.99},
            {"date": "2022-11-06", "title": "Binance Announces FTT Sale", "description": "Binance CEO CZ announces plan to liquidate $580 million in FTT holdings.", "significance": "Trigger event for bank run on FTX", "confidence": 0.99},
            {"date": "2022-11-08", "title": "FTX Halts Withdrawals", "description": "FTX stops processing customer withdrawal requests citing liquidity issues.", "significance": "Confirmation that customer funds were not available", "confidence": 0.99},
            {"date": "2022-11-11", "title": "FTX Files Bankruptcy", "description": "FTX, FTX US, and 130 affiliated companies file Chapter 11 bankruptcy.", "significance": "Largest cryptocurrency company failure in history", "confidence": 1.0},
            {"date": "2022-12-12", "title": "SBF Arrested in Bahamas", "description": "Sam Bankman-Fried arrested at his Bahamas residence on US federal charges.", "significance": "Criminal accountability begins", "confidence": 1.0},
            {"date": "2024-03-28", "title": "SBF Sentenced", "description": "Sam Bankman-Fried sentenced to 25 years in federal prison.", "significance": "One of the longest white-collar crime sentences in US history", "confidence": 1.0}
        ],

        "actors": [
            {
                "name": "Sam Bankman-Fried (SBF)",
                "role": "Founder & CEO, FTX",
                "description": "MIT physics graduate who founded Alameda Research and FTX. Known for effective altruism advocacy and political donations.",
                "key_actions": ["Founded both FTX and Alameda Research", "Approved secret transfer of customer funds", "Made $40M in political donations", "Lied to investors about company segregation"],
                "affiliations": ["FTX", "Alameda Research", "FTX Foundation", "Effective Altruism movement"],
                "aliases": ["SBF"],
                "current_status": "Serving 25-year federal prison sentence",
                "confidence": 0.99,
                "photo_available": True
            },
            {
                "name": "Caroline Ellison",
                "role": "CEO, Alameda Research",
                "description": "Stanford mathematics graduate. Led Alameda Research's trading operations and was in a relationship with SBF.",
                "key_actions": ["Directed Alameda trading strategies", "Aware of and facilitated fund transfers from FTX", "Cooperated with prosecutors", "Testified against SBF"],
                "affiliations": ["Alameda Research", "Jane Street (former)"],
                "current_status": "Cooperating witness, awaiting sentencing",
                "confidence": 0.97,
                "photo_available": True
            },
            {
                "name": "Gary Wang",
                "role": "Co-founder & CTO, FTX",
                "description": "MIT graduate, former Google engineer. Built FTX's trading platform including alleged backdoor features.",
                "key_actions": ["Built FTX exchange infrastructure", "Implemented secret 'allow_negative' feature for Alameda", "Cooperating witness"],
                "affiliations": ["FTX", "Google (former)"],
                "current_status": "Cooperating witness, awaiting sentencing",
                "confidence": 0.96,
                "photo_available": True
            },
            {
                "name": "Nishad Singh",
                "role": "Director of Engineering, FTX",
                "description": "UC Berkeley graduate who oversaw FTX's engineering team and was aware of financial irregularities.",
                "key_actions": ["Oversaw technical implementation", "Received loans from Alameda", "Cooperating witness"],
                "affiliations": ["FTX", "Facebook (former)"],
                "current_status": "Cooperating witness, awaiting sentencing",
                "confidence": 0.94,
                "photo_available": False
            },
            {
                "name": "Ryan Salame",
                "role": "Co-CEO, FTX Digital Markets",
                "description": "Led FTX's Bahamian entity and was involved in political donation schemes.",
                "key_actions": ["Managed Bahamian operations", "Made straw donor political contributions", "Pleaded guilty to campaign finance violations"],
                "affiliations": ["FTX Digital Markets"],
                "current_status": "Sentenced to 7.5 years",
                "confidence": 0.93,
                "photo_available": False
            }
        ],

        "relationships": [
            {"from": "Sam Bankman-Fried", "to": "Alameda Research", "type": "ownership", "description": "SBF owned 90% of Alameda Research", "evidence_strength": "strong"},
            {"from": "Sam Bankman-Fried", "to": "FTX", "type": "control", "description": "SBF controlled FTX through ownership structure", "evidence_strength": "strong"},
            {"from": "FTX", "to": "Alameda Research", "type": "fund_transfer", "description": "Approximately $8-10 billion in customer funds secretly transferred", "evidence_strength": "strong"},
            {"from": "Caroline Ellison", "to": "Sam Bankman-Fried", "type": "personal", "description": "On-and-off romantic relationship", "evidence_strength": "confirmed"},
            {"from": "Alameda Research", "to": "FTT Token", "type": "collateral", "description": "Alameda used FTT as collateral for loans, creating circular dependency", "evidence_strength": "strong"},
            {"from": "FTX", "to": "Sequoia Capital", "type": "investor", "description": "Sequoia invested $150M+, later wrote down to zero", "evidence_strength": "confirmed"}
        ],

        "evidence": [
            {"type": "document", "title": "CoinDesk Balance Sheet Article", "description": "Published November 2, 2022 revealing Alameda's FTT exposure", "credibility": 0.95, "source": "CoinDesk"},
            {"type": "testimony", "title": "Caroline Ellison Trial Testimony", "description": "Detailed account of knowing fraud and fund misappropriation", "credibility": 0.98, "source": "US District Court SDNY"},
            {"type": "code", "title": "'allow_negative' Feature", "description": "Secret code allowing Alameda unlimited withdrawals from FTX", "credibility": 0.99, "source": "Gary Wang testimony"},
            {"type": "financial", "title": "Bankruptcy Filing Analysis", "description": "John Ray III's findings showing complete failure of corporate controls", "credibility": 0.97, "source": "Chapter 11 Filing"},
            {"type": "document", "title": "SEC Complaint", "description": "Detailed allegations of securities fraud and misrepresentation", "credibility": 0.98, "source": "SEC.gov"}
        ],

        "findings": [
            {"finding_type": "fact", "content": "FTX customer deposits totaled approximately $16 billion at peak, with $8-10 billion subsequently unaccounted for or transferred to Alameda Research.", "summary": "Massive fund misappropriation", "confidence_score": 0.97, "supporting_sources": 12},
            {"finding_type": "fact", "content": "A secret 'backdoor' in FTX's code allowed Alameda Research to withdraw unlimited funds without triggering normal security alerts.", "summary": "Technical mechanism of fraud", "confidence_score": 0.98, "supporting_sources": 3},
            {"finding_type": "pattern", "content": "FTX operated from the Bahamas specifically to avoid US regulatory oversight while still serving US customers through complex corporate structures.", "summary": "Regulatory arbitrage pattern", "confidence_score": 0.89, "supporting_sources": 8},
            {"finding_type": "fact", "content": "Sam Bankman-Fried made approximately $40 million in political donations to both parties, with some violations of campaign finance laws.", "summary": "Political influence campaign", "confidence_score": 0.94, "supporting_sources": 15},
            {"finding_type": "evidence", "content": "No independent board existed at FTX. SBF, Wang, and Singh made all major decisions without oversight.", "summary": "Complete governance failure", "confidence_score": 0.96, "supporting_sources": 6},
            {"finding_type": "fact", "content": "FTX's terms of service explicitly stated customer funds would not be used for trading, a promise that was systematically violated.", "summary": "Terms of service violation", "confidence_score": 0.99, "supporting_sources": 2},
            {"finding_type": "gap", "content": "The full trail of where misappropriated funds ultimately went remains partially unclear, with ongoing forensic accounting.", "summary": "Fund tracing incomplete", "confidence_score": 0.72, "supporting_sources": 4}
        ],

        "perspectives": [
            {
                "perspective_type": "historical",
                "analyst": "Historical Context Analyst",
                "analysis_text": "The FTX collapse represents one of the largest financial frauds in history, comparable to Enron and Bernie Madoff's scheme. The concentration of power without oversight, combined with a charismatic leader promoting charitable causes, created conditions for massive fraud to go undetected. The 'effective altruism' veneer provided moral cover for actions that ultimately harmed millions.",
                "key_insights": [
                    "Parallels to Enron in governance failures and auditor capture",
                    "Fastest collapse from peak valuation ($32B) to bankruptcy in history",
                    "Cryptocurrency industry's 'move fast and break things' culture enabled fraud",
                    "Media and investors failed to apply basic due diligence"
                ],
                "recommendations": [
                    "Implement mandatory segregation of customer funds with third-party verification",
                    "Require registered exchanges to maintain audited proof-of-reserves",
                    "Establish clear jurisdictional requirements for serving US customers"
                ],
                "warnings": ["Similar structures may exist at other cryptocurrency entities"],
                "confidence": 0.88
            },
            {
                "perspective_type": "economic",
                "analyst": "Economic Impact Analyst",
                "analysis_text": "The economic ripple effects extended far beyond FTX's direct victims. The collapse triggered a cascade of failures including BlockFi, Genesis, and contributed to broader crypto market capitalization declining over $200 billion. Institutional confidence in cryptocurrency markets suffered a significant setback.",
                "key_insights": [
                    "Direct customer losses estimated at $8-10 billion",
                    "Indirect market capitalization loss exceeded $200 billion",
                    "Contagion spread to BlockFi (bankruptcy), Genesis (bankruptcy), DCG (restructuring)",
                    "Venture capital write-downs in billions (Sequoia, Paradigm, others)"
                ],
                "recommendations": [
                    "Implement circuit breakers for large withdrawals across the industry",
                    "Require disclosure of institutional counterparty relationships",
                    "Consider deposit insurance mechanisms for regulated exchanges"
                ],
                "warnings": ["Interconnected lending relationships remain opaque in crypto"],
                "confidence": 0.85
            }
        ],

        "sources": [
            {"url": "https://sec.gov/news/press-release/2022-219", "title": "SEC Charges Samuel Bankman-Fried with Defrauding Investors", "domain": "sec.gov", "snippet": "The Securities and Exchange Commission today charged Samuel Bankman-Fried with orchestrating a scheme to defraud equity investors in FTX...", "credibility_score": 0.99, "source_type": "government", "date_accessed": "2024-01-15"},
            {"url": "https://www.coindesk.com/business/2022/11/02/divisions-in-sam-bankman-frieds-crypto-empire-blur-on-his-trading-titan-alamedas-balance-sheet/", "title": "CoinDesk Alameda Balance Sheet Exposé", "domain": "coindesk.com", "snippet": "A balance sheet reviewed by CoinDesk shows that Alameda Research's investment foundation is also the FTT token...", "credibility_score": 0.94, "source_type": "news", "date_accessed": "2022-11-02"},
            {"url": "https://www.justice.gov/usao-sdny/pr/united-states-attorney-announces-charges-against-ftx-founder-samuel-bankman-fried", "title": "DOJ Criminal Charges Announcement", "domain": "justice.gov", "snippet": "Damian Williams, the United States Attorney for the Southern District of New York, announced criminal charges against Samuel Bankman-Fried...", "credibility_score": 0.99, "source_type": "government", "date_accessed": "2022-12-13"},
            {"url": "https://restructuring.ra.kroll.com/FTX/", "title": "FTX Bankruptcy Case Documents", "domain": "kroll.com", "snippet": "Official restructuring portal for FTX Trading Ltd. and affiliated debtors...", "credibility_score": 0.97, "source_type": "legal", "date_accessed": "2024-02-01"},
            {"url": "https://www.nytimes.com/2024/03/28/technology/sam-bankman-fried-sentencing.html", "title": "Sam Bankman-Fried Sentenced to 25 Years", "domain": "nytimes.com", "snippet": "The FTX founder was convicted of fraud and money laundering after a trial that revealed how he used customer money...", "credibility_score": 0.95, "source_type": "news", "date_accessed": "2024-03-28"}
        ],

        "claims": []
    }


def create_rich_competitive_data() -> Dict[str, Any]:
    """Create highly detailed competitive analysis data."""
    return {
        "session_id": str(uuid4()),
        "session_title": "AI Code Assistant Market: Comprehensive Competitive Analysis 2024",
        "session_query": "Provide a detailed competitive analysis of GitHub Copilot, Cursor, and Claude Code in the AI coding assistant market",
        "template_type": "competitive",
        "status": "completed",
        "research_duration_minutes": 38,
        "total_sources_analyzed": 89,
        "parameters": {"depth": "comprehensive", "include_pricing": True},
        "created_at": datetime.now() - timedelta(hours=2),
        "completed_at": datetime.now(),

        "market_overview": {
            "total_market_size_2024": "$3.2 billion",
            "projected_size_2028": "$13.5 billion",
            "cagr": "33.2%",
            "key_drivers": ["Developer productivity demands", "AI model improvements", "Enterprise adoption", "Cloud IDE shift"],
            "market_maturity": "Early growth stage"
        },

        "competitors": [
            {
                "name": "GitHub Copilot",
                "parent_company": "Microsoft/GitHub",
                "market_position": "Market Leader",
                "market_share_estimate": "45-55%",
                "launch_date": "June 2021",
                "users": "1.8M+ paid subscribers (Feb 2024)",
                "revenue_estimate": "$300M+ ARR",
                "funding": "Microsoft backed (N/A)",
                "key_features": [
                    "Native GitHub/VS Code integration",
                    "GPT-4 powered suggestions",
                    "Copilot Chat for Q&A",
                    "Workspace context understanding",
                    "Enterprise tier with privacy controls"
                ],
                "pricing": {
                    "individual": "$10/month or $100/year",
                    "business": "$19/user/month",
                    "enterprise": "$39/user/month"
                },
                "strengths": [
                    "Deepest IDE integration",
                    "Largest training dataset (GitHub repos)",
                    "Microsoft enterprise relationships",
                    "Brand recognition and trust"
                ],
                "weaknesses": [
                    "Limited to code completion paradigm",
                    "Less effective for large refactors",
                    "Privacy concerns with code telemetry",
                    "Locked to Microsoft ecosystem"
                ],
                "confidence": 0.95
            },
            {
                "name": "Cursor",
                "parent_company": "Anysphere",
                "market_position": "Fast-Growing Challenger",
                "market_share_estimate": "8-12%",
                "launch_date": "March 2023",
                "users": "Unknown (private), 100K+ estimated",
                "revenue_estimate": "$30-50M ARR estimated",
                "funding": "$60M (Series A, Aug 2024)",
                "key_features": [
                    "AI-first IDE (VSCode fork)",
                    "Multi-model support (GPT-4, Claude)",
                    "Codebase-wide context",
                    "Composer for multi-file edits",
                    "Built-in terminal AI"
                ],
                "pricing": {
                    "hobby": "Free (limited)",
                    "pro": "$20/month",
                    "business": "$40/user/month"
                },
                "strengths": [
                    "Purpose-built AI IDE experience",
                    "Multi-file edit capabilities",
                    "Fast iteration on AI features",
                    "Growing developer enthusiasm"
                ],
                "weaknesses": [
                    "VSCode fork may lag updates",
                    "Smaller company resources",
                    "Less enterprise presence",
                    "Model costs affect margins"
                ],
                "confidence": 0.88
            },
            {
                "name": "Claude Code (Anthropic)",
                "parent_company": "Anthropic",
                "market_position": "Emerging Disruptor",
                "market_share_estimate": "3-5%",
                "launch_date": "February 2025",
                "users": "Bundled with Claude Pro (unknown)",
                "revenue_estimate": "Part of Claude revenue",
                "funding": "Anthropic: $7.3B+ raised",
                "key_features": [
                    "Terminal-based agentic coding",
                    "Extended thinking for complex tasks",
                    "File system and git integration",
                    "Multi-step autonomous execution",
                    "Claude 3.5 Sonnet / Opus models"
                ],
                "pricing": {
                    "included": "With Claude Pro $20/month",
                    "api": "Pay per token usage"
                },
                "strengths": [
                    "True agentic capabilities",
                    "Best for complex/novel problems",
                    "Safety-focused approach",
                    "Anthropic model quality"
                ],
                "weaknesses": [
                    "CLI-only (no GUI IDE)",
                    "Newer, less proven at scale",
                    "Learning curve for non-terminal users",
                    "Limited integrations currently"
                ],
                "confidence": 0.85
            }
        ],

        "feature_comparison": {
            "categories": ["Code Completion", "Chat/Q&A", "Multi-file Edit", "Agentic Tasks", "IDE Integration", "Model Choice", "Enterprise Ready"],
            "scores": {
                "GitHub Copilot": [5, 4, 2, 2, 5, 1, 5],
                "Cursor": [4, 4, 5, 3, 4, 5, 3],
                "Claude Code": [3, 5, 4, 5, 2, 1, 2]
            }
        },

        "findings": [
            {"finding_type": "pattern", "content": "All major players are converging on 'agentic' capabilities - the ability to perform multi-step coding tasks autonomously. This represents a shift from completion-based to task-based assistance.", "summary": "Agentic convergence", "confidence_score": 0.92},
            {"finding_type": "fact", "content": "GitHub Copilot has 1.8M+ paid subscribers as of February 2024, with GitHub reporting it as their fastest-growing product ever.", "summary": "Copilot subscriber milestone", "confidence_score": 0.96},
            {"finding_type": "fact", "content": "Developer productivity studies show 55% faster task completion with AI assistants, though quality impact varies by task type.", "summary": "Productivity impact", "confidence_score": 0.84},
            {"finding_type": "pattern", "content": "Enterprise adoption is accelerating, with 50,000+ organizations using Copilot Business/Enterprise. Security and privacy controls are now table stakes.", "summary": "Enterprise adoption trends", "confidence_score": 0.89},
            {"finding_type": "gap", "content": "Long-term impact on developer skills and code quality remains under-studied. Some evidence suggests over-reliance may affect learning.", "summary": "Skills impact unknown", "confidence_score": 0.68}
        ],

        "perspectives": [
            {
                "perspective_type": "market_position",
                "analysis_text": "The AI code assistant market is entering a critical phase where the paradigm is shifting from 'code completion' to 'agentic coding'. While GitHub Copilot leads in users and integration, Cursor and Claude Code are pioneering the next generation of AI-native development experiences.",
                "key_insights": [
                    "First-mover advantage (Copilot) is being challenged by innovation (Cursor, Claude)",
                    "The IDE itself is being reimagined around AI capabilities",
                    "Terminal/CLI-based tools (Claude Code) appeal to power users",
                    "Multi-model flexibility is becoming a competitive advantage"
                ],
                "recommendations": [
                    "Evaluate tools based on workflow fit, not just features",
                    "Consider multi-tool strategies for different task types",
                    "Monitor agentic capability development closely"
                ],
                "warnings": ["Market leadership could shift rapidly with model improvements"],
                "confidence": 0.87
            },
            {
                "perspective_type": "swot",
                "analysis_text": "Strategic analysis reveals distinct positioning for each player, with opportunities and threats varying by target segment.",
                "key_insights": [
                    "Copilot's strength (integration) could become weakness (lock-in resistance)",
                    "Cursor's opportunity (AI-native IDE) requires execution at scale",
                    "Claude Code's threat (niche CLI) could become strength (power user loyalty)"
                ],
                "recommendations": [
                    "Watch for Copilot's agentic feature releases in 2024-2025",
                    "Cursor's Series A runway enables aggressive R&D",
                    "Anthropic's model improvements directly benefit Claude Code"
                ],
                "warnings": ["New entrants (Amazon, Google) could reshape dynamics"],
                "confidence": 0.82
            }
        ],

        "sources": [
            {"url": "https://github.blog/2024-02-22-copilot-anniversary/", "title": "GitHub Copilot Anniversary Report", "domain": "github.blog", "credibility_score": 0.94, "source_type": "corporate"},
            {"url": "https://www.cursor.com/pricing", "title": "Cursor Pricing Page", "domain": "cursor.com", "credibility_score": 0.90, "source_type": "corporate"},
            {"url": "https://www.anthropic.com/claude-code", "title": "Claude Code Documentation", "domain": "anthropic.com", "credibility_score": 0.95, "source_type": "corporate"},
            {"url": "https://www.gartner.com/en/documents/ai-code-assistants", "title": "Gartner AI Code Assistant Report", "domain": "gartner.com", "credibility_score": 0.92, "source_type": "research_report"}
        ],

        "claims": []
    }


def create_rich_financial_data() -> Dict[str, Any]:
    """Create highly detailed financial analysis data."""
    return {
        "session_id": str(uuid4()),
        "session_title": "NVIDIA Investment Analysis: Q3 FY2025 Deep Dive",
        "session_query": "Should I invest in NVIDIA (NVDA) at current valuations given AI infrastructure demand? Provide comprehensive analysis.",
        "template_type": "financial",
        "status": "completed",
        "research_duration_minutes": 52,
        "total_sources_analyzed": 67,
        "parameters": {"depth": "comprehensive", "include_valuation": True},
        "created_at": datetime.now() - timedelta(hours=2),
        "completed_at": datetime.now(),

        "company_profile": {
            "name": "NVIDIA Corporation",
            "ticker": "NVDA",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Semiconductors",
            "market_cap": "$3.4 trillion",
            "employees": "29,600+",
            "headquarters": "Santa Clara, California",
            "ceo": "Jensen Huang (co-founder)"
        },

        "financial_metrics": {
            "latest_quarter": "Q3 FY2025 (Oct 2024)",
            "revenue": {"value": "$35.1B", "yoy_change": "+94%", "beat_estimate": True, "estimate": "$33.2B"},
            "gross_margin": {"value": "75.0%", "yoy_change": "+11pp", "guidance": "74.5-75%"},
            "operating_margin": {"value": "62.3%", "yoy_change": "+15pp"},
            "net_income": {"value": "$19.3B", "yoy_change": "+109%"},
            "eps": {"value": "$0.78", "yoy_change": "+103%", "beat_estimate": True, "estimate": "$0.74"},
            "free_cash_flow": {"value": "$16.8B", "ttm": "$58.2B"},
            "cash_position": "$38.5B",
            "debt": "$9.7B (net cash positive)"
        },

        "segment_breakdown": [
            {"segment": "Data Center", "revenue": "$30.8B", "yoy_change": "+112%", "pct_total": "88%", "notes": "AI training/inference demand"},
            {"segment": "Gaming", "revenue": "$3.3B", "yoy_change": "+15%", "pct_total": "9%", "notes": "RTX 40 series cycle maturing"},
            {"segment": "Professional Visualization", "revenue": "$0.5B", "yoy_change": "+17%", "pct_total": "1%", "notes": "Workstation GPUs"},
            {"segment": "Automotive", "revenue": "$0.4B", "yoy_change": "+72%", "pct_total": "1%", "notes": "Self-driving platforms growing"}
        ],

        "valuation_metrics": {
            "stock_price": "$140.50 (as of analysis)",
            "52_week_range": "$45.25 - $149.77",
            "pe_ratio_ttm": "68.5x",
            "pe_ratio_forward": "35.2x (FY2026E)",
            "peg_ratio": "1.2x",
            "ps_ratio": "38.5x",
            "ev_ebitda": "55.2x",
            "historical_pe_avg": "40x (5-year)",
            "price_target_consensus": "$165 (median)",
            "analyst_ratings": {"strong_buy": 42, "buy": 12, "hold": 5, "sell": 0}
        },

        "growth_catalysts": [
            {"catalyst": "Blackwell GPU Launch", "timing": "Q4 FY2025", "impact": "High", "description": "Next-gen architecture with 2.5x training performance", "confidence": 0.94},
            {"catalyst": "Hyperscaler Capex", "timing": "Ongoing", "impact": "High", "description": "Microsoft, Google, Amazon, Meta all increasing AI infrastructure spend", "confidence": 0.91},
            {"catalyst": "Sovereign AI", "timing": "2024-2026", "impact": "Medium", "description": "Governments building domestic AI compute capacity", "confidence": 0.82},
            {"catalyst": "Inference Demand", "timing": "2025+", "impact": "High", "description": "Production AI deployments driving inference chip demand", "confidence": 0.85},
            {"catalyst": "Software/Services", "timing": "Ongoing", "impact": "Medium", "description": "CUDA moat deepening, DGX Cloud, AI Enterprise expanding", "confidence": 0.78}
        ],

        "risk_factors": [
            {"risk": "Customer Concentration", "severity": "High", "description": "Top 5 customers = 50%+ of Data Center revenue", "mitigation": "Diversifying customer base, long-term contracts"},
            {"risk": "China Export Restrictions", "severity": "High", "description": "US restrictions limit China sales (~10-15% DC revenue at risk)", "mitigation": "Compliant chip designs (H20), geographic diversification"},
            {"risk": "Competition Intensifying", "severity": "Medium", "description": "AMD MI300X, Intel Gaudi, custom chips (Google TPU, Amazon Trainium)", "mitigation": "CUDA ecosystem moat, continuous innovation"},
            {"risk": "Valuation Risk", "severity": "Medium", "description": "Premium valuation leaves little room for disappointment", "mitigation": "Growth rate justifies premium if sustained"},
            {"risk": "Supply Chain", "severity": "Medium", "description": "TSMC dependency for advanced nodes, CoWoS packaging constraints", "mitigation": "Multi-year supply agreements, alternative packaging development"}
        ],

        "findings": [
            {"finding_type": "fact", "content": "NVIDIA achieved $35.1 billion in Q3 FY2025 revenue, up 94% year-over-year, with Data Center segment generating $30.8 billion (88% of total), exceeding all analyst estimates.", "summary": "Record quarterly results", "confidence_score": 0.99},
            {"finding_type": "fact", "content": "Gross margins expanded to 75% from 64% year-over-year, demonstrating exceptional pricing power and operating leverage as AI demand outpaces supply.", "summary": "Margin expansion", "confidence_score": 0.98},
            {"finding_type": "pattern", "content": "Hyperscaler capex guidance indicates continued aggressive AI infrastructure investment through 2025-2026, with Microsoft, Google, and Amazon all projecting increased capital expenditure.", "summary": "Hyperscaler spending trend", "confidence_score": 0.91},
            {"finding_type": "fact", "content": "Blackwell GPU demand significantly exceeds supply for next several quarters according to management commentary, with production ramping in Q4 FY2025.", "summary": "Blackwell demand", "confidence_score": 0.93},
            {"finding_type": "pattern", "content": "The inference market (deploying AI models in production) is emerging as the next growth driver, potentially larger than training market long-term.", "summary": "Inference opportunity", "confidence_score": 0.84},
            {"finding_type": "gap", "content": "Long-term AI infrastructure spending sustainability beyond current hyperscaler buildout cycle remains uncertain. Spending could normalize after initial capacity build.", "summary": "Demand sustainability question", "confidence_score": 0.72}
        ],

        "perspectives": [
            {
                "perspective_type": "valuation",
                "analyst": "Valuation Analyst",
                "analysis_text": "NVIDIA's current valuation of 68.5x trailing earnings appears elevated versus historical averages (40x), but forward estimates of 35x on FY2026E earnings are more reasonable given the growth trajectory. The PEG ratio of 1.2x suggests the stock is fairly valued relative to growth, though not cheap. DCF analysis with conservative assumptions yields fair value in the $130-150 range.",
                "key_insights": [
                    "Forward P/E of 35x reasonable for 50%+ growth",
                    "PEG of 1.2x indicates fair value, not deep value",
                    "Premium justified by moat but priced for perfection",
                    "Any growth deceleration could trigger multiple compression"
                ],
                "recommendations": [
                    "Consider dollar-cost averaging rather than lump sum at ATH",
                    "Position size appropriately given volatility (2-5% of portfolio)",
                    "Set price alerts for better entry points on pullbacks"
                ],
                "warnings": ["Guidance miss or margin compression could trigger 20%+ drawdown"],
                "confidence": 0.85
            },
            {
                "perspective_type": "risk",
                "analyst": "Risk Analyst",
                "analysis_text": "Key risks center on concentration (customers, TSMC), geopolitics (China restrictions), and competition (AMD, custom silicon). The stock's beta of 1.7 indicates elevated volatility. However, the company's net cash position and FCF generation provide significant downside protection.",
                "key_insights": [
                    "Customer concentration improving but still elevated",
                    "China risk partially priced in but could worsen",
                    "TSMC dependency is industry-wide, not NVDA-specific",
                    "Competition is real but 2+ years behind on software stack"
                ],
                "recommendations": [
                    "Monitor hyperscaler capex guidance for demand signals",
                    "Track AMD MI300X adoption as competitive indicator",
                    "Watch for potential China policy escalation"
                ],
                "warnings": ["Export restriction expansion could impact 10-15% of revenue"],
                "confidence": 0.82
            }
        ],

        "sources": [
            {"url": "https://investor.nvidia.com/financial-info/quarterly-results/default.aspx", "title": "NVIDIA Q3 FY2025 Earnings", "domain": "investor.nvidia.com", "credibility_score": 1.0, "source_type": "sec_filing"},
            {"url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001045810", "title": "NVIDIA SEC Filings", "domain": "sec.gov", "credibility_score": 1.0, "source_type": "sec_filing"},
            {"url": "https://finance.yahoo.com/quote/NVDA", "title": "NVDA Market Data", "domain": "finance.yahoo.com", "credibility_score": 0.88, "source_type": "financial"},
            {"url": "https://www.tipranks.com/stocks/nvda/forecast", "title": "Analyst Consensus", "domain": "tipranks.com", "credibility_score": 0.85, "source_type": "research_report"}
        ],

        "claims": []
    }


def create_rich_legal_data() -> Dict[str, Any]:
    """Create highly detailed legal analysis data."""
    return {
        "session_id": str(uuid4()),
        "session_title": "GDPR Compliance for AI Systems: Legal Requirements and Risks",
        "session_query": "What are the comprehensive GDPR compliance requirements for AI companies operating in the EU, including the intersection with the EU AI Act?",
        "template_type": "legal",
        "status": "completed",
        "research_duration_minutes": 61,
        "total_sources_analyzed": 94,
        "parameters": {"jurisdiction": "EU", "depth": "comprehensive"},
        "created_at": datetime.now() - timedelta(hours=3),
        "completed_at": datetime.now(),

        "regulatory_framework": {
            "primary_regulation": "General Data Protection Regulation (GDPR) - Regulation (EU) 2016/679",
            "effective_date": "May 25, 2018",
            "scope": "Any organization processing personal data of EU residents",
            "key_principles": ["Lawfulness, fairness, transparency", "Purpose limitation", "Data minimization", "Accuracy", "Storage limitation", "Integrity and confidentiality", "Accountability"],
            "supervisory_authorities": "National DPAs in each EU member state, coordinated by EDPB"
        },

        "ai_specific_requirements": [
            {
                "article": "Article 22",
                "title": "Automated Individual Decision-Making, Including Profiling",
                "requirement": "Data subjects have the right not to be subject to a decision based solely on automated processing which produces legal or similarly significant effects",
                "exceptions": ["Contract necessity", "Legal authorization", "Explicit consent"],
                "ai_implications": "AI systems making consequential decisions must incorporate human oversight or fall within exceptions",
                "compliance_steps": ["Identify automated decisions with legal/significant effects", "Implement human review processes", "Provide meaningful information about logic involved", "Allow objection and human review on request"],
                "risk_level": "High"
            },
            {
                "article": "Article 25",
                "title": "Data Protection by Design and Default",
                "requirement": "Implement appropriate technical and organizational measures designed to implement data protection principles",
                "ai_implications": "AI systems must be designed with privacy as a core principle from inception",
                "compliance_steps": ["Conduct privacy impact assessment at design stage", "Minimize data collection to what's necessary", "Implement pseudonymization where possible", "Build in data subject rights mechanisms"],
                "risk_level": "Medium"
            },
            {
                "article": "Article 35",
                "title": "Data Protection Impact Assessment (DPIA)",
                "requirement": "DPIA mandatory when processing likely to result in high risk to rights and freedoms",
                "ai_implications": "Most AI systems processing personal data will require DPIA, especially those involving profiling, large-scale processing, or systematic monitoring",
                "compliance_steps": ["Document processing operations", "Assess necessity and proportionality", "Identify and evaluate risks", "Develop mitigation measures", "Consult DPA if high risk remains"],
                "risk_level": "High"
            },
            {
                "article": "Articles 13-14",
                "title": "Right to Information/Transparency",
                "requirement": "Provide meaningful information about the existence of automated decision-making including logic involved, significance, and envisaged consequences",
                "ai_implications": "AI explainability is required - must be able to explain how AI reaches decisions",
                "compliance_steps": ["Document AI decision logic", "Create understandable explanations for data subjects", "Include in privacy notices", "Provide on request"],
                "risk_level": "Medium"
            }
        ],

        "eu_ai_act_intersection": {
            "status": "Entered into force August 1, 2024; phased implementation through 2027",
            "key_overlaps": [
                "Both require risk assessment for AI systems",
                "Transparency requirements under both regimes",
                "Human oversight mandates complement each other",
                "Data governance requirements overlap significantly"
            ],
            "compliance_timeline": [
                {"date": "August 2024", "requirement": "AI Act enters force"},
                {"date": "February 2025", "requirement": "Prohibited AI practices banned"},
                {"date": "August 2025", "requirement": "GPAI model requirements apply"},
                {"date": "August 2026", "requirement": "High-risk AI system requirements apply"},
                {"date": "August 2027", "requirement": "Full implementation for embedded AI in regulated products"}
            ]
        },

        "enforcement_actions": [
            {"year": "2023", "entity": "Meta/Facebook", "authority": "Irish DPC", "issue": "Behavioral advertising legal basis", "fine": "€1.2 billion", "relevance": "Largest GDPR fine; legal basis for AI training data relevant"},
            {"year": "2023", "entity": "OpenAI (ChatGPT)", "authority": "Italian Garante", "issue": "No legal basis, no age verification, inaccurate data", "fine": "Temporary ban lifted after compliance", "relevance": "First major action against AI chatbot"},
            {"year": "2024", "entity": "OpenAI", "authority": "Italian Garante", "issue": "GDPR violations related to training data and user data processing", "fine": "€15 million", "relevance": "Precedent for AI training data enforcement"},
            {"year": "2024", "entity": "Clearview AI", "authority": "French CNIL", "issue": "Biometric data processing without consent", "fine": "€20 million", "relevance": "Facial recognition AI enforcement precedent"}
        ],

        "compliance_checklist": [
            {"requirement": "Lawful basis for AI training data", "status": "Critical", "description": "Consent, legitimate interest assessment, or other valid basis for training data"},
            {"requirement": "Data Protection Impact Assessment", "status": "Required", "description": "Mandatory for high-risk AI processing"},
            {"requirement": "Privacy by Design implementation", "status": "Required", "description": "Build privacy into AI system architecture"},
            {"requirement": "Transparency and explainability", "status": "Required", "description": "Meaningful information about AI decision logic"},
            {"requirement": "Human oversight for automated decisions", "status": "Required", "description": "Human review for decisions with legal/significant effects"},
            {"requirement": "Data subject rights mechanisms", "status": "Required", "description": "Access, rectification, erasure, objection procedures"},
            {"requirement": "Cross-border transfer safeguards", "status": "If applicable", "description": "SCCs, adequacy decisions for non-EU transfers"},
            {"requirement": "Records of processing activities", "status": "Required", "description": "Document all AI processing operations"},
            {"requirement": "DPO appointment", "status": "If applicable", "description": "Required for large-scale systematic monitoring"}
        ],

        "findings": [
            {"finding_type": "fact", "content": "Article 22 of GDPR establishes a right not to be subject to automated decisions with legal or similarly significant effects, with limited exceptions requiring explicit consent, contract necessity, or legal authorization.", "summary": "Automated decision-making rights", "confidence_score": 0.99, "citation": "GDPR Article 22"},
            {"finding_type": "fact", "content": "A Data Protection Impact Assessment (DPIA) under Article 35 is mandatory before processing likely to result in high risk, which includes most AI systems performing profiling or large-scale data processing.", "summary": "DPIA requirement", "confidence_score": 0.98, "citation": "GDPR Article 35"},
            {"finding_type": "pattern", "content": "European data protection authorities are increasingly focusing enforcement on AI companies, with the Italian Garante leading actions against ChatGPT and subsequent DPAs following similar investigations.", "summary": "Enforcement trend toward AI", "confidence_score": 0.89},
            {"finding_type": "fact", "content": "Maximum GDPR fines are €20 million or 4% of global annual turnover, whichever is higher. The largest fine to date is €1.2 billion against Meta for data transfer violations.", "summary": "Maximum penalty structure", "confidence_score": 1.0, "citation": "GDPR Article 83"},
            {"finding_type": "pattern", "content": "Courts and DPAs are interpreting 'human oversight' requirements strictly - rubber-stamping AI decisions does not satisfy Article 22 requirements.", "summary": "Human oversight interpretation", "confidence_score": 0.87},
            {"finding_type": "gap", "content": "The intersection between GDPR and the EU AI Act creates some regulatory uncertainty during the transition period, particularly regarding which requirements take precedence in overlapping areas.", "summary": "GDPR-AI Act uncertainty", "confidence_score": 0.78}
        ],

        "perspectives": [
            {
                "perspective_type": "compliance",
                "analyst": "Compliance Advisor",
                "analysis_text": "GDPR compliance for AI systems requires a comprehensive approach addressing data collection, training, deployment, and ongoing operation. The key challenge is balancing AI development needs with data minimization principles. Organizations should adopt a 'privacy-first' AI development methodology.",
                "key_insights": [
                    "Lawful basis must be established before collecting ANY training data",
                    "The 'right to explanation' under GDPR requires AI systems to be somewhat interpretable",
                    "Synthetic data and privacy-preserving techniques can reduce compliance burden",
                    "Cross-border transfers for AI processing require careful safeguards"
                ],
                "recommendations": [
                    "Conduct comprehensive DPIA before any AI deployment",
                    "Implement genuine human oversight for consequential decisions",
                    "Document lawful basis for all training data",
                    "Build data subject request handling into AI systems",
                    "Engage with relevant DPAs proactively"
                ],
                "warnings": [
                    "Using personal data for AI training without proper legal basis is high-risk",
                    "Cross-border data transfers (especially to US) require additional safeguards post-Schrems II"
                ],
                "confidence": 0.90
            },
            {
                "perspective_type": "regulatory_risk",
                "analyst": "Regulatory Risk Analyst",
                "analysis_text": "Regulatory risk for AI companies in the EU is elevated and increasing. The combination of GDPR enforcement, the new EU AI Act, and national initiatives creates a complex compliance landscape. First-mover enforcement actions set precedents that affect the entire industry.",
                "key_insights": [
                    "Irish DPC and Italian Garante are most active on AI enforcement",
                    "French CNIL has issued comprehensive AI training guidance",
                    "Coordination between DPAs increasing for cross-border AI cases",
                    "EU AI Act will layer additional requirements starting 2025"
                ],
                "recommendations": [
                    "Monitor enforcement actions closely for compliance guidance",
                    "Consider appointing EU representative if not established in EU",
                    "Prepare for AI Act compliance timeline now",
                    "Document compliance decisions for accountability demonstration"
                ],
                "warnings": ["Enforcement appetite is high - regulators are making examples"],
                "confidence": 0.86
            }
        ],

        "sources": [
            {"url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj", "title": "General Data Protection Regulation (GDPR) Official Text", "domain": "eur-lex.europa.eu", "credibility_score": 1.0, "source_type": "regulation"},
            {"url": "https://edpb.europa.eu/our-work-tools/general-guidance/guidelines-recommendations-best-practices_en", "title": "EDPB Guidelines on AI and Automated Decision-Making", "domain": "edpb.europa.eu", "credibility_score": 0.99, "source_type": "regulatory_guidance"},
            {"url": "https://www.cnil.fr/en/artificial-intelligence", "title": "CNIL AI Position and Guidance", "domain": "cnil.fr", "credibility_score": 0.97, "source_type": "regulatory_guidance"},
            {"url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689", "title": "EU AI Act Official Text", "domain": "eur-lex.europa.eu", "credibility_score": 1.0, "source_type": "regulation"},
            {"url": "https://www.garanteprivacy.it/", "title": "Italian Garante Decisions on AI", "domain": "garanteprivacy.it", "credibility_score": 0.98, "source_type": "regulatory_decision"}
        ],

        "claims": []
    }


RICH_DATA_GENERATORS = {
    "investigative": create_rich_investigative_data,
    "competitive": create_rich_competitive_data,
    "financial": create_rich_financial_data,
    "legal": create_rich_legal_data
}


# =============================================================================
# HTML GENERATION
# =============================================================================

def get_template_theme(template_type: str) -> str:
    """Get CSS theme overrides for template type."""
    return TEMPLATE_THEMES.get(template_type, TEMPLATE_THEMES["investigative"])


def build_html_prompt(data: Dict[str, Any], template_type: str) -> str:
    """Build comprehensive prompt for HTML generation."""

    theme_css = get_template_theme(template_type)

    # Convert data to structured text for LLM
    data_text = f"""
# RESEARCH SESSION DATA

## Session Overview
- **Title**: {data.get('session_title', 'Research Report')}
- **Query**: {data.get('session_query', 'N/A')}
- **Template Type**: {template_type.title()} Research
- **Status**: {data.get('status', 'completed').title()}
- **Duration**: {data.get('research_duration_minutes', 'N/A')} minutes
- **Sources Analyzed**: {data.get('total_sources_analyzed', 0)}
- **Generated**: {datetime.now().strftime('%B %d, %Y at %H:%M')}

"""

    # Add executive summary if available
    if data.get('executive_summary'):
        data_text += f"""## Executive Summary
{data['executive_summary']}

"""

    # Add market overview for competitive
    if data.get('market_overview'):
        mo = data['market_overview']
        data_text += f"""## Market Overview
- **Current Size**: {mo.get('total_market_size_2024', 'N/A')}
- **Projected (2028)**: {mo.get('projected_size_2028', 'N/A')}
- **CAGR**: {mo.get('cagr', 'N/A')}
- **Key Drivers**: {', '.join(mo.get('key_drivers', []))}

"""

    # Add company profile for financial
    if data.get('company_profile'):
        cp = data['company_profile']
        data_text += f"""## Company Profile
| Attribute | Value |
|-----------|-------|
| Name | {cp.get('name', 'N/A')} |
| Ticker | {cp.get('ticker', 'N/A')} |
| Sector | {cp.get('sector', 'N/A')} |
| Market Cap | {cp.get('market_cap', 'N/A')} |
| CEO | {cp.get('ceo', 'N/A')} |

"""

    # Add financial metrics
    if data.get('financial_metrics'):
        fm = data['financial_metrics']
        data_text += f"""## Financial Metrics (Latest Quarter)
| Metric | Value | YoY Change | vs Estimate |
|--------|-------|------------|-------------|
"""
        for key, val in fm.items():
            if isinstance(val, dict):
                data_text += f"| {key.replace('_', ' ').title()} | {val.get('value', 'N/A')} | {val.get('yoy_change', 'N/A')} | {'Beat' if val.get('beat_estimate') else 'N/A'} |\n"

    # Add timeline events
    if data.get('key_timeline_events'):
        data_text += "\n## Timeline of Key Events\n"
        for event in data['key_timeline_events']:
            data_text += f"- **{event['date']}**: {event['title']} - {event['description']} (Confidence: {event['confidence']:.0%})\n"

    # Add actors
    if data.get('actors'):
        data_text += "\n## Key Actors\n"
        for actor in data['actors']:
            data_text += f"""
### {actor['name']}
- **Role**: {actor['role']}
- **Description**: {actor['description']}
- **Key Actions**: {', '.join(actor.get('key_actions', [])[:3])}
- **Current Status**: {actor.get('current_status', 'Unknown')}
- **Confidence**: {actor['confidence']:.0%}
"""

    # Add competitors
    if data.get('competitors'):
        data_text += "\n## Competitive Landscape\n"
        data_text += "| Company | Position | Market Share | Users | Key Differentiator |\n"
        data_text += "|---------|----------|--------------|-------|--------------------|\n"
        for comp in data['competitors']:
            diff = comp.get('key_features', ['N/A'])[0] if comp.get('key_features') else 'N/A'
            data_text += f"| {comp['name']} | {comp['market_position']} | {comp.get('market_share_estimate', 'N/A')} | {comp.get('users', 'N/A')} | {diff} |\n"

        data_text += "\n### Competitor Details\n"
        for comp in data['competitors']:
            data_text += f"""
#### {comp['name']}
- **Parent**: {comp.get('parent_company', 'Independent')}
- **Strengths**: {', '.join(comp.get('strengths', [])[:3])}
- **Weaknesses**: {', '.join(comp.get('weaknesses', [])[:2])}
- **Pricing**: {comp.get('pricing', {})}
"""

    # Add regulatory framework for legal
    if data.get('regulatory_framework'):
        rf = data['regulatory_framework']
        data_text += f"""## Regulatory Framework
- **Primary Regulation**: {rf.get('primary_regulation', 'N/A')}
- **Effective Date**: {rf.get('effective_date', 'N/A')}
- **Key Principles**: {', '.join(rf.get('key_principles', []))}

"""

    # Add AI-specific requirements
    if data.get('ai_specific_requirements'):
        data_text += "## AI-Specific Legal Requirements\n"
        for req in data['ai_specific_requirements']:
            data_text += f"""
### {req['article']}: {req['title']}
- **Requirement**: {req['requirement']}
- **AI Implications**: {req.get('ai_implications', 'N/A')}
- **Risk Level**: {req.get('risk_level', 'Medium')}
- **Compliance Steps**: {', '.join(req.get('compliance_steps', [])[:2])}
"""

    # Add compliance checklist
    if data.get('compliance_checklist'):
        data_text += "\n## Compliance Checklist\n"
        data_text += "| Requirement | Status | Description |\n"
        data_text += "|-------------|--------|-------------|\n"
        for item in data['compliance_checklist']:
            data_text += f"| {item['requirement']} | {item['status']} | {item['description'][:50]}... |\n"

    # Add risk factors
    if data.get('risk_factors'):
        data_text += "\n## Risk Factors\n"
        for risk in data['risk_factors']:
            data_text += f"- **{risk['risk']}** ({risk['severity']}): {risk['description']}\n"

    # Add growth catalysts
    if data.get('growth_catalysts'):
        data_text += "\n## Growth Catalysts\n"
        for cat in data['growth_catalysts']:
            data_text += f"- **{cat['catalyst']}** ({cat['timing']}): {cat['description']} - Impact: {cat['impact']}\n"

    # Add valuation metrics
    if data.get('valuation_metrics'):
        vm = data['valuation_metrics']
        data_text += "\n## Valuation Metrics\n"
        data_text += f"- **Stock Price**: {vm.get('stock_price', 'N/A')}\n"
        data_text += f"- **P/E (TTM)**: {vm.get('pe_ratio_ttm', 'N/A')}\n"
        data_text += f"- **Forward P/E**: {vm.get('pe_ratio_forward', 'N/A')}\n"
        data_text += f"- **Price Target Consensus**: {vm.get('price_target_consensus', 'N/A')}\n"

    # Add findings
    if data.get('findings'):
        data_text += "\n## Research Findings\n"
        for i, finding in enumerate(data['findings'], 1):
            data_text += f"{i}. **[{finding['finding_type'].upper()}]** {finding['content'][:200]}... (Confidence: {finding['confidence_score']:.0%})\n"

    # Add perspectives
    if data.get('perspectives'):
        data_text += "\n## Expert Perspectives\n"
        for perspective in data['perspectives']:
            data_text += f"""
### {perspective['perspective_type'].replace('_', ' ').title()} Analysis
{perspective.get('analysis_text', '')}

**Key Insights:**
{chr(10).join('- ' + i for i in perspective.get('key_insights', [])[:4])}

**Recommendations:**
{chr(10).join('- ' + r for r in perspective.get('recommendations', [])[:3])}

**Warnings:**
{chr(10).join('- ' + w for w in perspective.get('warnings', [])[:2])}

*Confidence: {perspective.get('confidence', 0):.0%}*
"""

    # Add sources
    if data.get('sources'):
        data_text += "\n## Sources\n"
        for source in data['sources']:
            data_text += f"- [{source['title']}]({source['url']}) - {source['domain']} ({source['source_type']}, Credibility: {source['credibility_score']:.0%})\n"

    # Get template-specific theme
    theme_css = get_template_theme(template_type)

    # Build the full prompt with Design System
    prompt = f"""You are a professional report designer. Create a beautifully styled HTML report using the Design System CSS provided.

## TASK
Transform the research data into a polished, professional HTML document using the Design System components provided below. The CSS classes and patterns are ready to use - just apply them to structure the content.

## DESIGN SYSTEM CSS
Include this complete CSS in your <style> tag, then add the template theme after it:

```css
{DESIGN_SYSTEM_CSS}

{theme_css}
```

{VISUAL_RECIPES}

## RESEARCH DATA TO DISPLAY
{data_text}

## INSTRUCTIONS

1. **Use the Design System Classes**:
   - Use `.ds-card` for content cards
   - Use `.ds-metric-card` with `.value`, `.label`, `.change` for statistics
   - Use `.ds-badge` (success/warning/danger/info) for status indicators
   - Use `.ds-table` for data tables
   - Use `.ds-timeline` with `.ds-timeline-item` for chronological events
   - Use `.ds-callout` (info/success/warning/danger) for key findings
   - Use `.ds-profile` with `.ds-avatar` for actor/entity cards
   - Use `.ds-grid` (ds-grid-2/3/4) for layouts
   - Use `.ds-stats-row` for rows of metric cards

2. **Structure**:
   - Start with key metrics in a `.ds-stats-row`
   - Use `.ds-card` sections for major content areas
   - Apply `.ds-badge` to show confidence/status/severity
   - Use `.ds-timeline` for any chronological data
   - End with sources in a table or list

3. **Template-Specific Guidance for {template_type.upper()}**:
   - Investigative: Focus on timeline, actor cards, evidence callouts
   - Competitive: Focus on comparison tables, feature grids, market metrics
   - Financial: Focus on metric cards, change indicators (+/-), risk badges
   - Legal: Focus on citation callouts, compliance checklists, article references

4. **Technical Requirements**:
   - Complete HTML5 document starting with <!DOCTYPE html>
   - ALL CSS in single <style> tag (Design System + Theme + any custom)
   - Semantic HTML structure (header, main, section, footer)
   - Include ALL data provided - don't omit details

## OUTPUT
Return ONLY the complete HTML document starting with <!DOCTYPE html>.
No explanations, no markdown code blocks, just the raw HTML.
"""

    return prompt


async def generate_html_report(data: Dict[str, Any], template_type: str, api_key: str) -> str:
    """Generate HTML report using OpenRouter API."""

    prompt = build_html_prompt(data, template_type)

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://research-platform.local",
                "X-Title": "Research Report Generator"
            },
            json={
                "model": "google/gemini-3-flash-preview",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 32000
            }
        )

        response.raise_for_status()
        result = response.json()
        html = result["choices"][0]["message"]["content"]

        # Clean response
        html = html.strip()
        if html.startswith("```html"):
            html = html[7:]
        elif html.startswith("```"):
            html = html[3:]
        if html.endswith("```"):
            html = html[:-3]
        html = html.strip()

        if not html.lower().startswith("<!doctype"):
            pos = html.lower().find("<!doctype")
            if pos > 0:
                html = html[pos:]

        return html


async def run_html_generation_tests():
    """Run HTML generation tests for all template types."""

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY environment variable not set")
        print("Set it with: set OPENROUTER_API_KEY=your_key_here")
        sys.exit(1)

    print("\n" + "="*70)
    print(" HTML REPORT GENERATION TEST")
    print("="*70)
    print(f" Started: {datetime.now().isoformat()}")
    print(f" Output: {_results_dir}")
    print(f" API Key: {api_key[:8]}...{api_key[-4:]}")
    print("="*70)

    results = []

    for template_type, generator in RICH_DATA_GENERATORS.items():
        print(f"\n[{len(results)+1}/4] Generating {template_type.upper()} report...")

        try:
            # Generate rich data
            data = generator()

            # Generate HTML
            print(f"    Calling OpenRouter API (may take 30-60s)...")
            html = await generate_html_report(data, template_type, api_key)

            # Save HTML
            html_path = _results_dir / f"{template_type}_report.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

            char_count = len(html)
            print(f"    [OK] Generated {char_count:,} characters")
            print(f"    Saved: {html_path.name}")

            results.append({
                "template": template_type,
                "chars": char_count,
                "success": True,
                "file": html_path.name
            })

        except Exception as e:
            print(f"    [FAIL] {e}")
            results.append({
                "template": template_type,
                "success": False,
                "error": str(e)
            })

    # Summary
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)

    success = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\n  Total: {len(results)}")
    print(f"  Successful: {len(success)}")
    print(f"  Failed: {len(failed)}")

    if success:
        total_chars = sum(r["chars"] for r in success)
        print(f"\n  Total HTML generated: {total_chars:,} characters")
        print(f"\n  Generated files:")
        for r in success:
            print(f"    - {r['file']} ({r['chars']:,} chars)")

    if failed:
        print("\n  Failed:")
        for r in failed:
            print(f"    - {r['template']}: {r['error'][:60]}")

    print("\n  Open the HTML files in a browser to view the reports!")
    print("="*70)

    return results


if __name__ == "__main__":
    asyncio.run(run_html_generation_tests())
