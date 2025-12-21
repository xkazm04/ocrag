"""Header component with stats and upload functionality."""
import streamlit as st
from api import load_documents, load_agentic_stats, upload_document
from config import ALLOWED_DOC_TYPES


def render_header():
    """Render the header row with title, stats, and upload."""
    col_title, col_stats, col_upload = st.columns([2, 3, 3])

    with col_title:
        st.markdown("## RAG System")

    with col_stats:
        _render_stats()

    with col_upload:
        _render_upload()

    st.markdown("<hr style='margin:0.3rem 0;'>", unsafe_allow_html=True)


def _render_stats():
    """Render the stats row."""
    docs = st.session_state.documents
    stats = st.session_state.agentic_stats or {}
    total_tokens = sum(d['token_count'] for d in docs) if docs else 0

    st.markdown(f"""
    <div class="stats-row">
        <div class="stat-item">
            <div class="stat-value">{len(docs)}</div>
            <div class="stat-label">Docs</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{total_tokens:,}</div>
            <div class="stat-label">Tokens</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{stats.get('claims', 0)}</div>
            <div class="stat-label">Claims</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{stats.get('entities', 0)}</div>
            <div class="stat-label">Entities</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_upload():
    """Render the upload expander."""
    with st.expander("Upload Documents", expanded=False):
        uploaded_files = st.file_uploader(
            "Drop files",
            type=ALLOWED_DOC_TYPES,
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        if uploaded_files:
            col_mode, col_btn = st.columns([2, 1])
            with col_mode:
                extraction_mode = st.selectbox(
                    "Mode",
                    ["both", "map_only", "sql_only"],
                    label_visibility="collapsed"
                )
            with col_btn:
                if st.button("Process All", use_container_width=True):
                    _process_uploads(uploaded_files, extraction_mode)


def _process_uploads(uploaded_files, extraction_mode: str):
    """Process uploaded files."""
    progress = st.empty()
    results = []

    for i, file in enumerate(uploaded_files):
        progress.markdown(f"Processing {i+1}/{len(uploaded_files)}: {file.name}...")
        result = upload_document(file, extraction_mode)
        results.append((file.name, result))

    progress.empty()

    # Show results
    result_html = "<div style='font-size:0.8rem;'>"
    for name, r in results:
        if r and "error" not in r:
            result_html += f"<div class='upload-item upload-ok'>OK {name}</div>"
        else:
            err = r.get('error', 'Unknown error') if r else 'Failed'
            result_html += f"<div class='upload-item upload-err'>ERR {name}: {err}</div>"
    result_html += "</div>"
    st.markdown(result_html, unsafe_allow_html=True)

    load_documents()
    load_agentic_stats()
