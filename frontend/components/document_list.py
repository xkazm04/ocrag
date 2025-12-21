"""Document list sidebar component."""
import streamlit as st
from api import load_documents, load_agentic_stats, delete_document
from state import clear_chat_messages
from config import MAX_FILENAME_DISPLAY


def render_document_list():
    """Render the document list in the sidebar."""
    st.markdown("#### Documents")

    _render_action_buttons()
    _render_documents()


def _render_action_buttons():
    """Render refresh and clear chat buttons."""
    col_ref, col_clr = st.columns(2)

    with col_ref:
        if st.button("Refresh", help="Refresh documents", use_container_width=True):
            load_documents()
            load_agentic_stats()
            st.rerun()

    with col_clr:
        if st.button("Clear Chat", use_container_width=True):
            clear_chat_messages()
            st.rerun()


def _render_documents():
    """Render the document list."""
    if not st.session_state.documents:
        st.markdown(
            "<div style='color:#6b7280;font-size:0.8rem;'>No documents</div>",
            unsafe_allow_html=True
        )
        return

    for doc in st.session_state.documents:
        cols = st.columns([5, 1])

        with cols[0]:
            name = doc['filename']
            short_name = name[:MAX_FILENAME_DISPLAY]
            if len(name) > MAX_FILENAME_DISPLAY:
                short_name += '...'

            chunks_info = f"{doc['chunk_count']}c" if doc['chunk_count'] > 0 else "full"

            st.markdown(f"""
            <div class="doc-row">
                <span class="doc-name" title="{name}">{short_name}</span>
                <span class="doc-meta">{doc['token_count']:,}t | {chunks_info}</span>
            </div>
            """, unsafe_allow_html=True)

        with cols[1]:
            if st.button("x", key=f"del_{doc['id']}", help="Delete"):
                delete_document(doc['id'])
                st.rerun()
