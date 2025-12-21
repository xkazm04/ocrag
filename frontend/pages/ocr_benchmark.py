"""OCR Benchmark Arena - Streamlit Page."""
import os
import streamlit as st
import httpx

# Page config
st.set_page_config(
    page_title="OCR Benchmark Arena",
    page_icon="🔍",
    layout="wide"
)

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

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
    st.session_state.ocr_results = None
if "ocr_evaluation" not in st.session_state:
    st.session_state.ocr_evaluation = None


def process_document(file_bytes: bytes, filename: str, engines: list, languages: list, evaluate: bool):
    """Call OCR API to process document."""
    try:
        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                f"{BACKEND_URL}/api/ocr/process",
                files={"file": (filename, file_bytes)},
                params={
                    "engines": ",".join(engines) if engines else None,
                    "languages": ",".join(languages),
                    "include_evaluation": evaluate
                }
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"Error: {e}")
        return None


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
    available_engines = []

    if engine_info:
        for eng in engine_info.get("engines", []):
            status = "✅" if eng["available"] else "❌"
            label = f"{status} {eng['name']}"
            if st.checkbox(label, value=eng["available"], key=f"eng_{eng['id']}"):
                if eng["available"]:
                    available_engines.append(eng["id"])
    else:
        st.warning("Could not load engine info")
        available_engines = ["gpt", "gemini"]

    # Languages
    st.markdown("### 🌍 Languages")
    languages = st.multiselect(
        "Languages",
        ["en", "de", "fr", "es", "cs", "zh"],
        default=["en"],
        label_visibility="collapsed"
    )

    # Evaluation toggle
    run_evaluation = st.checkbox("Run LLM Evaluation", value=False)

    # Process button
    if st.button("🚀 Process Document", use_container_width=True, type="primary"):
        if not uploaded_file:
            st.warning("Please upload a document first")
        elif not available_engines:
            st.warning("Please select at least one engine")
        else:
            with st.spinner("Processing..."):
                result = process_document(
                    uploaded_file.getvalue(),
                    uploaded_file.name,
                    available_engines,
                    languages or ["en"],
                    run_evaluation
                )
                if result:
                    st.session_state.ocr_results = result.get("results", {})
                    st.session_state.ocr_evaluation = result.get("evaluation")
                    st.success(f"Processed in {result.get('total_time_ms', 0):.0f}ms")

with col_results:
    st.markdown("### 📊 Results")

    results = st.session_state.ocr_results
    evaluation = st.session_state.ocr_evaluation

    if not results:
        st.info("Upload a document and click Process to see results")
    else:
        # Group by category
        categories = {"llm": [], "open_llm": [], "traditional": []}
        for eid, res in results.items():
            cat = res.get("category", "traditional")
            categories[cat].append((eid, res))

        # Tabs
        tab_llm, tab_open, tab_trad = st.tabs([
            f"🤖 LLM ({len(categories['llm'])})",
            f"🔓 Open ({len(categories['open_llm'])})",
            f"📝 Traditional ({len(categories['traditional'])})"
        ])

        def render_results(items):
            if not items:
                st.markdown("*No results*")
                return
            for eid, res in items:
                success = res.get("success", False)
                time_ms = res.get("processing_time_ms", 0)
                cost = res.get("cost_usd")

                stats = f"⏱️ {time_ms:.0f}ms"
                if cost:
                    stats += f" | 💰 ${cost:.4f}"

                score_html = ""
                if evaluation and eid in evaluation:
                    score = evaluation[eid].get("composite_score", 0)
                    cls = "score-high" if score >= 80 else "score-medium" if score >= 60 else "score-low"
                    score_html = f"<span class='score-badge {cls}'>{score}/100</span>"

                st.markdown(f"""
                <div class="result-card">
                    <b>{eid.upper()}</b> {score_html}<br>
                    <small style="color:#94a3b8;">{stats}</small>
                </div>
                """, unsafe_allow_html=True)

                if success and res.get("text"):
                    with st.expander("View text"):
                        st.text_area("", res["text"], height=150, key=f"txt_{eid}", label_visibility="collapsed")
                elif not success:
                    st.error(res.get("error", "Failed"))

        with tab_llm:
            render_results(categories["llm"])
        with tab_open:
            render_results(categories["open_llm"])
        with tab_trad:
            render_results(categories["traditional"])
