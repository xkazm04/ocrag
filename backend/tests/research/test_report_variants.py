"""Comprehensive test for all report variants with mock data.

Generates all 16 report variants using rich mock data and optionally
tests LLM HTML generation. Results are saved to results/reports/.

Run with: python tests/research/test_report_variants.py [--html]

Options:
  --html    Also generate HTML using LLM (requires OpenRouter API key)
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, List

# Setup paths
_script_dir = Path(__file__).parent
_backend_dir = _script_dir.parent.parent
_results_dir = _script_dir / "results" / "reports"
sys.path.insert(0, str(_backend_dir))

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")

# Ensure results directory exists
_results_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# MOCK DATA GENERATORS
# =============================================================================

def create_investigative_mock_data() -> Dict[str, Any]:
    """Create rich mock data for investigative research."""
    return {
        "session_id": uuid4(),
        "session_title": "FTX Collapse Investigation",
        "session_query": "What led to the collapse of FTX and who were the key players involved?",
        "template_type": "investigative",
        "status": "completed",
        "parameters": {"max_searches": 15, "granularity": "detailed"},
        "created_at": datetime.now() - timedelta(hours=2),
        "completed_at": datetime.now(),
        "findings": [
            {
                "finding_type": "event",
                "content": "On November 2, 2022, CoinDesk published an article revealing that Alameda Research held a significant portion of its assets in FTT tokens, raising concerns about the financial stability of both companies.",
                "summary": "CoinDesk article exposes Alameda-FTX connection",
                "confidence_score": 0.95,
                "event_date": "2022-11-02",
                "temporal_context": "recent"
            },
            {
                "finding_type": "event",
                "content": "Binance CEO Changpeng Zhao announced on November 6 that Binance would sell its FTT holdings, triggering a massive sell-off and withdrawal run on FTX.",
                "summary": "Binance announces FTT sale",
                "confidence_score": 0.98,
                "event_date": "2022-11-06"
            },
            {
                "finding_type": "actor",
                "content": "Sam Bankman-Fried (SBF) was the founder and CEO of FTX, previously known for effective altruism advocacy and political donations. He maintained close ties with Alameda Research.",
                "summary": "Sam Bankman-Fried (SBF)",
                "confidence_score": 0.99,
                "extracted_data": {
                    "role": "Founder & CEO of FTX",
                    "affiliations": ["FTX", "Alameda Research", "Effective Altruism"],
                    "aliases": ["SBF"]
                }
            },
            {
                "finding_type": "actor",
                "content": "Caroline Ellison served as CEO of Alameda Research and was responsible for trading decisions that led to significant losses using customer funds.",
                "summary": "Caroline Ellison",
                "confidence_score": 0.92,
                "extracted_data": {
                    "role": "CEO of Alameda Research",
                    "affiliations": ["Alameda Research", "FTX"]
                }
            },
            {
                "finding_type": "relationship",
                "content": "FTX secretly transferred customer funds to Alameda Research to cover trading losses, creating an $8 billion shortfall.",
                "summary": "FTX-Alameda fund transfer",
                "confidence_score": 0.88
            },
            {
                "finding_type": "fact",
                "content": "FTX customer deposits totaled approximately $16 billion, with an estimated $8-10 billion missing.",
                "summary": "Missing customer funds",
                "confidence_score": 0.85
            },
            {
                "finding_type": "evidence",
                "content": "Internal documents revealed that FTX had a 'secret backdoor' that allowed transfers without proper accounting oversight.",
                "summary": "Secret backdoor in FTX systems",
                "confidence_score": 0.82,
                "extracted_data": {"source": "Court filings", "type": "documentary"}
            },
            {
                "finding_type": "pattern",
                "content": "A pattern of regulatory arbitrage emerged, with FTX operating from the Bahamas to avoid US regulations while actively courting US customers.",
                "summary": "Regulatory arbitrage pattern",
                "confidence_score": 0.78
            },
            {
                "finding_type": "gap",
                "content": "The exact timeline of when customer funds were first misappropriated remains unclear from public documents.",
                "confidence_score": 0.65
            }
        ],
        "perspectives": [
            {
                "perspective_type": "historical",
                "analysis_text": "The FTX collapse represents one of the largest financial frauds in history, comparable to Enron and WorldCom in scale and audacity.",
                "key_insights": [
                    "Concentration of power without oversight enabled fraud",
                    "Regulatory gaps in crypto allowed unchecked growth",
                    "Celebrity endorsements lent false legitimacy"
                ],
                "recommendations": [
                    "Implement mandatory segregation of customer funds",
                    "Require regular third-party audits for exchanges"
                ],
                "warnings": ["Similar structures exist at other crypto companies"],
                "confidence": 0.85
            },
            {
                "perspective_type": "economic",
                "analysis_text": "The economic impact extended beyond FTX investors, affecting the entire crypto market and legitimate projects.",
                "key_insights": [
                    "Market capitalization loss exceeded $200 billion",
                    "Contagion spread to BlockFi, Genesis, and others"
                ],
                "recommendations": ["Diversify crypto holdings", "Use regulated custodians"],
                "warnings": [],
                "confidence": 0.80
            }
        ],
        "sources": [
            {
                "url": "https://www.coindesk.com/business/2022/11/02/divisions-in-sam-bankman-frieds-crypto-empire-blur-on-his-trading-titan-alamedas-balance-sheet/",
                "title": "Divisions in Sam Bankman-Fried's Crypto Empire",
                "domain": "coindesk.com",
                "snippet": "A review of Alameda's balance sheet reveals...",
                "credibility_score": 0.92,
                "source_type": "news"
            },
            {
                "url": "https://www.sec.gov/litigation/complaints/2022/comp-pr2022-219.pdf",
                "title": "SEC Charges Samuel Bankman-Fried",
                "domain": "sec.gov",
                "snippet": "The Securities and Exchange Commission today charged...",
                "credibility_score": 0.98,
                "source_type": "government"
            }
        ],
        "claims": []
    }


def create_competitive_mock_data() -> Dict[str, Any]:
    """Create rich mock data for competitive intelligence."""
    return {
        "session_id": uuid4(),
        "session_title": "AI Code Assistant Market Analysis",
        "session_query": "Compare GitHub Copilot, Cursor, and Claude Code in the AI coding assistant market",
        "template_type": "competitive",
        "status": "completed",
        "parameters": {"max_searches": 12, "granularity": "detailed"},
        "created_at": datetime.now() - timedelta(hours=1),
        "completed_at": datetime.now(),
        "findings": [
            {
                "finding_type": "actor",
                "content": "GitHub Copilot is the market leader with an estimated 1.3 million paid subscribers as of 2024, leveraging GitHub's developer ecosystem.",
                "summary": "GitHub Copilot",
                "confidence_score": 0.95,
                "extracted_data": {
                    "market_position": "Market Leader",
                    "differentiators": ["GitHub integration", "Large training data", "Enterprise adoption"]
                }
            },
            {
                "finding_type": "actor",
                "content": "Cursor positions itself as a 'AI-first' IDE, differentiating through full editor replacement rather than plugin approach.",
                "summary": "Cursor",
                "confidence_score": 0.88,
                "extracted_data": {
                    "market_position": "Challenger",
                    "differentiators": ["Full IDE experience", "Multi-model support", "Context awareness"]
                }
            },
            {
                "finding_type": "actor",
                "content": "Claude Code offers terminal-based AI assistance with strong reasoning capabilities and agentic features.",
                "summary": "Claude Code",
                "confidence_score": 0.90,
                "extracted_data": {
                    "market_position": "Emerging",
                    "differentiators": ["Agentic capabilities", "Safety focus", "Extended context"]
                }
            },
            {
                "finding_type": "fact",
                "content": "The AI code assistant market is projected to reach $5.2 billion by 2028, growing at 25% CAGR.",
                "summary": "Market size projection",
                "confidence_score": 0.82
            },
            {
                "finding_type": "pattern",
                "content": "All major players are moving toward 'agentic' capabilities where AI can autonomously complete multi-step coding tasks.",
                "summary": "Agentic trend in AI coding",
                "confidence_score": 0.85
            },
            {
                "finding_type": "gap",
                "content": "Enterprise adoption metrics for Cursor and Claude Code are not publicly available for direct comparison.",
                "confidence_score": 0.60
            }
        ],
        "perspectives": [
            {
                "perspective_type": "competitive_advantage",
                "analysis_text": "Each player has distinct competitive advantages based on their positioning and technology.",
                "key_insights": [
                    "GitHub Copilot benefits from network effects and ecosystem lock-in",
                    "Cursor's IDE-first approach offers deeper integration",
                    "Claude Code's terminal approach suits power users and CI/CD workflows"
                ],
                "recommendations": [
                    "Consider multi-tool strategy for different use cases",
                    "Evaluate based on existing workflow and toolchain"
                ],
                "warnings": ["Rapid innovation may shift competitive dynamics quickly"],
                "confidence": 0.85
            },
            {
                "perspective_type": "pricing_strategy",
                "analysis_text": "Pricing varies significantly with different value propositions.",
                "key_insights": [
                    "Copilot: $10/month individual, $19/month business",
                    "Cursor: $20/month with usage-based model",
                    "Claude Code: Bundled with Claude Pro subscription"
                ],
                "recommendations": ["Calculate TCO including productivity gains"],
                "warnings": [],
                "confidence": 0.78
            }
        ],
        "sources": [
            {
                "url": "https://github.blog/2024-copilot-updates",
                "title": "GitHub Copilot 2024 Updates",
                "domain": "github.blog",
                "credibility_score": 0.90,
                "source_type": "corporate"
            },
            {
                "url": "https://www.cursor.com/about",
                "title": "About Cursor",
                "domain": "cursor.com",
                "credibility_score": 0.85,
                "source_type": "corporate"
            }
        ],
        "claims": []
    }


def create_financial_mock_data() -> Dict[str, Any]:
    """Create rich mock data for financial analysis."""
    return {
        "session_id": uuid4(),
        "session_title": "NVIDIA Investment Analysis",
        "session_query": "Should I invest in NVIDIA (NVDA) at current valuations given AI demand?",
        "template_type": "financial",
        "status": "completed",
        "parameters": {"max_searches": 10, "granularity": "detailed"},
        "created_at": datetime.now() - timedelta(hours=1),
        "completed_at": datetime.now(),
        "findings": [
            {
                "finding_type": "fact",
                "content": "NVIDIA reported Q3 FY2025 revenue of $35.1 billion, up 94% year-over-year, driven by data center demand.",
                "summary": "Q3 revenue growth",
                "confidence_score": 0.98,
                "extracted_data": {"metrics": [{"name": "Revenue", "value": "$35.1B", "context": "Q3 FY2025"}]}
            },
            {
                "finding_type": "fact",
                "content": "Data center segment generated $30.8 billion, representing 88% of total revenue.",
                "summary": "Data center dominance",
                "confidence_score": 0.97,
                "extracted_data": {"metrics": [{"name": "Data Center Revenue", "value": "$30.8B"}]}
            },
            {
                "finding_type": "event",
                "content": "NVIDIA announced Blackwell architecture GPUs shipping in Q4, with demand exceeding supply.",
                "summary": "Blackwell GPU launch",
                "confidence_score": 0.92,
                "event_date": "2024-11-20"
            },
            {
                "finding_type": "pattern",
                "content": "Gross margins have expanded from 64% to 75% over the past year as AI chip demand outpaces supply.",
                "summary": "Margin expansion trend",
                "confidence_score": 0.88,
                "extracted_data": {"metrics": [{"name": "Gross Margin", "value": "75%"}]}
            },
            {
                "finding_type": "fact",
                "content": "Current P/E ratio of 65x is elevated compared to historical average of 40x.",
                "summary": "Valuation metrics",
                "confidence_score": 0.90,
                "extracted_data": {"metrics": [{"name": "P/E Ratio", "value": "65x"}]}
            },
            {
                "finding_type": "gap",
                "content": "Long-term sustainability of AI infrastructure spending by hyperscalers remains uncertain.",
                "summary": "Demand sustainability question",
                "confidence_score": 0.70
            }
        ],
        "perspectives": [
            {
                "perspective_type": "valuation",
                "analysis_text": "NVIDIA trades at premium multiples justified by exceptional growth, but valuation leaves little room for disappointment.",
                "key_insights": [
                    "PEG ratio of 1.2x suggests reasonable growth-adjusted valuation",
                    "Forward P/E of 35x on 2025 estimates more reasonable",
                    "DCF analysis suggests fair value near current levels"
                ],
                "recommendations": [
                    "Consider dollar-cost averaging rather than lump sum",
                    "Set position size limits given volatility"
                ],
                "warnings": ["Any guidance miss could trigger significant correction"],
                "confidence": 0.82
            },
            {
                "perspective_type": "risk",
                "analysis_text": "Key risks include customer concentration, competition, and geopolitical factors.",
                "key_insights": [
                    "Top 5 customers represent 50%+ of data center revenue",
                    "AMD and Intel increasing AI chip investments",
                    "China export restrictions limit addressable market"
                ],
                "recommendations": ["Monitor hyperscaler capex guidance closely"],
                "warnings": ["Export restrictions could tighten further"],
                "confidence": 0.78
            }
        ],
        "sources": [
            {
                "url": "https://investor.nvidia.com/q3-2025-results",
                "title": "NVIDIA Q3 FY2025 Results",
                "domain": "investor.nvidia.com",
                "credibility_score": 0.99,
                "source_type": "sec_filing"
            }
        ],
        "claims": []
    }


def create_legal_mock_data() -> Dict[str, Any]:
    """Create rich mock data for legal research."""
    return {
        "session_id": uuid4(),
        "session_title": "GDPR Compliance for AI Companies",
        "session_query": "What are the GDPR compliance requirements for companies deploying AI systems in the EU?",
        "template_type": "legal",
        "status": "completed",
        "parameters": {"max_searches": 10, "granularity": "detailed"},
        "created_at": datetime.now() - timedelta(hours=1),
        "completed_at": datetime.now(),
        "findings": [
            {
                "finding_type": "fact",
                "content": "Article 22 of GDPR provides individuals the right not to be subject to decisions based solely on automated processing, including profiling, which produces legal or similarly significant effects.",
                "summary": "Article 22 - Automated Decision Making",
                "confidence_score": 0.98,
                "extracted_data": {"citation": "GDPR Article 22"}
            },
            {
                "finding_type": "fact",
                "content": "Data controllers must implement 'privacy by design and by default' when developing AI systems, as mandated by Article 25.",
                "summary": "Privacy by Design requirement",
                "confidence_score": 0.97,
                "extracted_data": {"citation": "GDPR Article 25"}
            },
            {
                "finding_type": "fact",
                "content": "A Data Protection Impact Assessment (DPIA) is mandatory under Article 35 when processing is likely to result in high risk to individuals, which typically includes AI systems.",
                "summary": "DPIA requirement",
                "confidence_score": 0.95,
                "extracted_data": {"citation": "GDPR Article 35"}
            },
            {
                "finding_type": "pattern",
                "content": "Courts have consistently interpreted 'meaningful human oversight' to require genuine human review capability, not merely rubber-stamping AI decisions.",
                "summary": "Human oversight interpretation",
                "confidence_score": 0.85
            },
            {
                "finding_type": "fact",
                "content": "Maximum GDPR fines can reach €20 million or 4% of global annual turnover, whichever is higher.",
                "summary": "Maximum penalties",
                "confidence_score": 0.99,
                "extracted_data": {"citation": "GDPR Article 83"}
            },
            {
                "finding_type": "gap",
                "content": "The intersection of GDPR and the new EU AI Act creates compliance uncertainties that regulators have not yet clarified.",
                "confidence_score": 0.72
            }
        ],
        "perspectives": [
            {
                "perspective_type": "compliance",
                "analysis_text": "GDPR compliance for AI requires a comprehensive approach covering data collection, processing, storage, and decision-making.",
                "key_insights": [
                    "Lawful basis must be established before collecting training data",
                    "Right to explanation applies to AI-driven decisions",
                    "Data minimization principle limits training data scope"
                ],
                "recommendations": [
                    "Conduct DPIA before deploying any AI system",
                    "Implement human review processes for high-stakes decisions",
                    "Document lawful basis for all training data",
                    "Establish data subject request handling procedures"
                ],
                "warnings": [
                    "Training on personal data without consent is high-risk",
                    "Cross-border data transfers require additional safeguards"
                ],
                "confidence": 0.88
            },
            {
                "perspective_type": "regulatory_risk",
                "analysis_text": "Enforcement actions against AI companies are increasing as regulators build expertise.",
                "key_insights": [
                    "Irish DPC has investigated major AI companies",
                    "French CNIL has issued guidance on AI training data",
                    "Italian Garante temporarily banned ChatGPT in 2023"
                ],
                "recommendations": [
                    "Engage with national DPAs proactively",
                    "Monitor enforcement trends across EU member states"
                ],
                "warnings": [],
                "confidence": 0.82
            }
        ],
        "sources": [
            {
                "url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
                "title": "General Data Protection Regulation (GDPR)",
                "domain": "eur-lex.europa.eu",
                "credibility_score": 1.0,
                "source_type": "regulation"
            },
            {
                "url": "https://edpb.europa.eu/our-work-tools/documents/public-consultations_en",
                "title": "EDPB Guidelines on AI and GDPR",
                "domain": "edpb.europa.eu",
                "credibility_score": 0.98,
                "source_type": "government"
            }
        ],
        "claims": []
    }


# Map template types to mock data generators
MOCK_DATA_GENERATORS = {
    "investigative": create_investigative_mock_data,
    "competitive": create_competitive_mock_data,
    "financial": create_financial_mock_data,
    "legal": create_legal_mock_data
}

# Map variants to their template type
VARIANT_TEMPLATES = {
    # Universal
    "executive_summary": "investigative",  # Works with any, using investigative
    "full_report": "investigative",
    "findings_only": "investigative",
    "source_bibliography": "investigative",
    # Investigative
    "timeline_report": "investigative",
    "actor_dossier": "investigative",
    "evidence_brief": "investigative",
    # Competitive
    "competitive_matrix": "competitive",
    "swot_analysis": "competitive",
    "battlecard": "competitive",
    # Financial
    "investment_thesis": "financial",
    "earnings_summary": "financial",
    "risk_assessment": "financial",
    # Legal
    "legal_brief": "legal",
    "case_digest": "legal",
    "compliance_checklist": "legal"
}


# =============================================================================
# TEST RUNNER
# =============================================================================

async def generate_report_variant(variant: str, generate_html: bool = False) -> Dict[str, Any]:
    """Generate a single report variant and return results."""
    import importlib.util

    # Determine template and get mock data
    template_type = VARIANT_TEMPLATES[variant]
    mock_data = MOCK_DATA_GENERATORS[template_type]()

    # Load schemas
    spec = importlib.util.spec_from_file_location(
        "report_schemas",
        _backend_dir / "app" / "research" / "reports" / "schemas.py"
    )
    schemas = importlib.util.module_from_spec(spec)
    sys.modules['app.research.reports.schemas'] = schemas
    spec.loader.exec_module(schemas)

    # Create ReportData
    data = schemas.ReportData(**mock_data)

    # Load composer
    # We need to handle relative imports by setting up the module hierarchy
    try:
        from app.research.reports.composers import get_composer
        from app.research.reports.schemas import ReportVariant

        composer = get_composer(variant)
        report_variant = ReportVariant(variant)

        # Generate markdown
        markdown = composer.compose(data, report_variant)

        result = {
            "variant": variant,
            "template_type": template_type,
            "markdown": markdown,
            "word_count": len(markdown.split()),
            "char_count": len(markdown),
            "success": True,
            "error": None
        }

        # Generate HTML if requested
        if generate_html:
            try:
                from app.research.reports.generators import create_html_generator

                generator = create_html_generator()
                html = await generator.generate(
                    markdown_content=markdown,
                    template_type=template_type,
                    title=f"{variant.replace('_', ' ').title()} Report"
                )
                result["html"] = html
                result["html_chars"] = len(html)
            except Exception as e:
                result["html"] = None
                result["html_error"] = str(e)

        return result

    except Exception as e:
        return {
            "variant": variant,
            "template_type": template_type,
            "success": False,
            "error": str(e)
        }


async def run_all_variants(generate_html: bool = False):
    """Run report generation for all variants."""
    print("\n" + "="*70)
    print(" REPORT VARIANT GENERATION TEST")
    print("="*70)
    print(f" Started: {datetime.now().isoformat()}")
    print(f" Generate HTML: {generate_html}")
    print(f" Output directory: {_results_dir}")
    print("="*70)

    variants = list(VARIANT_TEMPLATES.keys())
    results = []

    for i, variant in enumerate(variants, 1):
        print(f"\n[{i}/{len(variants)}] Generating: {variant}")

        result = await generate_report_variant(variant, generate_html)
        results.append(result)

        if result["success"]:
            print(f"    [OK] {result['word_count']} words, {result['char_count']} chars")

            # Save markdown
            md_path = _results_dir / f"{variant}.md"
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(result["markdown"])
            print(f"    Saved: {md_path.name}")

            # Save HTML if generated
            if result.get("html"):
                html_path = _results_dir / f"{variant}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(result["html"])
                print(f"    Saved: {html_path.name} ({result['html_chars']} chars)")
            elif result.get("html_error"):
                print(f"    HTML error: {result['html_error'][:50]}...")

        else:
            print(f"    [FAIL] {result['error']}")

    # Summary
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)

    success = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\n  Total variants: {len(variants)}")
    print(f"  Successful: {len(success)}")
    print(f"  Failed: {len(failed)}")

    if success:
        total_words = sum(r["word_count"] for r in success)
        total_chars = sum(r["char_count"] for r in success)
        print(f"\n  Total words generated: {total_words:,}")
        print(f"  Total characters: {total_chars:,}")
        print(f"  Average per report: {total_words // len(success)} words")

    if failed:
        print("\n  Failed variants:")
        for r in failed:
            print(f"    - {r['variant']}: {r['error'][:50]}...")

    # By template type
    print("\n  By template type:")
    for template in ["investigative", "competitive", "financial", "legal"]:
        template_results = [r for r in success if r["template_type"] == template]
        if template_results:
            words = sum(r["word_count"] for r in template_results)
            print(f"    {template}: {len(template_results)} variants, {words} words")

    print("\n" + "="*70)

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate all report variants with mock data")
    parser.add_argument("--html", action="store_true", help="Also generate HTML using LLM")
    args = parser.parse_args()

    try:
        results = asyncio.run(run_all_variants(generate_html=args.html))

        # Exit with error if any failed
        if any(not r["success"] for r in results):
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nTest interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
