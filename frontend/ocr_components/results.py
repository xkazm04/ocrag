"""OCR results display component."""
import streamlit as st
from typing import Optional


def render_results(results: dict, evaluation: Optional[dict] = None):
    """
    Render OCR results in categorized tabs.

    Args:
        results: Dict of engine_id -> result dict
        evaluation: Optional dict of engine_id -> evaluation dict
    """
    if not results:
        st.info("No results yet. Upload a document and process it.")
        return

    # Group by category
    llm_results = {}
    open_llm_results = {}
    traditional_results = {}

    for engine_id, result in results.items():
        category = result.get("category", "traditional")
        if category == "llm":
            llm_results[engine_id] = result
        elif category == "open_llm":
            open_llm_results[engine_id] = result
        else:
            traditional_results[engine_id] = result

    # Create tabs
    tab_llm, tab_open, tab_trad = st.tabs([
        f"🤖 LLM APIs ({len(llm_results)})",
        f"🔓 Open LLM ({len(open_llm_results)})",
        f"📝 Traditional ({len(traditional_results)})"
    ])

    with tab_llm:
        _render_category_results(llm_results, evaluation)

    with tab_open:
        _render_category_results(open_llm_results, evaluation)

    with tab_trad:
        _render_category_results(traditional_results, evaluation)


def _render_category_results(results: dict, evaluation: Optional[dict]):
    """Render results for a category."""
    if not results:
        st.markdown("*No engines processed in this category*")
        return

    for engine_id, result in results.items():
        _render_single_result(engine_id, result, evaluation)


def _render_single_result(engine_id: str, result: dict, evaluation: Optional[dict]):
    """Render a single engine result."""
    success = result.get("success", False)
    engine_name = _get_engine_name(engine_id)

    # Header with stats
    time_ms = result.get("processing_time_ms", 0)
    cost = result.get("cost_usd")
    tokens = result.get("tokens_used")

    stats_parts = [f"⏱️ {time_ms:.0f}ms"]
    if cost is not None:
        stats_parts.append(f"💰 ${cost:.4f}")
    if tokens:
        stats_parts.append(f"🔤 {tokens} tokens")

    # Get evaluation score if available
    eval_score = None
    if evaluation and engine_id in evaluation:
        eval_score = evaluation[engine_id].get("composite_score", 0)

    # Render card
    status_class = "available" if success else "unavailable"
    score_html = ""
    if eval_score is not None:
        score_class = "score-high" if eval_score >= 80 else "score-medium" if eval_score >= 60 else "score-low"
        score_html = f"<span class='score-badge {score_class}'>{eval_score}/100</span>"

    st.markdown(f"""
    <div class="result-card">
        <div class="result-header">
            <span class="result-engine">{engine_name} {score_html}</span>
            <span class="result-stats">{' | '.join(stats_parts)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if success:
        text = result.get("text", "")
        if text:
            with st.expander("View extracted text", expanded=False):
                st.text_area(
                    "Extracted text",
                    value=text,
                    height=200,
                    key=f"text_{engine_id}",
                    label_visibility="collapsed"
                )
        else:
            st.warning("No text extracted")
    else:
        error = result.get("error", "Unknown error")
        st.markdown(f"<div class='error-msg'>❌ {error}</div>", unsafe_allow_html=True)


def _get_engine_name(engine_id: str) -> str:
    """Get display name for engine."""
    names = {
        "gpt": "GPT-4o",
        "gemini": "Gemini 2.0 Flash",
        "mistral": "Mistral OCR",
        "qwen": "Qwen2 VL 72B",
        "paddle": "PaddleOCR",
        "easy": "EasyOCR",
        "surya": "Surya OCR",
    }
    return names.get(engine_id, engine_id)
