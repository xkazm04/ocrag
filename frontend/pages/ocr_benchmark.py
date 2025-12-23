"""OCR Benchmark Arena - Streamlit Page with async processing."""
import os
import streamlit as st
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Page config
st.set_page_config(
    page_title="OCR Benchmark Arena",
    page_icon="🔍",
    layout="wide"
)

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Engine display names
ENGINE_NAMES = {
    "gpt": "GPT-5.2",
    "gemini": "Gemini 3 Flash",
    "mistral": "Mistral OCR",
    "qwen": "Qwen2 VL",
    "paddle": "PaddleOCR",
    "easy": "EasyOCR",
    "surya": "Surya OCR"
}

ENGINE_ORDER = ["gpt", "gemini", "mistral", "qwen", "paddle", "easy", "surya"]

# Custom styles
st.markdown("""
<style>
.ocr-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
    padding: 1.5rem;
    border-radius: 8px;
    margin-bottom: 1rem;
}
.ocr-header-title { color: white; font-size: 1.5rem; font-weight: 600; }
.ocr-header-sub { color: #94a3b8; font-size: 0.85rem; }
.result-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
}
.score-badge {
    display: inline-block;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}
.score-high { background: #166534; color: #86efac; }
.score-medium { background: #854d0e; color: #fde047; }
.score-low { background: #991b1b; color: #fca5a5; }
.engine-card {
    background: #1e293b;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    border-left: 4px solid;
}
.engine-card.rank-1 { border-color: #fbbf24; }
.engine-card.rank-2 { border-color: #94a3b8; }
.engine-card.rank-3 { border-color: #b45309; }
.score-bar {
    height: 8px;
    border-radius: 4px;
    background: #374151;
    margin: 4px 0;
}
.score-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
}
.score-fill.high { background: linear-gradient(90deg, #22c55e, #16a34a); }
.score-fill.medium { background: linear-gradient(90deg, #eab308, #ca8a04); }
.score-fill.low { background: linear-gradient(90deg, #ef4444, #dc2626); }
.loading-card {
    background: #1e293b;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
}
.status-pending { color: #94a3b8; }
.status-running { color: #3b82f6; }
.status-success { color: #22c55e; }
.status-error { color: #ef4444; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="ocr-header">
    <div class="ocr-header-title">🔍 OCR Benchmark Arena</div>
    <div class="ocr-header-sub">Compare OCR solutions across LLM, Open LLM, and Traditional engines</div>
</div>
""", unsafe_allow_html=True)

# Session state
if "ocr_results" not in st.session_state:
    st.session_state.ocr_results = {}
if "ocr_evaluation" not in st.session_state:
    st.session_state.ocr_evaluation = None
if "processing_status" not in st.session_state:
    st.session_state.processing_status = {}


def process_single_engine(file_bytes: bytes, filename: str, engine_id: str, languages: list):
    """Process document with a single engine."""
    try:
        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                f"{BACKEND_URL}/api/ocr/process/{engine_id}",
                files={"file": (filename, file_bytes)},
                params={"languages": ",".join(languages)}
            )
            response.raise_for_status()
            return engine_id, response.json()
    except httpx.TimeoutException:
        return engine_id, {"success": False, "error": "Request timeout", "engine": engine_id}
    except Exception as e:
        return engine_id, {"success": False, "error": str(e), "engine": engine_id}


def run_evaluation(results: dict, language: str):
    """Run comparative evaluation on results."""
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{BACKEND_URL}/api/ocr/evaluate",
                json={
                    "results": results,
                    "language": language
                }
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"summary": f"Evaluation failed: {str(e)}", "engines": []}


