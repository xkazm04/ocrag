"""API request utilities for backend communication."""
import time
import httpx
import streamlit as st
from config import BACKEND_URL, API_TIMEOUT


def api_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make API request to backend."""
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
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


def load_document_chunks(doc_id: str) -> dict:
    """Load chunks for a specific document."""
    result = api_request("GET", f"/api/documents/{doc_id}/chunks")
    if result and "error" not in result:
        st.session_state.selected_doc_chunks = result
        st.session_state.selected_doc_id = doc_id
    return result


def load_document_map() -> dict:
    """Load the document map."""
    result = api_request("GET", "/api/documents/map/view")
    if result and "error" not in result:
        st.session_state.document_map = result
    return result


def upload_document(file, extraction_mode: str = "both") -> dict:
    """Upload single document to backend."""
    files = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
    return api_request(
        "POST",
        f"/api/documents/upload?extraction_mode={extraction_mode}",
        files=files
    )


def delete_document(doc_id: str) -> bool:
    """Delete document from backend."""
    result = api_request("DELETE", f"/api/documents/{doc_id}")
    if result and "error" not in result:
        load_documents()
        load_agentic_stats()
        return True
    return False


def send_message_map(query: str) -> dict:
    """Send query to Document Map RAG."""
    payload = {
        "query": query,
        "workspace_id": "default",
        "session_id": st.session_state.session_id_map
    }
    result = api_request("POST", "/api/chat/query", json=payload)
    if result and "error" not in result:
        st.session_state.session_id_map = result.get("session_id")
        return result
    return None


def send_message_agentic(query: str) -> dict:
    """Send query to Agentic SQL RAG."""
    payload = {
        "query": query,
        "workspace_id": "default",
        "session_id": st.session_state.session_id_agentic
    }
    result = api_request("POST", "/api/agentic/query", json=payload)
    if result and "error" not in result:
        st.session_state.session_id_agentic = result.get("session_id")
        return result
    return None


def query_map_rag(question: str) -> dict:
    """Query the Map RAG endpoint for batch testing."""
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
    return {
        "answer": "",
        "confidence": 0,
        "citations": [],
        "time": elapsed,
        "error": result.get("error", "Unknown error")
    }


def query_sql_rag(question: str) -> dict:
    """Query the SQL RAG endpoint for batch testing."""
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
    return {
        "answer": "",
        "confidence": 0,
        "iterations": 0,
        "queries": [],
        "time": elapsed,
        "error": result.get("error", "Unknown error")
    }
