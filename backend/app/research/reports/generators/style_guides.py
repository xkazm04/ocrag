"""Template-aware style guides for HTML report generation."""

from typing import Dict, Any


# Template-specific style configurations
TEMPLATE_STYLE_GUIDES: Dict[str, Dict[str, Any]] = {
    "investigative": {
        "tone": "journalistic, objective, evidence-focused",
        "visual_style": "clean, serious, newspaper-inspired layout",
        "emphasis": "timelines, actor profiles, evidence chains, source citations",
        "color_palette": "neutral grays (#333, #666, #999), accent blue (#2563eb) for links",
        "typography": "serif headlines, clean sans-serif body text",
        "special_elements": [
            "timeline visualization with dates",
            "actor cards with profiles",
            "evidence strength indicators",
            "source credibility badges"
        ]
    },
    "competitive": {
        "tone": "analytical, strategic, business-focused",
        "visual_style": "modern, data-rich, dashboard-like presentation",
        "emphasis": "comparison tables, matrices, metrics, market positioning",
        "color_palette": "corporate blues (#1e40af, #3b82f6), green (#10b981) for positive, red (#ef4444) for negative",
        "typography": "modern sans-serif throughout, bold headers",
        "special_elements": [
            "competitive comparison tables",
            "SWOT quadrant layouts",
            "market share visualizations",
            "battlecard quick-reference boxes"
        ]
    },
    "financial": {
        "tone": "quantitative, precise, professional",
        "visual_style": "Bloomberg-inspired, metric-heavy, data-dense",
        "emphasis": "numbers, trends, ratings, risk indicators, key metrics",
        "color_palette": "financial green (#059669) for gains, red (#dc2626) for losses, dark theme option (#1f2937)",
        "typography": "monospace for numbers, clean sans-serif for text",
        "special_elements": [
            "metric cards with large numbers",
            "bull/bear case comparison",
            "risk severity indicators",
            "financial data tables with alignment"
        ]
    },
    "legal": {
        "tone": "formal, authoritative, citation-heavy",
        "visual_style": "traditional legal document, minimal decoration, professional",
        "emphasis": "citations, precedents, structured arguments (IRAC), compliance status",
        "color_palette": "black and white primarily, minimal accent (#4b5563)",
        "typography": "traditional serif fonts, proper legal formatting",
        "special_elements": [
            "numbered paragraphs",
            "citation formatting",
            "compliance status checkboxes",
            "legal section headers (I, II, III)"
        ]
    },
    "general": {
        "tone": "professional, balanced, informative",
        "visual_style": "clean, modern, readable",
        "emphasis": "clear hierarchy, scannable sections, key takeaways",
        "color_palette": "neutral palette with blue (#3b82f6) accent",
        "typography": "modern sans-serif, good contrast",
        "special_elements": [
            "executive summary boxes",
            "key findings highlights",
            "source citations",
            "confidence indicators"
        ]
    }
}


def get_style_guide(template_type: str) -> Dict[str, Any]:
    """Get style guide for a template type."""
    # Normalize template type
    normalized = template_type.lower().replace("-", "_").replace(" ", "_")

    # Match to known templates
    if "investigative" in normalized:
        return TEMPLATE_STYLE_GUIDES["investigative"]
    elif "competitive" in normalized:
        return TEMPLATE_STYLE_GUIDES["competitive"]
    elif "financial" in normalized:
        return TEMPLATE_STYLE_GUIDES["financial"]
    elif "legal" in normalized:
        return TEMPLATE_STYLE_GUIDES["legal"]
    else:
        return TEMPLATE_STYLE_GUIDES["general"]


def format_style_guide_for_prompt(style_guide: Dict[str, Any]) -> str:
    """Format style guide as prompt-friendly text."""
    lines = []

    lines.append(f"**Tone:** {style_guide['tone']}")
    lines.append(f"**Visual Style:** {style_guide['visual_style']}")
    lines.append(f"**Emphasis:** {style_guide['emphasis']}")
    lines.append(f"**Color Palette:** {style_guide['color_palette']}")
    lines.append(f"**Typography:** {style_guide['typography']}")

    if style_guide.get('special_elements'):
        lines.append("**Special Elements to Consider:**")
        for element in style_guide['special_elements']:
            lines.append(f"  - {element}")

    return "\n".join(lines)


# Base CSS that all reports should include
BASE_CSS = """
/* Base Report Styles */
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: #1f2937;
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
    background: #ffffff;
}

h1 {
    font-size: 2rem;
    margin-bottom: 1rem;
    color: #111827;
    border-bottom: 2px solid #e5e7eb;
    padding-bottom: 0.5rem;
}

h2 {
    font-size: 1.5rem;
    margin-top: 2rem;
    margin-bottom: 1rem;
    color: #1f2937;
}

h3 {
    font-size: 1.25rem;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    color: #374151;
}

p {
    margin-bottom: 1rem;
}

ul, ol {
    margin-bottom: 1rem;
    padding-left: 1.5rem;
}

li {
    margin-bottom: 0.5rem;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
}

th, td {
    border: 1px solid #e5e7eb;
    padding: 0.75rem;
    text-align: left;
}

th {
    background: #f9fafb;
    font-weight: 600;
}

blockquote {
    border-left: 4px solid #3b82f6;
    padding-left: 1rem;
    margin: 1rem 0;
    color: #4b5563;
    font-style: italic;
}

code {
    background: #f3f4f6;
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-family: 'Fira Code', monospace;
}

hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 2rem 0;
}

a {
    color: #2563eb;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* Confidence indicators */
.confidence-high {
    color: #059669;
    font-weight: 500;
}

.confidence-medium {
    color: #d97706;
    font-weight: 500;
}

.confidence-low {
    color: #dc2626;
    font-weight: 500;
}

/* Print styles */
@media print {
    body {
        max-width: none;
        padding: 1cm;
    }

    h1, h2, h3 {
        page-break-after: avoid;
    }

    table, figure {
        page-break-inside: avoid;
    }

    a {
        color: inherit;
    }

    a[href]::after {
        content: " (" attr(href) ")";
        font-size: 0.8em;
        color: #6b7280;
    }
}
"""