def get_engine_info():
    """Get available engines from API."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{BACKEND_URL}/api/ocr/info")
            response.raise_for_status()
            return response.json()
    except Exception:
        return None


# Layout
col_upload, col_results = st.columns([1, 2])

with col_upload:
    st.markdown("### 📤 Upload Document")

    uploaded_file = st.file_uploader(
        "Upload image or PDF",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        if uploaded_file.type.startswith("image/"):
            st.image(uploaded_file, width=250)
        else:
            st.info(f"📄 {uploaded_file.name}")

    # Engine selection
    st.markdown("### ⚙️ Engines")

    engine_info = get_engine_info()
    selected_engines = []

    if engine_info:
        for eng in engine_info.get("engines", []):
            status = "✅" if eng["available"] else "❌"
            label = f"{status} {eng['name']}"
            if st.checkbox(label, value=eng["available"], key=f"eng_{eng['id']}"):
                if eng["available"]:
                    selected_engines.append(eng["id"])
    else:
        st.warning("Could not load engine info")
        selected_engines = ["gpt", "gemini"]

    # Languages
    st.markdown("### 🌍 Languages")
    languages = st.multiselect(
        "Languages",
        ["en", "de", "fr", "es", "cs", "zh"],
        default=["en"],
        label_visibility="collapsed"
    )

    # Evaluation toggle
    run_eval = st.checkbox("Run LLM Evaluation", value=False)

    # Process button
    if st.button("🚀 Process Document", use_container_width=True, type="primary"):
        if not uploaded_file:
            st.warning("Please upload a document first")
        elif not selected_engines:
            st.warning("Please select at least one engine")
        else:
            # Reset state
            st.session_state.ocr_results = {}
            st.session_state.ocr_evaluation = None
            st.session_state.processing_status = {eng: "pending" for eng in selected_engines}

            file_bytes = uploaded_file.getvalue()
            filename = uploaded_file.name
            langs = languages or ["en"]

            # Create progress container
            progress_container = st.empty()

            # Process engines in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=len(selected_engines)) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(process_single_engine, file_bytes, filename, eng, langs): eng
                    for eng in selected_engines
                }

                # Update UI as each completes
                completed = 0
                for future in as_completed(futures):
                    engine_id = futures[future]
                    try:
                        eng_id, result = future.result()
                        st.session_state.ocr_results[eng_id] = result
                        st.session_state.processing_status[eng_id] = "success" if result.get("success", False) else "error"
                    except Exception as e:
                        st.session_state.ocr_results[engine_id] = {
                            "success": False,
                            "error": str(e),
                            "engine": engine_id
                        }
                        st.session_state.processing_status[engine_id] = "error"

                    completed += 1
                    progress_container.progress(completed / len(selected_engines), f"Completed {completed}/{len(selected_engines)} engines")

            progress_container.empty()
            st.success(f"Processed {len(selected_engines)} engines")

            # Run evaluation if enabled and we have results
            if run_eval and st.session_state.ocr_results:
                with st.spinner("Running LLM evaluation..."):
                    eval_result = run_evaluation(st.session_state.ocr_results, langs[0])
                    st.session_state.ocr_evaluation = eval_result

            st.rerun()

with col_results:
    results = st.session_state.ocr_results
    evaluation = st.session_state.ocr_evaluation
    status = st.session_state.processing_status

    if not results and not status:
        st.info("Upload a document and click Process to see results")
    else:
        # Add manual evaluation button if we have results but no evaluation
        if results and not evaluation:
            successful_results = {k: v for k, v in results.items() if v.get("success") and v.get("text")}
            if len(successful_results) >= 2:
                if st.button("🔍 Run LLM Comparative Evaluation", use_container_width=True):
                    with st.spinner("Running LLM evaluation..."):
                        eval_result = run_evaluation(results, "en")
                        st.session_state.ocr_evaluation = eval_result
                    st.rerun()
        # Show processing status for each engine
        if status:
            st.markdown("### ⚡ Processing Status")
            status_cols = st.columns(min(len(status), 4))
            for i, (eng_id, eng_status) in enumerate(status.items()):
                col_idx = i % len(status_cols)
                with status_cols[col_idx]:
                    icon = {"pending": "⏳", "running": "🔄", "success": "✅", "error": "❌"}.get(eng_status, "❓")
                    st.markdown(f"{icon} **{ENGINE_NAMES.get(eng_id, eng_id)}**")
            st.markdown("---")

        # Show comparative evaluation if available
        if evaluation and evaluation.get("engines"):
            st.markdown("### 🏆 Comparative Analysis")

            if evaluation.get("summary"):
                st.markdown(f"*{evaluation.get('summary')}*")

            if evaluation.get("methodology"):
                st.caption(f"📊 {evaluation.get('methodology')}")

            st.markdown("---")

            engines_data = evaluation.get("engines", [])

            for eng in engines_data:
                rank = eng.get("rank", 0)
                rank_class = f"rank-{rank}" if rank <= 3 else ""
                rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")

                overall = eng.get("overall_score", 0)
                accuracy = eng.get("accuracy_score", 0)
                completeness = eng.get("completeness_score", 0)
                formatting = eng.get("formatting_score", 0)

                def score_class(score):
                    return "high" if score >= 75 else "medium" if score >= 50 else "low"

                st.markdown(f"""
                <div class="engine-card {rank_class}">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:1.1rem;font-weight:600;color:white;">
                            {rank_emoji} {eng.get('engine_name', eng.get('engine_id'))}
                        </span>
                        <span style="font-size:1.5rem;font-weight:700;color:{'#22c55e' if overall >= 75 else '#eab308' if overall >= 50 else '#ef4444'};">
                            {overall:.0f}%
                        </span>
                    </div>
                    <div style="color:#94a3b8;font-size:0.75rem;margin-bottom:0.5rem;">
                        {eng.get('category', 'traditional').upper()}
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;margin-top:0.5rem;">
                        <div>
                            <div style="color:#94a3b8;font-size:0.7rem;">Accuracy</div>
                            <div class="score-bar"><div class="score-fill {score_class(accuracy)}" style="width:{accuracy}%;"></div></div>
                            <div style="color:white;font-size:0.8rem;">{accuracy:.0f}%</div>
                        </div>
                        <div>
                            <div style="color:#94a3b8;font-size:0.7rem;">Completeness</div>
                            <div class="score-bar"><div class="score-fill {score_class(completeness)}" style="width:{completeness}%;"></div></div>
                            <div style="color:white;font-size:0.8rem;">{completeness:.0f}%</div>
                        </div>
                        <div>
                            <div style="color:#94a3b8;font-size:0.7rem;">Formatting</div>
                            <div class="score-bar"><div class="score-fill {score_class(formatting)}" style="width:{formatting}%;"></div></div>
                            <div style="color:white;font-size:0.8rem;">{formatting:.0f}%</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                strengths = eng.get("strengths", [])
                weaknesses = eng.get("weaknesses", [])
                if strengths or weaknesses:
                    with st.expander(f"Details for {eng.get('engine_name', eng.get('engine_id'))}"):
                        if strengths:
                            st.markdown("**Strengths:**")
                            for s in strengths:
                                st.markdown(f"- ✅ {s}")
                        if weaknesses:
                            st.markdown("**Weaknesses:**")
                            for w in weaknesses:
                                st.markdown(f"- ⚠️ {w}")

            st.markdown("---")

        # Results tabs
        if results:
            st.markdown("### 📄 Extracted Text")

            available_results = [e for e in ENGINE_ORDER if e in results]

            if available_results:
                tab_labels = [ENGINE_NAMES.get(e, e.upper()) for e in available_results]
                tabs = st.tabs(tab_labels)

                for i, engine_id in enumerate(available_results):
                    with tabs[i]:
                        res = results[engine_id]
                        success = res.get("success", False)
                        time_ms = res.get("processing_time_ms", 0)
                        cost = res.get("cost_usd")
                        category = res.get("category", "traditional")

                        cat_colors = {
                            "llm": ("#3b82f6", "LLM"),
                            "open_llm": ("#8b5cf6", "Open LLM"),
                            "traditional": ("#10b981", "Traditional")
                        }
                        cat_color, cat_label = cat_colors.get(category, ("#6b7280", "Other"))

                        stats_parts = [f"⏱️ {time_ms:.0f}ms"]
                        if cost is not None:
                            stats_parts.append(f"💰 ${cost:.4f}")

                        st.markdown(f"""
                        <div class="result-card">
                            <span style="background:{cat_color};color:white;padding:2px 8px;border-radius:4px;font-size:0.7rem;">{cat_label}</span>
                            <br><small style="color:#94a3b8;">{' | '.join(stats_parts)}</small>
                        </div>
                        """, unsafe_allow_html=True)

                        if success and res.get("text"):
                            st.text_area(
                                "Extracted Text",
                                res["text"],
                                height=350,
                                key=f"txt_{engine_id}",
                                label_visibility="collapsed"
                            )
                        elif not success:
                            st.error(res.get("error", "Processing failed"))
            else:
                st.warning("No results available")
