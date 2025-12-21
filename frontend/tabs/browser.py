"""Document browser tab for viewing document chunks."""
import streamlit as st
from api import load_document_chunks
from config import MAX_CONTENT_PREVIEW, DEFAULT_PREVIEW_CHARS


def render_browser_tab():
    """Render the document browser interface."""
    if not st.session_state.documents:
        st.info("No documents. Upload some first.")
        return

    _render_document_selector()
    _render_chunk_viewer()


def _render_document_selector():
    """Render document selection UI."""
    col_sel, col_load = st.columns([4, 1])

    with col_sel:
        doc_options = {
            d['id']: f"{d['filename']} ({d['token_count']:,}t)"
            for d in st.session_state.documents
        }
        selected_id = st.selectbox(
            "Document",
            list(doc_options.keys()),
            format_func=lambda x: doc_options[x],
            label_visibility="collapsed",
            key="browser_doc_select"
        )
        st.session_state._browser_selected_id = selected_id

    with col_load:
        if st.button("Load", use_container_width=True):
            load_document_chunks(st.session_state._browser_selected_id)


def _render_chunk_viewer():
    """Render chunk viewer if document is loaded."""
    selected_id = getattr(st.session_state, '_browser_selected_id', None)

    if not st.session_state.selected_doc_chunks:
        st.markdown(
            "<div style='color:#6b7280;text-align:center;padding:1rem;'>"
            "Select document and click Load</div>",
            unsafe_allow_html=True
        )
        return

    if st.session_state.selected_doc_id != selected_id:
        return

    data = st.session_state.selected_doc_chunks
    _render_document_info(data)

    if data['chunks']:
        _render_chunk_selector(data)


def _render_document_info(data: dict):
    """Render document info header."""
    col_info, _ = st.columns([2, 3])
    with col_info:
        st.markdown(f"**{data['filename']}** - {data['total']} chunk(s)")


def _render_chunk_selector(data: dict):
    """Render chunk selector and content viewer."""
    chunk_opts = {
        i: f"#{i+1}: {c['section'][:30]} ({c['position']})"
        for i, c in enumerate(data['chunks'])
    }

    idx = st.selectbox(
        "Chunk",
        list(chunk_opts.keys()),
        format_func=lambda x: chunk_opts[x],
        label_visibility="collapsed",
        key="browser_chunk_select"
    )

    if idx is not None:
        chunk = data['chunks'][idx]
        _render_chunk_content(chunk)


def _render_chunk_content(chunk: dict):
    """Render chunk metadata and content."""
    # Metadata grid
    st.markdown(f"""
    <div class="chunk-meta">
        <div class="chunk-meta-item">
            <div class="chunk-meta-label">ID</div>
            <div class="chunk-meta-value">{chunk['chunk_id']}</div>
        </div>
        <div class="chunk-meta-item">
            <div class="chunk-meta-label">Position</div>
            <div class="chunk-meta-value">{chunk['position']}</div>
        </div>
        <div class="chunk-meta-item">
            <div class="chunk-meta-label">Tokens</div>
            <div class="chunk-meta-value">{chunk['token_count']:,}</div>
        </div>
        <div class="chunk-meta-item">
            <div class="chunk-meta-label">Section</div>
            <div class="chunk-meta-value">{chunk['section'][:25]}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Context if available
    if chunk.get('context'):
        st.markdown(
            f"<div class='info-box'><b>Context:</b> {chunk['context']}</div>",
            unsafe_allow_html=True
        )

    # Content preview
    content = chunk['content']
    max_len = min(MAX_CONTENT_PREVIEW, len(content))
    preview_len = st.slider(
        "Preview chars",
        500, max_len,
        min(DEFAULT_PREVIEW_CHARS, max_len),
        100,
        label_visibility="collapsed"
    )

    preview = content[:preview_len]
    if len(content) > preview_len:
        preview += "\n...[truncated]"

    st.markdown(f"<div class='code-preview'>{preview}</div>", unsafe_allow_html=True)
    st.caption(f"{min(preview_len, len(content)):,} / {len(content):,} chars")
