"""
Streamlit UI for Intelligent RAG System.
Compact modern dark-themed interface with dual RAG modes.
"""
import streamlit as st
import httpx
import os

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="Intelligent RAG",
    page_icon="brain",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Compact dark theme CSS
st.markdown("""
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
</style>
""", unsafe_allow_html=True)


# Session state initialization
if "messages_map" not in st.session_state:
    st.session_state.messages_map = []
if "messages_agentic" not in st.session_state:
    st.session_state.messages_agentic = []
if "session_id_map" not in st.session_state:
    st.session_state.session_id_map = None
if "session_id_agentic" not in st.session_state:
    st.session_state.session_id_agentic = None
if "documents" not in st.session_state:
    st.session_state.documents = []
if "agentic_stats" not in st.session_state:
    st.session_state.agentic_stats = None
if "selected_doc_id" not in st.session_state:
    st.session_state.selected_doc_id = None
if "selected_doc_chunks" not in st.session_state:
    st.session_state.selected_doc_chunks = None
if "document_map" not in st.session_state:
    st.session_state.document_map = None
if "batch_results" not in st.session_state:
    st.session_state.batch_results = None
# OpenAI state
if "openai_api_key" not in st.session_state:
    # Use environment variable if available
    st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY") or None
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


def api_request(method: str, endpoint: str, **kwargs):
    """Make API request to backend."""
    try:
        with httpx.Client(timeout=180.0) as client:
            response = client.request(method, f"{BACKEND_URL}{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        return {"error": str(e)}


def load_documents():
    """Load documents from backend."""
    result = api_request("GET", "/api/documents/")
    if result and "error" not in result:
        st.session_state.documents = result.get("documents", [])


def load_agentic_stats():
    """Load agentic extraction stats."""
    result = api_request("GET", "/api/agentic/stats")
    if result and "error" not in result:
        st.session_state.agentic_stats = result


def load_document_chunks(doc_id: str):
    """Load chunks for a specific document."""
    result = api_request("GET", f"/api/documents/{doc_id}/chunks")
    if result and "error" not in result:
        st.session_state.selected_doc_chunks = result
        st.session_state.selected_doc_id = doc_id
    return result


def load_document_map():
    """Load the document map."""
    result = api_request("GET", "/api/documents/map/view")
    if result and "error" not in result:
        st.session_state.document_map = result
    return result


def query_map_rag(question: str) -> dict:
    """Query the Map RAG endpoint."""
    import time
    start = time.time()
    payload = {"query": question, "workspace_id": "default", "session_id": None}
    result = api_request("POST", "/api/chat/query", json=payload)
    elapsed = time.time() - start
    if result and "error" not in result:
        return {
            "answer": result.get("answer", ""),
            "confidence": result.get("confidence", 0),
            "citations": result.get("citations", []),
            "time": elapsed,
            "error": None
        }
    return {"answer": "", "confidence": 0, "citations": [], "time": elapsed, "error": result.get("error", "Unknown error")}


def query_sql_rag(question: str) -> dict:
    """Query the SQL RAG endpoint."""
    import time
    start = time.time()
    payload = {"query": question, "workspace_id": "default", "session_id": None}
    result = api_request("POST", "/api/agentic/query", json=payload)
    elapsed = time.time() - start
    if result and "error" not in result:
        return {
            "answer": result.get("answer", ""),
            "confidence": result.get("confidence", 0),
            "iterations": result.get("iterations", 0),
            "queries": result.get("queries_executed", []),
            "time": elapsed,
            "error": None
        }
    return {"answer": "", "confidence": 0, "iterations": 0, "queries": [], "time": elapsed, "error": result.get("error", "Unknown error")}


# === OpenAI Functions ===
def get_openai_client():
    """Get OpenAI client with current API key."""
    from openai import OpenAI
    if st.session_state.openai_api_key:
        return OpenAI(api_key=st.session_state.openai_api_key)
    return None


def openai_create_vector_store(name: str = "RAG_Comparison_Store"):
    """Create a vector store for file search."""
    client = get_openai_client()
    if not client:
        return None
    try:
        vector_store = client.beta.vector_stores.create(name=name)
        st.session_state.openai_vector_store_id = vector_store.id
        return vector_store
    except Exception as e:
        st.error(f"Failed to create vector store: {e}")
        return None


def openai_upload_file(file_bytes: bytes, filename: str):
    """Upload a file to OpenAI and add to vector store."""
    client = get_openai_client()
    if not client:
        return None

    try:
        # Create vector store if needed
        if not st.session_state.openai_vector_store_id:
            openai_create_vector_store()

        # Upload file
        file_obj = client.files.create(
            file=(filename, file_bytes),
            purpose="assistants"
        )

        # Add to vector store
        client.beta.vector_stores.files.create(
            vector_store_id=st.session_state.openai_vector_store_id,
            file_id=file_obj.id
        )

        file_info = {
            "id": file_obj.id,
            "filename": filename,
            "bytes": len(file_bytes),
            "status": "uploaded"
        }
        st.session_state.openai_files.append(file_info)
        return file_info
    except Exception as e:
        st.error(f"Failed to upload file: {e}")
        return None


def openai_create_assistant():
    """Create an assistant with file search capability."""
    client = get_openai_client()
    if not client or not st.session_state.openai_vector_store_id:
        return None

    try:
        assistant = client.beta.assistants.create(
            name="RAG Comparison Assistant",
            instructions="""You are a helpful assistant that answers questions based on the uploaded documents.
            Always cite your sources by referencing the specific documents you used.
            If you cannot find relevant information in the documents, say so clearly.""",
            model="gpt-4o-mini",
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [st.session_state.openai_vector_store_id]
                }
            }
        )
        st.session_state.openai_assistant_id = assistant.id
        return assistant
    except Exception as e:
        st.error(f"Failed to create assistant: {e}")
        return None


