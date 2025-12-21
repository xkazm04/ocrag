"""Session state initialization and management."""
import streamlit as st
from config import OPENAI_API_KEY


def init_session_state():
    """Initialize all session state variables."""
    # Chat messages
    if "messages_map" not in st.session_state:
        st.session_state.messages_map = []
    if "messages_agentic" not in st.session_state:
        st.session_state.messages_agentic = []

    # Session IDs
    if "session_id_map" not in st.session_state:
        st.session_state.session_id_map = None
    if "session_id_agentic" not in st.session_state:
        st.session_state.session_id_agentic = None

    # Documents
    if "documents" not in st.session_state:
        st.session_state.documents = []
    if "agentic_stats" not in st.session_state:
        st.session_state.agentic_stats = None

    # Document browser
    if "selected_doc_id" not in st.session_state:
        st.session_state.selected_doc_id = None
    if "selected_doc_chunks" not in st.session_state:
        st.session_state.selected_doc_chunks = None

    # Document map
    if "document_map" not in st.session_state:
        st.session_state.document_map = None

    # Batch testing
    if "batch_results" not in st.session_state:
        st.session_state.batch_results = None

    # OpenAI integration
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = OPENAI_API_KEY
    if "openai_files" not in st.session_state:
        st.session_state.openai_files = []
    if "openai_vector_store_id" not in st.session_state:
        st.session_state.openai_vector_store_id = None
    if "openai_assistant_id" not in st.session_state:
        st.session_state.openai_assistant_id = None
    if "openai_thread_id" not in st.session_state:
        st.session_state.openai_thread_id = None
    if "openai_messages" not in st.session_state:
        st.session_state.openai_messages = []
    if "openai_initialized" not in st.session_state:
        st.session_state.openai_initialized = False


def clear_chat_messages():
    """Clear all chat messages and reset sessions."""
    st.session_state.messages_map = []
    st.session_state.messages_agentic = []
    st.session_state.session_id_map = None
    st.session_state.session_id_agentic = None


def clear_batch_results():
    """Clear batch test results."""
    st.session_state.batch_results = None


def clear_openai_chat():
    """Clear OpenAI chat messages."""
    st.session_state.openai_messages = []
    st.session_state.openai_thread_id = None
