"""
Streamlit UI for Intelligent RAG System.
Compact modern dark-themed interface with dual RAG modes.

This is the main entry point that imports and orchestrates modular components.
"""
import streamlit as st

# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Intelligent RAG",
    page_icon="brain",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Import modules
from styles import apply_styles
from state import init_session_state
from api import load_documents, load_agentic_stats
from components import render_header, render_document_list
from tabs import (
    render_map_rag_tab,
    render_sql_rag_tab,
    render_browser_tab,
    render_doc_map_tab,
    render_batch_test_tab,
    render_openai_tab,
)


def main():
    """Main application entry point."""
    # Apply styles and initialize state
    apply_styles()
    init_session_state()

    # Load initial data if not already loaded
    if not st.session_state.documents:
        load_documents()
        load_agentic_stats()

    # Render header with stats and upload
    render_header()

    # Main layout: document list sidebar + content area
    col_docs, col_main = st.columns([1, 4])

    # Document list sidebar
    with col_docs:
        render_document_list()

    # Main content with tabs
    with col_main:
        render_tabs()


def render_tabs():
    """Render the main content tabs."""
    tab_map, tab_agentic, tab_browser, tab_docmap, tab_batch, tab_openai = st.tabs([
        "Map RAG",
        "SQL RAG",
        "Browser",
        "Doc Map",
        "Batch Test",
        "OpenAI"
    ])

    with tab_map:
        render_map_rag_tab()

    with tab_agentic:
        render_sql_rag_tab()

    with tab_browser:
        render_browser_tab()

    with tab_docmap:
        render_doc_map_tab()

    with tab_batch:
        render_batch_test_tab()

    with tab_openai:
        render_openai_tab()


if __name__ == "__main__":
    main()