def openai_create_thread():
    """Create a new conversation thread."""
    client = get_openai_client()
    if not client:
        return None

    try:
        thread = client.beta.threads.create()
        st.session_state.openai_thread_id = thread.id
        return thread
    except Exception as e:
        st.error(f"Failed to create thread: {e}")
        return None


def openai_query(question: str) -> dict:
    """Query the OpenAI assistant with file search."""
    import time
    client = get_openai_client()
    if not client:
        return {"answer": "", "citations": [], "error": "No API key", "time": 0}

    # Create assistant and thread if needed
    if not st.session_state.openai_assistant_id:
        openai_create_assistant()
    if not st.session_state.openai_thread_id:
        openai_create_thread()

    if not st.session_state.openai_assistant_id or not st.session_state.openai_thread_id:
        return {"answer": "", "citations": [], "error": "Failed to initialize", "time": 0}

    try:
        start = time.time()

        # Add message to thread
        client.beta.threads.messages.create(
            thread_id=st.session_state.openai_thread_id,
            role="user",
            content=question
        )

        # Run the assistant
        run = client.beta.threads.runs.create_and_poll(
            thread_id=st.session_state.openai_thread_id,
            assistant_id=st.session_state.openai_assistant_id
        )

        elapsed = time.time() - start

        if run.status == "completed":
            # Get messages
            messages = client.beta.threads.messages.list(
                thread_id=st.session_state.openai_thread_id,
                order="desc",
                limit=1
            )

            answer = ""
            citations = []

            for msg in messages.data:
                if msg.role == "assistant":
                    for content in msg.content:
                        if content.type == "text":
                            answer = content.text.value
                            # Extract annotations/citations
                            if hasattr(content.text, 'annotations'):
                                for ann in content.text.annotations:
                                    if hasattr(ann, 'file_citation'):
                                        citations.append({
                                            "file_id": ann.file_citation.file_id if hasattr(ann.file_citation, 'file_id') else "unknown",
                                            "quote": ann.file_citation.quote if hasattr(ann.file_citation, 'quote') else ""
                                        })
                    break

            return {"answer": answer, "citations": citations, "error": None, "time": elapsed}
        else:
            return {"answer": "", "citations": [], "error": f"Run status: {run.status}", "time": elapsed}
    except Exception as e:
        return {"answer": "", "citations": [], "error": str(e), "time": 0}


def openai_cleanup():
    """Delete OpenAI resources."""
    client = get_openai_client()
    if not client:
        return

    try:
        # Delete assistant
        if st.session_state.openai_assistant_id:
            client.beta.assistants.delete(st.session_state.openai_assistant_id)
            st.session_state.openai_assistant_id = None

        # Delete files
        for f in st.session_state.openai_files:
            try:
                client.files.delete(f["id"])
            except:
                pass
        st.session_state.openai_files = []

        # Delete vector store
        if st.session_state.openai_vector_store_id:
            client.beta.vector_stores.delete(st.session_state.openai_vector_store_id)
            st.session_state.openai_vector_store_id = None

        # Clear thread and messages
        st.session_state.openai_thread_id = None
        st.session_state.openai_messages = []

    except Exception as e:
        st.error(f"Cleanup error: {e}")


def upload_document(file, extraction_mode="both"):
    """Upload single document to backend."""
    files = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
    result = api_request(
        "POST",
        f"/api/documents/upload?extraction_mode={extraction_mode}",
        files=files
    )
    return result


def delete_document(doc_id: str):
    """Delete document from backend."""
    result = api_request("DELETE", f"/api/documents/{doc_id}")
    if result and "error" not in result:
        load_documents()
        load_agentic_stats()
        return True
    return False


def send_message_map(query: str):
    """Send query to Document Map RAG."""
    payload = {"query": query, "workspace_id": "default", "session_id": st.session_state.session_id_map}
    result = api_request("POST", "/api/chat/query", json=payload)
    if result and "error" not in result:
        st.session_state.session_id_map = result.get("session_id")
        return result
    return None


