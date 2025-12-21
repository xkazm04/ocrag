"""OCR evaluation display component."""
import streamlit as st
from typing import Optional


def render_evaluation(results: dict, evaluation: Optional[dict]):
    """
    Render evaluation summary and details.

    Args:
        results: Dict of engine_id -> result dict
        evaluation: Dict of engine_id -> evaluation dict
    """
    if not results:
        return

    st.markdown("### 📊 Benchmark Summary")

    # Calculate summary stats
    successful = [
        (eid, r) for eid, r in results.items()
        if r.get("success") and r.get("text")
    ]

    if not successful:
        st.warning("No successful OCR results to summarize")
        return

    # Find best performers
    fastest = min(successful, key=lambda x: x[1].get("processing_time_ms", float("inf")))
    cheapest = min(
        [(eid, r) for eid, r in successful if r.get("cost_usd") is not None],
        key=lambda x: x[1].get("cost_usd", float("inf")),
        default=(None, None)
    )

    # Best by score if evaluation available
    best_score = None
    if evaluation:
        scored = [
            (eid, evaluation[eid])
            for eid in [e[0] for e in successful]
            if eid in evaluation
        ]
        if scored:
            best_score = max(scored, key=lambda x: x[1].get("composite_score", 0))

    # Render summary cards
    cols = st.columns(3)

    with cols[0]:
        st.markdown("**⚡ Fastest**")
        st.markdown(f"_{_get_name(fastest[0])}_")
        st.markdown(f"`{fastest[1].get('processing_time_ms', 0):.0f}ms`")

    with cols[1]:
        if cheapest[0]:
            st.markdown("**💰 Most Cost-Effective**")
            st.markdown(f"_{_get_name(cheapest[0])}_")
            cost = cheapest[1].get("cost_usd", 0)
            st.markdown(f"`${cost:.4f}`" if cost > 0 else "`Free`")

    with cols[2]:
        if best_score:
            st.markdown("**🏆 Best Quality**")
            st.markdown(f"_{_get_name(best_score[0])}_")
            st.markdown(f"`{best_score[1].get('composite_score', 0)}/100`")

    # Detailed evaluation breakdown
    if evaluation:
        st.markdown("### 📈 Quality Scores")

        for engine_id in [e[0] for e in successful]:
            if engine_id not in evaluation:
                continue

            eval_data = evaluation[engine_id]
            _render_engine_evaluation(engine_id, eval_data)


def _render_engine_evaluation(engine_id: str, eval_data: dict):
    """Render evaluation details for one engine."""
    name = _get_name(engine_id)
    composite = eval_data.get("composite_score", 0)
    grammar = eval_data.get("grammar_score", 0)
    structure = eval_data.get("structure_score", 0)
    style = eval_data.get("style_score", 0)

    with st.expander(f"{name} - Score: {composite}/100"):
        # Score bars
        cols = st.columns(3)
        with cols[0]:
            st.metric("Grammar", f"{grammar}/100")
        with cols[1]:
            st.metric("Structure", f"{structure}/100")
        with cols[2]:
            st.metric("Style", f"{style}/100")

        # Issues
        issues = eval_data.get("issues", [])
        if issues:
            st.markdown("**Issues Found:**")
            for issue in issues[:5]:
                desc = issue.get("description", str(issue))
                st.markdown(f"- {desc}")

        # Recommendations
        recs = eval_data.get("recommendations", [])
        if recs:
            st.markdown("**Recommendations:**")
            for rec in recs[:3]:
                st.markdown(f"- {rec}")

        # Summary
        summary = eval_data.get("summary", "")
        if summary:
            st.markdown(f"**Summary:** {summary}")


def _get_name(engine_id: str) -> str:
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
