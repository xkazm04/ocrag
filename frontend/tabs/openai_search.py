"""OpenAI File Search tab for comparison with local RAG."""
import os
import re
import time
import streamlit as st
from state import clear_openai_chat


# Model configuration - easily changeable
# Options: "gpt-4o-mini", "gpt-4.1-mini-2025-04-14", "gpt-4.1-2025-04-14", "gpt-4o"
OPENAI_MODEL = "gpt-5-mini"

# QA System Prompt for the Assistant
QA_SYSTEM_PROMPT = """You are a knowledgeable assistant that answers questions based ONLY on the provided documents.

INSTRUCTIONS:
1. Answer the question using ONLY information found in the uploaded documents
2. Be concise and direct in your response
3. If the answer is not found in the documents, clearly state: "I could not find this information in the provided documents."
4. When citing information, the system will automatically add reference numbers - do not add your own citation markers
5. Structure your answer clearly with paragraphs if needed
6. Use bullet points for lists when appropriate
7. Always respond in the same language as the question

IMPORTANT: Base your answer strictly on the document content. Do not use external knowledge."""


def render_openai_tab():
    """Render the OpenAI file search interface."""
    _render_header()
    _render_api_key_section()

    if st.session_state.openai_api_key:
        # Load existing resources on first render
        if not st.session_state.get("openai_initialized"):
            with st.spinner("Loading existing files from OpenAI..."):
                _load_existing_resources()
            st.session_state.openai_initialized = True
        _render_main_interface()
    else:
        _render_no_key_message()


def _render_header():
    """Render the OpenAI tab header."""
    st.markdown(f"""
    <div class="openai-header">
        <div class="openai-header-title">OpenAI File Search</div>
        <div class="openai-header-sub">Model: {OPENAI_MODEL} | Cloud-based RAG comparison</div>
    </div>
    """, unsafe_allow_html=True)


def _render_api_key_section():
    """Render API key configuration."""
    env_key = os.getenv("OPENAI_API_KEY")

    if env_key:
        st.markdown(
            f"<div class='openai-status'>"
            f"API Key: from environment (sk-...{env_key[-4:]})</div>",
            unsafe_allow_html=True
        )
    else:
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=st.session_state.openai_api_key or "",
            placeholder="sk-...",
            label_visibility="collapsed"
        )
        if api_key and api_key != st.session_state.openai_api_key:
            st.session_state.openai_api_key = api_key
            st.session_state.openai_initialized = False
            st.rerun()

    _render_status()


def _render_status():
    """Render current OpenAI status."""
    if not st.session_state.openai_api_key:
        return

    status_parts = []
    if st.session_state.openai_vector_store_id:
        vs_id = st.session_state.openai_vector_store_id[:8]
        status_parts.append(f"VS: {vs_id}...")
    if st.session_state.openai_files:
        status_parts.append(f"Files: {len(st.session_state.openai_files)}")
    if st.session_state.openai_assistant_id:
        status_parts.append("Assistant: Ready")

    if status_parts:
        st.markdown(
            f"<div class='openai-status'>{' | '.join(status_parts)}</div>",
            unsafe_allow_html=True
        )


def _render_main_interface():
    """Render the main interface when API key is available."""
    _render_files_section()
    _render_chat_section()


def _render_files_section():
    """Render files upload and management."""
    with st.expander("Files & Upload", expanded=not st.session_state.openai_files):
        col_refresh, col_space = st.columns([1, 3])
        with col_refresh:
            if st.button("Refresh", key="openai_refresh", use_container_width=True):
                with st.spinner("Refreshing..."):
                    _load_existing_resources()
                st.rerun()

        files = st.file_uploader(
            "Upload to OpenAI",
            type=["pdf", "txt", "md", "docx"],
            accept_multiple_files=True,
            key="openai_uploader",
            label_visibility="collapsed"
        )

        if files:
            if st.button("Upload to OpenAI", use_container_width=True):
                _upload_files(files)

        _render_uploaded_files()
        _render_file_actions()


def _upload_files(files):
    """Upload files to OpenAI."""
    progress = st.empty()
    success_count = 0

    for i, f in enumerate(files):
        progress.markdown(f"Uploading {i+1}/{len(files)}: {f.name}...")
        result = _openai_upload_file(f.getvalue(), f.name)
        if result:
            success_count += 1

    progress.empty()

    if success_count > 0:
        st.success(f"Uploaded {success_count} file(s)")
        _load_existing_resources()

    st.rerun()


