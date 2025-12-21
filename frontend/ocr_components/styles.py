"""OCR Benchmark page styles."""
import streamlit as st


def apply_ocr_styles():
    """Apply custom CSS for OCR Benchmark page."""
    st.markdown("""
    <style>
    /* OCR Page Header */
    .ocr-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .ocr-header-title {
        color: white;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
    }
    .ocr-header-sub {
        color: #94a3b8;
        font-size: 0.85rem;
        margin-top: 0.25rem;
    }

    /* Engine Cards */
    .engine-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    .engine-card.available {
        border-left: 3px solid #22c55e;
    }
    .engine-card.unavailable {
        border-left: 3px solid #ef4444;
        opacity: 0.6;
    }
    .engine-name {
        color: #f1f5f9;
        font-weight: 600;
        font-size: 1rem;
    }
    .engine-meta {
        color: #94a3b8;
        font-size: 0.75rem;
        margin-top: 0.25rem;
    }

    /* Result Cards */
    .result-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #1e293b;
    }
    .result-engine {
        color: #60a5fa;
        font-weight: 600;
        font-size: 0.95rem;
    }
    .result-stats {
        display: flex;
        gap: 1rem;
        color: #94a3b8;
        font-size: 0.75rem;
    }
    .result-text {
        background: #1e293b;
        border-radius: 4px;
        padding: 0.75rem;
        font-family: monospace;
        font-size: 0.8rem;
        color: #e2e8f0;
        max-height: 300px;
        overflow-y: auto;
        white-space: pre-wrap;
    }

    /* Score Badge */
    .score-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .score-high { background: #166534; color: #86efac; }
    .score-medium { background: #854d0e; color: #fde047; }
    .score-low { background: #991b1b; color: #fca5a5; }

    /* Category Tabs */
    .category-label {
        color: #94a3b8;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    /* Error State */
    .error-msg {
        background: #450a0a;
        border: 1px solid #991b1b;
        color: #fca5a5;
        padding: 0.75rem;
        border-radius: 4px;
        font-size: 0.85rem;
    }

    /* Processing Indicator */
    .processing {
        color: #60a5fa;
        font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)
