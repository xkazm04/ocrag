"""Tab modules for the RAG application."""
from tabs.map_rag import render_map_rag_tab
from tabs.sql_rag import render_sql_rag_tab
from tabs.browser import render_browser_tab
from tabs.doc_map import render_doc_map_tab
from tabs.batch_test import render_batch_test_tab
from tabs.openai_search import render_openai_tab

__all__ = [
    "render_map_rag_tab",
    "render_sql_rag_tab",
    "render_browser_tab",
    "render_doc_map_tab",
    "render_batch_test_tab",
    "render_openai_tab",
]
