"""CSS styles for the Streamlit UI."""
import streamlit as st


def apply_styles():
    """Apply compact dark theme CSS styles."""
    st.markdown(MAIN_STYLES, unsafe_allow_html=True)


MAIN_STYLES = """
<style>
    /* Reduce default padding but add top space for Streamlit bar */
    .block-container {
        padding: 2.5rem 1rem 0 1rem !important;
        max-width: 100% !important;
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Main dark theme */
    .stApp { background-color: #0e1117; }

    /* Sidebar compact */
    [data-testid="stSidebar"] {
        background-color: #1a1d24;
        border-right: 1px solid #2d3139;
    }
    [data-testid="stSidebar"] .block-container { padding: 0.5rem !important; }

    /* Compact headers */
    h1 { font-size: 1.5rem !important; margin: 0 0 0.5rem 0 !important; }
    h2 { font-size: 1.2rem !important; margin: 0 0 0.3rem 0 !important; }
    h3 { font-size: 1rem !important; margin: 0 0 0.2rem 0 !important; }
    h4 { font-size: 0.9rem !important; margin: 0 !important; }

    /* Compact messages */
    .msg { padding: 0.5rem; border-radius: 6px; margin: 0.3rem 0; font-size: 0.85rem; }
    .msg-user { background: #1e3a5f; border-left: 2px solid #4a9eff; }
    .msg-assistant { background: #1a1d24; border-left: 2px solid #10b981; }
    .msg-agentic { background: #1a1d24; border-left: 2px solid #f59e0b; }
    .msg-header { font-weight: 600; font-size: 0.75rem; color: #9ca3af; margin-bottom: 0.2rem; }

    /* Compact document cards */
    .doc-row {
        display: flex; align-items: center; justify-content: space-between;
        background: #1a1d24; padding: 0.4rem 0.6rem; border-radius: 4px;
        margin: 0.2rem 0; border: 1px solid #2d3139; font-size: 0.8rem;
    }
    .doc-row:hover { border-color: #4a9eff; }
    .doc-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .doc-meta { color: #6b7280; font-size: 0.7rem; margin-left: 0.5rem; }

    /* Compact stats */
    .stats-row {
        display: flex; gap: 1rem; background: #1a1d24;
        padding: 0.4rem 0.8rem; border-radius: 4px; margin: 0.3rem 0;
    }
    .stat-item { text-align: center; }
    .stat-value { font-size: 1.1rem; font-weight: 600; color: #4a9eff; }
    .stat-label { font-size: 0.65rem; color: #6b7280; text-transform: uppercase; }

    /* SQL/reasoning boxes */
    .info-box {
        background: #161b22; padding: 0.4rem 0.6rem; border-radius: 4px;
        margin: 0.2rem 0; font-size: 0.75rem; color: #8b949e;
    }

    /* Badges */
    .badge {
        background: #2d3139; padding: 0.1rem 0.4rem; border-radius: 3px;
        font-size: 0.7rem; color: #9ca3af; display: inline-block; margin: 0.1rem;
    }

    /* Confidence colors */
    .conf-high { color: #10b981; }
    .conf-med { color: #f59e0b; }
    .conf-low { color: #ef4444; }

    /* Compact tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] {
        background: #1a1d24; border-radius: 4px 4px 0 0;
        color: #9ca3af; padding: 0.3rem 0.8rem; font-size: 0.85rem;
    }
    .stTabs [aria-selected="true"] { background: #2d3139; color: #fff; }

    /* Compact buttons */
    .stButton > button {
        background: #4a9eff; color: white; border: none;
        border-radius: 4px; padding: 0.3rem 0.6rem; font-size: 0.8rem;
    }
    .stButton > button:hover { background: #3a8eef; }

    /* Compact file uploader */
    [data-testid="stFileUploader"] {
        background: #1a1d24; border: 1px dashed #2d3139;
        border-radius: 4px; padding: 0.5rem;
    }
    [data-testid="stFileUploader"] section { padding: 0 !important; }
    [data-testid="stFileUploader"] small { font-size: 0.7rem !important; }

    /* Compact metrics */
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; }

    /* Compact expander */
    .streamlit-expanderHeader { font-size: 0.8rem !important; padding: 0.3rem !important; }
    .streamlit-expanderContent { padding: 0.3rem !important; }

    /* Compact selectbox */
    .stSelectbox label { font-size: 0.8rem !important; }

    /* Compact divider */
    hr { margin: 0.5rem 0 !important; }

    /* Upload progress */
    .upload-item {
        display: flex; align-items: center; gap: 0.5rem;
        padding: 0.3rem; font-size: 0.8rem;
    }
    .upload-ok { color: #10b981; }
    .upload-err { color: #ef4444; }

    /* Code preview */
    .code-preview {
        background: #0d1117; padding: 0.5rem; border-radius: 4px;
        border: 1px solid #30363d; font-family: monospace;
        white-space: pre-wrap; font-size: 0.75rem; max-height: 400px;
        overflow-y: auto;
    }

    /* Chunk metadata grid */
    .chunk-meta {
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 0.5rem; background: #1a1d24; padding: 0.5rem;
        border-radius: 4px; margin: 0.3rem 0;
    }
    .chunk-meta-item { font-size: 0.75rem; }
    .chunk-meta-label { color: #6b7280; }
    .chunk-meta-value { color: #fff; font-weight: 500; }

    /* Document Map Styles */
    .map-section {
        background: #1a1d24; border-radius: 6px; padding: 0.6rem;
        margin: 0.4rem 0; border: 1px solid #2d3139;
    }
    .map-section-title {
        font-size: 0.8rem; font-weight: 600; color: #4a9eff;
        margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.3rem;
    }
    .map-doc-card {
        background: #161b22; border-radius: 4px; padding: 0.5rem;
        margin: 0.3rem 0; border-left: 2px solid #4a9eff;
    }
    .map-doc-title { font-weight: 600; font-size: 0.8rem; color: #fff; }
    .map-doc-essence { font-size: 0.75rem; color: #9ca3af; margin: 0.2rem 0; }
    .map-doc-meta { font-size: 0.7rem; color: #6b7280; }
    .map-topics { display: flex; flex-wrap: wrap; gap: 0.2rem; margin-top: 0.3rem; }
    .map-topic {
        background: #2d3139; padding: 0.1rem 0.4rem; border-radius: 3px;
        font-size: 0.65rem; color: #9ca3af;
    }
    .map-entity-section { margin: 0.3rem 0; }
    .map-entity-type {
        font-size: 0.7rem; color: #6b7280; text-transform: uppercase;
        margin-bottom: 0.2rem;
    }
    .map-entity-list { display: flex; flex-wrap: wrap; gap: 0.2rem; }
    .map-entity {
        background: #1e3a5f; padding: 0.1rem 0.4rem; border-radius: 3px;
        font-size: 0.65rem; color: #4a9eff;
    }
    .map-xref-row {
        display: flex; align-items: center; gap: 0.5rem;
        padding: 0.2rem 0; font-size: 0.75rem; border-bottom: 1px solid #2d3139;
    }
    .map-xref-key { color: #fff; min-width: 150px; }
    .map-xref-docs { color: #6b7280; }
    .map-summary-box {
        background: #0d1117; padding: 0.5rem; border-radius: 4px;
        font-size: 0.8rem; color: #9ca3af; border: 1px solid #30363d;
    }
    .map-chunk {
        background: #0d1117; padding: 0.3rem 0.5rem; border-radius: 3px;
        margin: 0.2rem 0; font-size: 0.7rem; color: #8b949e;
        border-left: 2px solid #30363d;
    }

    /* Batch Tester Styles */
    .batch-result {
        background: #1a1d24; border-radius: 6px; padding: 0.6rem;
        margin: 0.5rem 0; border: 1px solid #2d3139;
    }
    .batch-question {
        font-weight: 600; font-size: 0.85rem; color: #fff;
        padding-bottom: 0.4rem; border-bottom: 1px solid #2d3139;
        margin-bottom: 0.4rem;
    }
    .batch-answers { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
    .batch-answer {
        background: #161b22; border-radius: 4px; padding: 0.5rem;
        font-size: 0.75rem;
    }
    .batch-answer-map { border-left: 2px solid #10b981; }
    .batch-answer-sql { border-left: 2px solid #f59e0b; }
    .batch-answer-header {
        font-weight: 600; font-size: 0.7rem; color: #9ca3af;
        margin-bottom: 0.3rem; display: flex; justify-content: space-between;
    }
    .batch-answer-content { color: #d1d5db; line-height: 1.4; }
    .batch-meta { font-size: 0.65rem; color: #6b7280; margin-top: 0.3rem; }
    .batch-progress {
        background: #2d3139; border-radius: 4px; padding: 0.4rem 0.6rem;
        font-size: 0.8rem; color: #9ca3af; margin: 0.3rem 0;
    }
    .batch-summary {
        display: flex; gap: 1rem; background: #1a1d24;
        padding: 0.5rem; border-radius: 4px; margin: 0.5rem 0;
    }
    .batch-summary-item { text-align: center; }
    .batch-summary-value { font-size: 1rem; font-weight: 600; color: #4a9eff; }
    .batch-summary-label { font-size: 0.65rem; color: #6b7280; }

    /* OpenAI Tab Styles */
    .openai-header {
        background: linear-gradient(135deg, #10a37f 0%, #1a7f5a 100%);
        padding: 0.5rem 0.8rem; border-radius: 6px; margin-bottom: 0.5rem;
    }
    .openai-header-title { color: #fff; font-weight: 600; font-size: 0.9rem; }
    .openai-header-sub { color: rgba(255,255,255,0.8); font-size: 0.7rem; }
    .openai-file-card {
        background: #1a1d24; border-radius: 4px; padding: 0.4rem 0.6rem;
        margin: 0.2rem 0; border-left: 2px solid #10a37f; font-size: 0.8rem;
        display: flex; justify-content: space-between; align-items: center;
    }
    .openai-file-name { color: #fff; }
    .openai-file-meta { color: #6b7280; font-size: 0.7rem; }
    .openai-msg { padding: 0.5rem; border-radius: 6px; margin: 0.3rem 0; font-size: 0.85rem; }
    .openai-msg-user { background: #1e3a5f; border-left: 2px solid #4a9eff; }
    .openai-msg-assistant { background: #1a2e1a; border-left: 2px solid #10a37f; }
    .openai-citation {
        background: #0d1117; padding: 0.3rem 0.5rem; border-radius: 4px;
        font-size: 0.7rem; color: #8b949e; margin-top: 0.3rem;
        border: 1px solid #30363d;
    }
    .openai-status {
        background: #161b22; padding: 0.3rem 0.5rem; border-radius: 4px;
        font-size: 0.75rem; color: #10a37f; display: inline-block;
    }
    .openai-answer {
        color: #e5e7eb; line-height: 1.5; white-space: pre-wrap;
    }
    .openai-sources {
        background: #0d1117; padding: 0.5rem; border-radius: 4px;
        font-size: 0.75rem; color: #9ca3af; margin-top: 0.5rem;
        border: 1px solid #30363d;
    }
    .openai-source-item {
        color: #10a37f; font-family: monospace;
    }
</style>
"""