def _render_uploaded_files():
    """Render list of uploaded files."""
    if not st.session_state.openai_files:
        st.markdown(
            "<div style='color:#6b7280;font-size:0.8rem;padding:0.5rem;'>"
            "No files in vector store</div>",
            unsafe_allow_html=True
        )
        return

    st.markdown("**Files in Vector Store:**")
    files_html = ""
    for i, f in enumerate(st.session_state.openai_files):
        name = f.get('filename', f.get('id', 'unknown'))[:30]
        status = f.get('status', 'unknown')
        size_bytes = f.get('bytes', 0)
        size_kb = size_bytes // 1024 if size_bytes else 0

        status_color = "#10b981" if status == "completed" else "#f59e0b"
        size_str = f"{size_kb}KB" if size_kb > 0 else ""

        files_html += f"""
        <div class="openai-file-card">
            <span class="openai-file-name">[{i+1}] {name}</span>
            <span class="openai-file-meta" style="color:{status_color};">
                {status} {size_str}
            </span>
        </div>
        """
    st.markdown(files_html, unsafe_allow_html=True)


def _render_file_actions():
    """Render file action buttons."""
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Clear Chat", key="openai_clear_chat", use_container_width=True):
            clear_openai_chat()
            st.rerun()

    with col2:
        if st.session_state.openai_files or st.session_state.openai_vector_store_id:
            if st.button("Delete All", key="openai_cleanup", use_container_width=True):
                with st.spinner("Cleaning up..."):
                    _openai_cleanup()
                st.success("Cleaned up")
                st.rerun()