def send_message_agentic(query: str):
    """Send query to Agentic SQL RAG."""
    payload = {"query": query, "workspace_id": "default", "session_id": st.session_state.session_id_agentic}
    result = api_request("POST", "/api/agentic/query", json=payload)
    if result and "error" not in result:
        st.session_state.session_id_agentic = result.get("session_id")
        return result
    return None


# Load documents on first run
if not st.session_state.documents:
    load_documents()
    load_agentic_stats()


# === HEADER ROW ===
col_title, col_stats, col_upload = st.columns([2, 3, 3])

with col_title:
    st.markdown("## RAG System")

with col_stats:
    docs = st.session_state.documents
    stats = st.session_state.agentic_stats or {}
    total_tokens = sum(d['token_count'] for d in docs) if docs else 0
    st.markdown(f"""
    <div class="stats-row">
        <div class="stat-item"><div class="stat-value">{len(docs)}</div><div class="stat-label">Docs</div></div>
        <div class="stat-item"><div class="stat-value">{total_tokens:,}</div><div class="stat-label">Tokens</div></div>
        <div class="stat-item"><div class="stat-value">{stats.get('claims', 0)}</div><div class="stat-label">Claims</div></div>
        <div class="stat-item"><div class="stat-value">{stats.get('entities', 0)}</div><div class="stat-label">Entities</div></div>
    </div>
    """, unsafe_allow_html=True)

