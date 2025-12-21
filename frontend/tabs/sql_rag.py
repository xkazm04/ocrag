"""Agentic SQL RAG chat tab."""
import streamlit as st
from api import send_message_agentic
from config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM


def render_sql_rag_tab():
    """Render the Agentic SQL RAG chat interface."""
    chat_container = st.container()

    with chat_container:
        if st.session_state.messages_agentic:
            _render_messages()
        else:
            _render_empty_state()

    _handle_input()


def _render_messages():
    """Render chat messages."""
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
            conf_class = _get_confidence_class(conf)
            iterations = msg.get('iterations', 0)

            st.markdown(f"""
            <div class="msg msg-agentic">
                <div class="msg-header">
                    Agentic <span class="{conf_class}">({conf:.0%})</span> | {iterations} iters
                </div>
                {msg["content"]}
            </div>
            """, unsafe_allow_html=True)

            _render_details(msg)


def _render_details(msg: dict):
    """Render expandable details for a message."""
    if not msg.get("queries_executed") and not msg.get("reasoning_steps"):
        return

    with st.expander("Details", expanded=False):
        if msg.get("reasoning_steps"):
            for step in msg["reasoning_steps"]:
                st.markdown(
                    f"<div class='info-box'>{step}</div>",
                    unsafe_allow_html=True
                )

        if msg.get("queries_executed"):
            for q in msg["queries_executed"]:
                st.code(q, language="sql")

        if msg.get("sources"):
            st.markdown("Sources: " + ", ".join(f"`{s}`" for s in msg["sources"]))


def _render_empty_state():
    """Render empty state message."""
    st.markdown("""
    <div style="text-align:center;color:#6b7280;padding:2rem;font-size:0.85rem;">
        <b>Agentic SQL RAG</b><br>
        Iterative SQL queries with LLM reasoning. Best for precise facts.
    </div>
    """, unsafe_allow_html=True)


def _handle_input():
    """Handle chat input."""
    query = st.chat_input("Ask question (SQL RAG)...", key="input_agentic")

    if query:
        st.session_state.messages_agentic.append({"role": "user", "content": query})

        with st.spinner("Querying..."):
            response = send_message_agentic(query)
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


def _get_confidence_class(confidence: float) -> str:
    """Get CSS class based on confidence level."""
    if confidence > CONFIDENCE_HIGH:
        return "conf-high"
    elif confidence > CONFIDENCE_MEDIUM:
        return "conf-med"
    return "conf-low"