def _render_chat_section():
    """Render chat interface."""
    # Create a container for messages
    chat_container = st.container()

    with chat_container:
        # Display existing messages
        for msg in st.session_state.openai_messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="openai-msg openai-msg-user">
                    <div class="msg-header">You</div>
                    {msg["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                _render_assistant_message(msg)

        # Empty state
        if not st.session_state.openai_messages:
            _render_chat_empty_state()

        # Show loading spinner if processing
        if st.session_state.get("openai_processing", False):
            with st.spinner("Searching documents and generating response..."):
                time.sleep(0.1)  # Brief pause to show spinner

    # Chat input - only show if we have files
    if st.session_state.openai_files:
        query = st.chat_input("Ask OpenAI...", key="openai_chat_input")
        if query:
            _process_query(query)


def _process_query(query: str):
    """Process a chat query with loading state."""
    # Add user message immediately
    st.session_state.openai_messages.append({"role": "user", "content": query})

    # Set processing flag
    st.session_state.openai_processing = True

    # Show loading state
    with st.spinner("Searching documents and generating response..."):
        result = _openai_query(query)

    # Clear processing flag
    st.session_state.openai_processing = False

    # Add assistant response
    st.session_state.openai_messages.append({
        "role": "assistant",
        "content": result.get("answer", ""),
        "clean_content": result.get("clean_answer", ""),
        "citations": result.get("citations", []),
        "sources": result.get("sources", []),
        "time": result.get("time", 0),
        "error": result.get("error")
    })

    st.rerun()


def _render_assistant_message(msg: dict):
    """Render an assistant message with numbered citations and legend."""
    # Use clean content if available, otherwise original
    answer = msg.get("clean_content") or msg.get("content", "")

    if msg.get("error"):
        answer = f"Error: {msg['error']}"

    time_str = f"{msg.get('time', 0):.1f}s"

    # Build sources legend
    sources_html = ""
    sources = msg.get("sources", [])
    if sources:
        sources_html = "<div class='openai-sources'><b>Sources:</b><br>"
        for src in sources:
            num = src.get("number", "?")
            filename = src.get("filename", "Unknown")
            sources_html += f"<span class='openai-source-item'>[{num}] {filename}</span><br>"
        sources_html += "</div>"

    st.markdown(f"""
    <div class="openai-msg openai-msg-assistant">
        <div class="msg-header">
            OpenAI <span style="color:#6b7280;">({time_str})</span>
        </div>
        <div class="openai-answer">{answer}</div>
        {sources_html}
    </div>
    """, unsafe_allow_html=True)


def _render_chat_empty_state():
    """Render empty chat state."""
    if st.session_state.openai_files:
        msg = "Files ready. Ask a question to search."
    else:
        msg = "Upload files above, then ask questions."

    st.markdown(f"""
    <div style="text-align:center;color:#6b7280;padding:2rem;font-size:0.85rem;">
        {msg}
    </div>
    """, unsafe_allow_html=True)


def _render_no_key_message():
    """Render message when no API key is available."""
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


# ============================================
# Citation Processing Functions
# ============================================

def _process_citations(text: str, annotations: list, client) -> dict:
    """
    Process OpenAI annotations and convert to numbered references.

    Args:
        text: The raw answer text with 【...】 markers
        annotations: List of annotation objects from OpenAI
        client: OpenAI client for file lookups

    Returns:
        dict with clean_answer, citations list, and sources legend
    """
    if not annotations:
        return {
            "clean_answer": text,
            "citations": [],
            "sources": []
        }

    # Build file_id to filename mapping
    file_map = {}
    for f in st.session_state.openai_files:
        file_map[f["id"]] = f.get("filename", f["id"][:12])

    # Track unique sources and their numbers
    source_to_number = {}
    sources_list = []
    citation_number = 1

    # Process each annotation
    citations = []
    for ann in annotations:
        if hasattr(ann, 'file_citation'):
            file_id = getattr(ann.file_citation, 'file_id', None)

            if file_id:
                # Get or assign source number
                if file_id not in source_to_number:
                    source_to_number[file_id] = citation_number
                    filename = file_map.get(file_id)

                    # Try to get filename from API if not in local cache
                    if not filename and client:
                        try:
                            file_info = client.files.retrieve(file_id)
                            filename = file_info.filename
                        except Exception:
                            filename = file_id[:12]

                    sources_list.append({
                        "number": citation_number,
                        "file_id": file_id,
                        "filename": filename or file_id[:12]
                    })
                    citation_number += 1

                citations.append({
                    "file_id": file_id,
                    "number": source_to_number[file_id],
                    "text": getattr(ann, 'text', ''),
                    "quote": getattr(ann.file_citation, 'quote', '')
                })

    # Replace 【...】 markers with numbered references
    clean_answer = _replace_citation_markers(text, citations)

    return {
        "clean_answer": clean_answer,
        "citations": citations,
        "sources": sources_list
    }


def _replace_citation_markers(text: str, citations: list) -> str:
    """
    Replace OpenAI's citation markers with numbered references.

    Converts: 【4:11†source】 -> [1]
    """
    # Pattern to match OpenAI citation markers: 【...】
    pattern = r'【[^】]+】'

    # Find all markers
    markers = re.findall(pattern, text)

    if not markers:
        return text

    # Build marker to number mapping based on order of appearance
    marker_to_number = {}
    seen_files = {}
    current_num = 1

    for marker in markers:
        if marker not in marker_to_number:
            # Extract file reference from marker (e.g., "4:11" from "【4:11†source】")
            # The number before : often corresponds to file index
            match = re.search(r'【(\d+):', marker)
            if match:
                file_idx = match.group(1)
                if file_idx not in seen_files:
                    seen_files[file_idx] = current_num
                    current_num += 1
                marker_to_number[marker] = seen_files[file_idx]
            else:
                marker_to_number[marker] = current_num
                current_num += 1

    # Replace markers with numbered references
    result = text
    for marker, num in marker_to_number.items():
        result = result.replace(marker, f"[{num}]")

    return result


# ============================================
# OpenAI API Functions
# ============================================

def _get_openai_client():
    """Get OpenAI client with current API key."""
    try:
        from openai import OpenAI
        if st.session_state.openai_api_key:
            return OpenAI(api_key=st.session_state.openai_api_key)
    except Exception as e:
        st.error(f"Failed to create OpenAI client: {e}")
    return None


def _load_existing_resources():
    """Load existing vector stores and files from OpenAI."""
    client = _get_openai_client()
    if not client:
        return

    try:
        vector_stores = client.beta.vector_stores.list(limit=10)

        target_vs = None
        for vs in vector_stores.data:
            if vs.name == "RAG_Comparison_Store":
                target_vs = vs
                break

        if not target_vs and vector_stores.data:
            target_vs = vector_stores.data[0]

        if target_vs:
            st.session_state.openai_vector_store_id = target_vs.id

            vs_files = client.beta.vector_stores.files.list(
                vector_store_id=target_vs.id,
                limit=100
            )

            files_list = []
            for vs_file in vs_files.data:
                try:
                    file_info = client.files.retrieve(vs_file.id)
                    files_list.append({
                        "id": vs_file.id,
                        "filename": file_info.filename,
                        "bytes": file_info.bytes,
                        "status": vs_file.status
                    })
                except Exception:
                    files_list.append({
                        "id": vs_file.id,
                        "filename": vs_file.id[:20],
                        "bytes": 0,
                        "status": vs_file.status
                    })

            st.session_state.openai_files = files_list

            assistants = client.beta.assistants.list(limit=20)
            for asst in assistants.data:
                if asst.name == "RAG Comparison Assistant":
                    # Update assistant with new prompt and model if it exists
                    try:
                        client.beta.assistants.update(
                            asst.id,
                            instructions=QA_SYSTEM_PROMPT,
                            model=OPENAI_MODEL
                        )
                    except Exception:
                        pass
                    st.session_state.openai_assistant_id = asst.id
                    break
        else:
            st.session_state.openai_vector_store_id = None
            st.session_state.openai_files = []

    except Exception as e:
        st.warning(f"Could not load existing resources: {e}")


def _openai_upload_file(file_bytes: bytes, filename: str):
    """Upload a file to OpenAI and add to vector store."""
    client = _get_openai_client()
    if not client:
        return None

    try:
        if not st.session_state.openai_vector_store_id:
            vs = client.beta.vector_stores.create(name="RAG_Comparison_Store")
            st.session_state.openai_vector_store_id = vs.id

        file_obj = client.files.create(
            file=(filename, file_bytes),
            purpose="assistants"
        )

        vs_file = client.beta.vector_stores.files.create_and_poll(
            vector_store_id=st.session_state.openai_vector_store_id,
            file_id=file_obj.id
        )

        return {
            "id": file_obj.id,
            "filename": filename,
            "bytes": len(file_bytes),
            "status": vs_file.status
        }

    except Exception as e:
        st.error(f"Failed to upload {filename}: {e}")
        return None


def _openai_query(question: str) -> dict:
    """Query the OpenAI assistant with improved citation handling."""
    client = _get_openai_client()
    if not client:
        return {"answer": "", "citations": [], "error": "No API key", "time": 0}

    if not st.session_state.openai_vector_store_id:
        return {"answer": "", "citations": [], "error": "No vector store", "time": 0}

    try:
        # Create or update assistant
        if not st.session_state.openai_assistant_id:
            assistant = client.beta.assistants.create(
                name="RAG Comparison Assistant",
                instructions=QA_SYSTEM_PROMPT,
                model=OPENAI_MODEL,
                tools=[{"type": "file_search"}],
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [st.session_state.openai_vector_store_id]
                    }
                }
            )
            st.session_state.openai_assistant_id = assistant.id

        # Create thread if needed
        if not st.session_state.openai_thread_id:
            thread = client.beta.threads.create()
            st.session_state.openai_thread_id = thread.id

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
            messages = client.beta.threads.messages.list(
                thread_id=st.session_state.openai_thread_id,
                order="desc",
                limit=1
            )

            for msg in messages.data:
                if msg.role == "assistant":
                    answer_text = ""
                    annotations = []

                    for content in msg.content:
                        if content.type == "text":
                            answer_text = content.text.value

                            # Get annotations
                            if hasattr(content.text, 'annotations'):
                                annotations = content.text.annotations

                    # Process citations
                    citation_result = _process_citations(
                        answer_text, annotations, client
                    )

                    return {
                        "answer": answer_text,
                        "clean_answer": citation_result["clean_answer"],
                        "citations": citation_result["citations"],
                        "sources": citation_result["sources"],
                        "time": elapsed,
                        "error": None
                    }

        return {
            "answer": "",
            "citations": [],
            "sources": [],
            "error": f"Run status: {run.status}",
            "time": elapsed
        }

    except Exception as e:
        return {"answer": "", "citations": [], "sources": [], "error": str(e), "time": 0}


def _openai_cleanup():
    """Delete OpenAI resources."""
    client = _get_openai_client()
    if not client:
        return

    try:
        if st.session_state.openai_assistant_id:
            try:
                client.beta.assistants.delete(st.session_state.openai_assistant_id)
            except Exception:
                pass
            st.session_state.openai_assistant_id = None

        for f in st.session_state.openai_files:
            try:
                client.files.delete(f["id"])
            except Exception:
                pass
        st.session_state.openai_files = []

        if st.session_state.openai_vector_store_id:
            try:
                client.beta.vector_stores.delete(st.session_state.openai_vector_store_id)
            except Exception:
                pass
            st.session_state.openai_vector_store_id = None

        st.session_state.openai_thread_id = None
        st.session_state.openai_messages = []
        st.session_state.openai_initialized = False

    except Exception as e:
        st.error(f"Cleanup error: {e}")