with col_upload:
    with st.expander("Upload Documents", expanded=False):
        uploaded_files = st.file_uploader(
            "Drop files",
            type=["pdf", "png", "jpg", "jpeg", "webp", "md"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        if uploaded_files:
            col_mode, col_btn = st.columns([2, 1])
            with col_mode:
                extraction_mode = st.selectbox(
                    "Mode", ["both", "map_only", "sql_only"],
                    label_visibility="collapsed"
                )
            with col_btn:
                if st.button("Process All", use_container_width=True):
                    progress = st.empty()
                    results = []
                    for i, file in enumerate(uploaded_files):
                        progress.markdown(f"Processing {i+1}/{len(uploaded_files)}: {file.name}...")
                        result = upload_document(file, extraction_mode)
                        results.append((file.name, result))

                    # Show results
                    progress.empty()
                    success = sum(1 for _, r in results if r and "error" not in r)
                    failed = len(results) - success

                    result_html = f"<div style='font-size:0.8rem;'>"
                    for name, r in results:
                        if r and "error" not in r:
                            result_html += f"<div class='upload-item upload-ok'>✓ {name}</div>"
                        else:
                            err = r.get('error', 'Unknown error') if r else 'Failed'
                            result_html += f"<div class='upload-item upload-err'>✗ {name}: {err}</div>"
                    result_html += "</div>"
                    st.markdown(result_html, unsafe_allow_html=True)

                    load_documents()
                    load_agentic_stats()

st.markdown("<hr style='margin:0.3rem 0;'>", unsafe_allow_html=True)

# === MAIN LAYOUT: Sidebar + Content ===
col_docs, col_main = st.columns([1, 4])

# Document List (Left Panel)
with col_docs:
    st.markdown("#### Documents")
    col_ref, col_clr = st.columns(2)
    with col_ref:
        if st.button("↻", help="Refresh", use_container_width=True):
            load_documents()
            load_agentic_stats()
            st.rerun()
    with col_clr:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages_map = []
            st.session_state.messages_agentic = []
            st.session_state.session_id_map = None
            st.session_state.session_id_agentic = None
            st.rerun()

    if st.session_state.documents:
        for doc in st.session_state.documents:
            cols = st.columns([5, 1])
            with cols[0]:
                name = doc['filename']
                short_name = name[:20] + ('...' if len(name) > 20 else '')
                chunks_info = f"{doc['chunk_count']}c" if doc['chunk_count'] > 0 else "full"
                st.markdown(f"""
                <div class="doc-row">
                    <span class="doc-name" title="{name}">{short_name}</span>
                    <span class="doc-meta">{doc['token_count']:,}t | {chunks_info}</span>
                </div>
                """, unsafe_allow_html=True)
            with cols[1]:
                if st.button("×", key=f"del_{doc['id']}", help="Delete"):
                    delete_document(doc['id'])
                    st.rerun()
    else:
        st.markdown("<div style='color:#6b7280;font-size:0.8rem;'>No documents</div>", unsafe_allow_html=True)

# Main Content (Right Panel)
with col_main:
    tab_map, tab_agentic, tab_browser, tab_docmap, tab_batch, tab_openai = st.tabs(["Map RAG", "SQL RAG", "Browser", "Doc Map", "Batch Test", "OpenAI"])

    # === Document Map RAG Tab ===
    with tab_map:
        # Chat container with fixed height
        chat_container = st.container()

        with chat_container:
            if st.session_state.messages_map:
                for msg in st.session_state.messages_map:
                    if msg["role"] == "user":
                        st.markdown(f"""
                        <div class="msg msg-user">
                            <div class="msg-header">You</div>
                            {msg["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        conf = msg.get("confidence", 0.5)
                        conf_class = "conf-high" if conf > 0.7 else "conf-med" if conf > 0.4 else "conf-low"
                        citations = ""
                        if msg.get("citations"):
                            citations = " ".join(f"<span class='badge'>{c.get('doc_id', '?')[:12]}</span>" for c in msg["citations"])
                        st.markdown(f"""
                        <div class="msg msg-assistant">
                            <div class="msg-header">Assistant <span class="{conf_class}">({conf:.0%})</span></div>
                            {msg["content"]}
                            <div style="margin-top:0.3rem;">{citations}</div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="text-align:center;color:#6b7280;padding:2rem;font-size:0.85rem;">
                    <b>Document Map RAG</b><br>
                    One-shot retrieval using document map. Fast (1-2 LLM calls).
                </div>
                """, unsafe_allow_html=True)

        query_map = st.chat_input("Ask question (Map RAG)...", key="input_map")
        if query_map:
            st.session_state.messages_map.append({"role": "user", "content": query_map})
            with st.spinner("Retrieving..."):
                response = send_message_map(query_map)
                if response:
                    st.session_state.messages_map.append({
                        "role": "assistant",
                        "content": response["answer"],
                        "citations": response.get("citations", []),
                        "confidence": response.get("confidence", 0.5),
                    })
            st.rerun()

    # === Agentic SQL RAG Tab ===
    with tab_agentic:
        chat_container = st.container()

        with chat_container:
            if st.session_state.messages_agentic:
                for msg in st.session_state.messages_agentic:
                    if msg["role"] == "user":
                        st.markdown(f"""
                        <div class="msg msg-user">
                            <div class="msg-header">You</div>
                            {msg["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        conf = msg.get("confidence", 0.5)
                        conf_class = "conf-high" if conf > 0.7 else "conf-med" if conf > 0.4 else "conf-low"
                        st.markdown(f"""
                        <div class="msg msg-agentic">
                            <div class="msg-header">Agentic <span class="{conf_class}">({conf:.0%})</span> | {msg.get('iterations', 0)} iters</div>
                            {msg["content"]}
                        </div>
                        """, unsafe_allow_html=True)

                        # Compact reasoning/queries expander
                        if msg.get("queries_executed") or msg.get("reasoning_steps"):
                            with st.expander("Details", expanded=False):
                                if msg.get("reasoning_steps"):
                                    for step in msg["reasoning_steps"]:
                                        st.markdown(f"<div class='info-box'>{step}</div>", unsafe_allow_html=True)
                                if msg.get("queries_executed"):
                                    for q in msg["queries_executed"]:
                                        st.code(q, language="sql")
                                if msg.get("sources"):
                                    st.markdown("Sources: " + ", ".join(f"`{s}`" for s in msg["sources"]))
            else:
                st.markdown("""
                <div style="text-align:center;color:#6b7280;padding:2rem;font-size:0.85rem;">
                    <b>Agentic SQL RAG</b><br>
                    Iterative SQL queries with LLM reasoning. Best for precise facts.
                </div>
                """, unsafe_allow_html=True)

        query_agentic = st.chat_input("Ask question (SQL RAG)...", key="input_agentic")
        if query_agentic:
            st.session_state.messages_agentic.append({"role": "user", "content": query_agentic})
            with st.spinner("Querying..."):
                response = send_message_agentic(query_agentic)
                if response:
                    st.session_state.messages_agentic.append({
                        "role": "assistant",
                        "content": response["answer"],
                        "confidence": response.get("confidence", 0.5),
                        "queries_executed": response.get("queries_executed", []),
                        "reasoning_steps": response.get("reasoning_steps", []),
                        "sources": response.get("sources", []),
                        "iterations": response.get("iterations", 0)
                    })
            st.rerun()

    # === Document Browser Tab ===
    with tab_browser:
        if not st.session_state.documents:
            st.info("No documents. Upload some first.")
        else:
            col_sel, col_load = st.columns([4, 1])
            with col_sel:
                doc_options = {d['id']: f"{d['filename']} ({d['token_count']:,}t)" for d in st.session_state.documents}
                selected_id = st.selectbox("Document", list(doc_options.keys()), format_func=lambda x: doc_options[x], label_visibility="collapsed")
            with col_load:
                if st.button("Load", use_container_width=True):
                    load_document_chunks(selected_id)

            if st.session_state.selected_doc_chunks and st.session_state.selected_doc_id == selected_id:
                data = st.session_state.selected_doc_chunks

                col_info, col_chunk_sel = st.columns([2, 3])
                with col_info:
                    st.markdown(f"**{data['filename']}** - {data['total']} chunk(s)")

                with col_chunk_sel:
                    if data['chunks']:
                        chunk_opts = {i: f"#{i+1}: {c['section'][:30]} ({c['position']})" for i, c in enumerate(data['chunks'])}
                        idx = st.selectbox("Chunk", list(chunk_opts.keys()), format_func=lambda x: chunk_opts[x], label_visibility="collapsed")

                        if idx is not None:
                            chunk = data['chunks'][idx]

                            # Compact metadata grid
                            st.markdown(f"""
                            <div class="chunk-meta">
                                <div class="chunk-meta-item"><div class="chunk-meta-label">ID</div><div class="chunk-meta-value">{chunk['chunk_id']}</div></div>
                                <div class="chunk-meta-item"><div class="chunk-meta-label">Position</div><div class="chunk-meta-value">{chunk['position']}</div></div>
                                <div class="chunk-meta-item"><div class="chunk-meta-label">Tokens</div><div class="chunk-meta-value">{chunk['token_count']:,}</div></div>
                                <div class="chunk-meta-item"><div class="chunk-meta-label">Section</div><div class="chunk-meta-value">{chunk['section'][:25]}</div></div>
                            </div>
                            """, unsafe_allow_html=True)

                            if chunk.get('context'):
                                st.markdown(f"<div class='info-box'><b>Context:</b> {chunk['context']}</div>", unsafe_allow_html=True)

                            # Content preview
                            content = chunk['content']
                            max_len = min(3000, len(content))
                            preview_len = st.slider("Preview chars", 500, max_len, min(1500, max_len), 100, label_visibility="collapsed")
                            preview = content[:preview_len] + ("\n...[truncated]" if len(content) > preview_len else "")
                            st.markdown(f"<div class='code-preview'>{preview}</div>", unsafe_allow_html=True)
                            st.caption(f"{min(preview_len, len(content)):,} / {len(content):,} chars")
            else:
                st.markdown("<div style='color:#6b7280;text-align:center;padding:1rem;'>Select document and click Load</div>", unsafe_allow_html=True)

    # === Document Map Viewer Tab ===
    with tab_docmap:
        col_load_map, col_info_map = st.columns([1, 4])
        with col_load_map:
            if st.button("Load Map", use_container_width=True):
                load_document_map()

        doc_map = st.session_state.document_map

        if doc_map:
            with col_info_map:
                st.markdown(f"<span style='color:#6b7280;font-size:0.75rem;'>Last updated: {doc_map.get('last_updated', 'N/A')}</span>", unsafe_allow_html=True)

            # Corpus Summary
            if doc_map.get('corpus_summary'):
                st.markdown(f"""
                <div class="map-section">
                    <div class="map-section-title">Corpus Summary</div>
                    <div class="map-summary-box">{doc_map['corpus_summary']}</div>
                </div>
                """, unsafe_allow_html=True)

            # Two-column layout for documents and cross-references
            col_docs_map, col_xrefs = st.columns([3, 2])

            with col_docs_map:
                st.markdown(f"""
                <div class="map-section">
                    <div class="map-section-title">Documents ({len(doc_map.get('documents', []))})</div>
                </div>
                """, unsafe_allow_html=True)

                for doc in doc_map.get('documents', []):
                    # Build topics HTML
                    topics_html = ""
                    if doc.get('topics'):
                        topics_html = '<div class="map-topics">' + ''.join(
                            f'<span class="map-topic">{t}</span>' for t in doc['topics'][:8]
                        ) + '</div>'

                    # Build entities HTML
                    entities_html = ""
                    if doc.get('entities'):
                        for etype, elist in doc['entities'].items():
                            if elist:
                                entities_html += f'<div class="map-entity-section">'
                                entities_html += f'<div class="map-entity-type">{etype}</div>'
                                entities_html += '<div class="map-entity-list">'
                                entities_html += ''.join(f'<span class="map-entity">{e}</span>' for e in elist[:6])
                                entities_html += '</div></div>'

                    # Build chunks HTML if present
                    chunks_html = ""
                    if doc.get('chunks'):
                        chunks_html = '<div style="margin-top:0.3rem;">'
                        for chunk in doc['chunks'][:3]:
                            chunks_html += f'<div class="map-chunk">{chunk.get("section", "?")} - {chunk.get("context", "")[:60]}...</div>'
                        if len(doc['chunks']) > 3:
                            chunks_html += f'<div class="map-chunk">... +{len(doc["chunks"]) - 3} more chunks</div>'
                        chunks_html += '</div>'

                    st.markdown(f"""
                    <div class="map-doc-card">
                        <div class="map-doc-title">{doc.get('filename', 'Unknown')}</div>
                        <div class="map-doc-essence">{doc.get('essence', '')[:200]}{'...' if len(doc.get('essence', '')) > 200 else ''}</div>
                        <div class="map-doc-meta">Type: {doc.get('type', 'other')} | Size: {doc.get('size_class', '?')} | ID: {doc.get('id', '?')[:12]}</div>
                        {topics_html}
                        {entities_html}
                        {chunks_html}
                    </div>
                    """, unsafe_allow_html=True)

            with col_xrefs:
                xrefs = doc_map.get('cross_references', {})

                # By Topic
                by_topic = xrefs.get('by_topic', {})
                if by_topic:
                    st.markdown(f"""
                    <div class="map-section">
                        <div class="map-section-title">Cross-Refs by Topic ({len(by_topic)})</div>
                    </div>
                    """, unsafe_allow_html=True)

                    for topic, doc_ids in list(by_topic.items())[:10]:
                        docs_str = ', '.join(d[:8] for d in doc_ids)
                        st.markdown(f"""
                        <div class="map-xref-row">
                            <span class="map-xref-key">{topic[:25]}</span>
                            <span class="map-xref-docs">{docs_str}</span>
                        </div>
                        """, unsafe_allow_html=True)

                # By Entity
                by_entity = xrefs.get('by_entity', {})
                if by_entity:
                    st.markdown(f"""
                    <div class="map-section" style="margin-top:0.5rem;">
                        <div class="map-section-title">Cross-Refs by Entity ({len(by_entity)})</div>
                    </div>
                    """, unsafe_allow_html=True)

                    for entity, doc_ids in list(by_entity.items())[:10]:
                        docs_str = ', '.join(d[:8] for d in doc_ids)
                        st.markdown(f"""
                        <div class="map-xref-row">
                            <span class="map-xref-key">{entity[:25]}</span>
                            <span class="map-xref-docs">{docs_str}</span>
                        </div>
                        """, unsafe_allow_html=True)

                if not by_topic and not by_entity:
                    st.markdown("<div style='color:#6b7280;font-size:0.8rem;'>No cross-references yet</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#6b7280;text-align:center;padding:2rem;'>Click 'Load Map' to view the document map structure</div>", unsafe_allow_html=True)

    # === Batch Tester Tab ===
    with tab_batch:
        import json

        st.markdown("**Compare both RAG modes with batch questions**")

        col_upload_batch, col_sample = st.columns([3, 2])

        with col_upload_batch:
            batch_file = st.file_uploader(
                "Upload JSON file with questions",
                type=["json"],
                help='Format: {"questions": ["Q1", "Q2", ...]} or ["Q1", "Q2", ...]',
                label_visibility="collapsed"
            )

        with col_sample:
            with st.expander("Sample Format", expanded=False):
                st.code('''{"questions": [
  "What is the main topic?",
  "Who are the key people?",
  "What metrics are mentioned?"
]}''', language="json")

        # Manual question input as alternative
        manual_questions = st.text_area(
            "Or enter questions (one per line)",
            height=80,
            placeholder="What is the document about?\nWhat are the key findings?",
            label_visibility="collapsed"
        )

        col_run, col_clear = st.columns([1, 1])
        with col_run:
            run_batch = st.button("Run Batch Test", use_container_width=True, type="primary")
        with col_clear:
            if st.button("Clear Results", use_container_width=True):
                st.session_state.batch_results = None
                st.rerun()

        if run_batch:
            questions = []

            # Parse questions from file or manual input
            if batch_file:
                try:
                    content = batch_file.read().decode('utf-8')
                    data = json.loads(content)
                    if isinstance(data, list):
                        questions = data
                    elif isinstance(data, dict) and 'questions' in data:
                        questions = data['questions']
                    else:
                        st.error("Invalid format. Expected list or {questions: [...]}")
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {e}")
            elif manual_questions.strip():
                questions = [q.strip() for q in manual_questions.strip().split('\n') if q.strip()]

            if questions:
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, question in enumerate(questions):
                    status_text.markdown(f"<div class='batch-progress'>Processing {i+1}/{len(questions)}: {question[:50]}...</div>", unsafe_allow_html=True)
                    progress_bar.progress((i + 1) / len(questions))

                    # Query both RAG systems
                    map_result = query_map_rag(question)
                    sql_result = query_sql_rag(question)

                    results.append({
                        "question": question,
                        "map_rag": map_result,
                        "sql_rag": sql_result
                    })

                progress_bar.empty()
                status_text.empty()

                st.session_state.batch_results = results
                st.rerun()
            else:
                st.warning("No questions provided. Upload a JSON file or enter questions manually.")

        # Display results
        if st.session_state.batch_results:
            results = st.session_state.batch_results

            # Summary stats
            total = len(results)
            avg_map_time = sum(r['map_rag']['time'] for r in results) / total if total else 0
            avg_sql_time = sum(r['sql_rag']['time'] for r in results) / total if total else 0
            avg_map_conf = sum(r['map_rag']['confidence'] for r in results) / total if total else 0
            avg_sql_conf = sum(r['sql_rag']['confidence'] for r in results) / total if total else 0

            st.markdown(f"""
            <div class="batch-summary">
                <div class="batch-summary-item"><div class="batch-summary-value">{total}</div><div class="batch-summary-label">Questions</div></div>
                <div class="batch-summary-item"><div class="batch-summary-value">{avg_map_time:.1f}s</div><div class="batch-summary-label">Avg Map Time</div></div>
                <div class="batch-summary-item"><div class="batch-summary-value">{avg_sql_time:.1f}s</div><div class="batch-summary-label">Avg SQL Time</div></div>
                <div class="batch-summary-item"><div class="batch-summary-value">{avg_map_conf:.0%}</div><div class="batch-summary-label">Avg Map Conf</div></div>
                <div class="batch-summary-item"><div class="batch-summary-value">{avg_sql_conf:.0%}</div><div class="batch-summary-label">Avg SQL Conf</div></div>
            </div>
            """, unsafe_allow_html=True)

            # Export button
            export_data = json.dumps(results, indent=2, default=str)
            st.download_button(
                "Export Results (JSON)",
                data=export_data,
                file_name="batch_results.json",
                mime="application/json"
            )

            st.markdown("---")

            # Individual results
            for i, result in enumerate(results):
                q = result['question']
                map_r = result['map_rag']
                sql_r = result['sql_rag']

                map_conf_class = "conf-high" if map_r['confidence'] > 0.7 else "conf-med" if map_r['confidence'] > 0.4 else "conf-low"
                sql_conf_class = "conf-high" if sql_r['confidence'] > 0.7 else "conf-med" if sql_r['confidence'] > 0.4 else "conf-low"

                # Truncate answers for display
                map_answer = map_r['answer'][:500] + ('...' if len(map_r['answer']) > 500 else '') if map_r['answer'] else '(Error or empty)'
                sql_answer = sql_r['answer'][:500] + ('...' if len(sql_r['answer']) > 500 else '') if sql_r['answer'] else '(Error or empty)'

                st.markdown(f"""
                <div class="batch-result">
                    <div class="batch-question">Q{i+1}: {q}</div>
                    <div class="batch-answers">
                        <div class="batch-answer batch-answer-map">
                            <div class="batch-answer-header">
                                <span>Map RAG</span>
                                <span class="{map_conf_class}">{map_r['confidence']:.0%} | {map_r['time']:.1f}s</span>
                            </div>
                            <div class="batch-answer-content">{map_answer}</div>
                            <div class="batch-meta">Citations: {len(map_r.get('citations', []))}</div>
                        </div>
                        <div class="batch-answer batch-answer-sql">
                            <div class="batch-answer-header">
                                <span>SQL RAG</span>
                                <span class="{sql_conf_class}">{sql_r['confidence']:.0%} | {sql_r['time']:.1f}s</span>
                            </div>
                            <div class="batch-answer-content">{sql_answer}</div>
                            <div class="batch-meta">Iterations: {sql_r.get('iterations', 0)} | Queries: {len(sql_r.get('queries', []))}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Expandable details
                with st.expander(f"Details Q{i+1}", expanded=False):
                    col_map_detail, col_sql_detail = st.columns(2)
                    with col_map_detail:
                        st.markdown("**Full Map RAG Answer:**")
                        st.markdown(f"<div class='code-preview'>{map_r['answer']}</div>", unsafe_allow_html=True)
                        if map_r.get('citations'):
                            st.markdown("**Citations:**")
                            for c in map_r['citations']:
                                st.markdown(f"- `{c.get('doc_id', '?')}`: {c.get('relevance', 'N/A')}")
                    with col_sql_detail:
                        st.markdown("**Full SQL RAG Answer:**")
                        st.markdown(f"<div class='code-preview'>{sql_r['answer']}</div>", unsafe_allow_html=True)
                        if sql_r.get('queries'):
                            st.markdown("**SQL Queries:**")
                            for q in sql_r['queries']:
                                st.code(q, language="sql")
        else:
            st.markdown("""
            <div style="text-align:center;color:#6b7280;padding:2rem;font-size:0.85rem;">
                <b>Batch Tester</b><br>
                Upload a JSON file with questions or enter them manually.<br>
                Both RAG modes will be queried for each question to compare results.
            </div>
            """, unsafe_allow_html=True)

    # === OpenAI File Search Tab ===
    with tab_openai:
        st.markdown("""
        <div class="openai-header">
            <div class="openai-header-title">OpenAI File Search</div>
            <div class="openai-header-sub">Compare against OpenAI's cloud-based RAG solution</div>
        </div>
        """, unsafe_allow_html=True)

        # API Key configuration
        env_key = os.getenv("OPENAI_API_KEY")
        if env_key:
            # Key from environment - show status
            st.markdown(f"<div class='openai-status'>API Key: from environment (sk-...{env_key[-4:]})</div>", unsafe_allow_html=True)
        else:
            # No env key - show input field
            api_key_input = st.text_input(
                "OpenAI API Key",
                type="password",
                value=st.session_state.openai_api_key or "",
                placeholder="sk-...",
                label_visibility="collapsed"
            )
            if api_key_input and api_key_input != st.session_state.openai_api_key:
                st.session_state.openai_api_key = api_key_input

        # Status display
        if st.session_state.openai_api_key:
            status_parts = []
            if st.session_state.openai_vector_store_id:
                status_parts.append(f"VS: {st.session_state.openai_vector_store_id[:8]}...")
            if st.session_state.openai_files:
                status_parts.append(f"Files: {len(st.session_state.openai_files)}")
            if st.session_state.openai_assistant_id:
                status_parts.append("Assistant: Ready")
            if status_parts:
                st.markdown(f"<div class='openai-status'>{' | '.join(status_parts)}</div>", unsafe_allow_html=True)

        if st.session_state.openai_api_key:
            # Files section in expander
            with st.expander("Files & Upload", expanded=not st.session_state.openai_files):
                openai_files = st.file_uploader(
                    "Upload to OpenAI",
                    type=["pdf", "txt", "md", "docx"],
                    accept_multiple_files=True,
                    key="openai_uploader",
                    label_visibility="collapsed"
                )

                if openai_files:
                    if st.button("Upload to OpenAI", use_container_width=True):
                        progress = st.empty()
                        for i, f in enumerate(openai_files):
                            progress.markdown(f"Uploading {i+1}/{len(openai_files)}: {f.name}...")
                            result = openai_upload_file(f.getvalue(), f.name)
                            if result:
                                st.success(f"Uploaded: {f.name}")
                        progress.empty()
                        st.rerun()

                # List uploaded files
                if st.session_state.openai_files:
                    st.markdown("**Uploaded Files:**")
                    files_html = ""
                    for f in st.session_state.openai_files:
                        files_html += f"""<div class="openai-file-card">
                            <span class="openai-file-name">{f['filename'][:30]}</span>
                            <span class="openai-file-meta">{f['bytes'] // 1024}KB</span>
                        </div>"""
                    st.markdown(files_html, unsafe_allow_html=True)

                    if st.button("Clear Chat", key="openai_clear_chat", use_container_width=True):
                        st.session_state.openai_messages = []
                        st.session_state.openai_thread_id = None
                        st.rerun()
                    if st.button("Delete All Files", key="openai_cleanup", use_container_width=True):
                        with st.spinner("Cleaning up..."):
                            openai_cleanup()
                        st.success("Cleaned up")
                        st.rerun()

            # Chat section
            chat_container = st.container()
            with chat_container:
                if st.session_state.openai_messages:
                    for msg in st.session_state.openai_messages:
                        if msg["role"] == "user":
                            st.markdown(f"""
                            <div class="openai-msg openai-msg-user">
                                <div class="msg-header">You</div>
                                {msg["content"]}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            answer = msg.get("content", "")
                            citations_html = ""
                            if msg.get("citations"):
                                citations_html = "<div class='openai-citation'><b>Citations:</b> "
                                for c in msg["citations"][:3]:
                                    quote = c.get("quote", "")[:100]
                                    citations_html += f"<br>- {quote}..."
                                citations_html += "</div>"

                            st.markdown(f"""
                            <div class="openai-msg openai-msg-assistant">
                                <div class="msg-header">OpenAI <span style="color:#6b7280;">({msg.get('time', 0):.1f}s)</span></div>
                                {answer}
                                {citations_html}
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    if st.session_state.openai_files:
                        st.markdown("""
                        <div style="text-align:center;color:#6b7280;padding:2rem;font-size:0.85rem;">
                            Files uploaded. Ask a question to search.
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="text-align:center;color:#6b7280;padding:2rem;font-size:0.85rem;">
                            Upload files in the expander above, then ask questions.
                        </div>
                        """, unsafe_allow_html=True)

            # Chat input
            if st.session_state.openai_files:
                query_openai = st.chat_input("Ask OpenAI...", key="openai_input")
                if query_openai:
                    st.session_state.openai_messages.append({"role": "user", "content": query_openai})
                    with st.spinner("Querying OpenAI..."):
                        result = openai_query(query_openai)
                        st.session_state.openai_messages.append({
                            "role": "assistant",
                            "content": result["answer"],
                            "citations": result.get("citations", []),
                            "time": result.get("time", 0),
                            "error": result.get("error")
                        })
                    st.rerun()
        else:
            st.markdown("""
            <div style="text-align:center;color:#6b7280;padding:3rem;font-size:0.85rem;">
                <b>OpenAI File Search</b><br><br>
                Set OPENAI_API_KEY in .env or enter your API key above.<br>
                This module uses OpenAI's Assistants API with file_search tool.<br><br>
                <b>Features:</b><br>
                - Upload files directly to OpenAI<br>
                - Automatic vector store creation<br>
                - File search with GPT-4o-mini<br>
                - Separate from local RAG for comparison
            </div>
            """, unsafe_allow_html=True)
