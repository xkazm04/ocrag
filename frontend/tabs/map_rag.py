"""Document Map RAG chat tab."""
import streamlit as st
from api import send_message_map
from config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM


def render_map_rag_tab():
    """Render the Document Map RAG chat interface."""
    chat_container = st.container()

    with chat_container:
        if st.session_state.messages_map:
            _render_messages()
        else:
            _render_empty_state()

    _handle_input()


def _render_messages():
    """Render chat messages."""
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
            conf_class = _get_confidence_class(conf)

            citations = ""
            if msg.get("citations"):
                citations = " ".join(
                    f"<span class='badge'>{c.get('doc_id', '?')[:12]}</span>"
                    for c in msg["citations"]
                )

            st.markdown(f"""
            <div class="msg msg-assistant">
                <div class="msg-header">
                    Assistant <span class="{conf_class}">({conf:.0%})</span>
                </div>
                {msg["content"]}
                <div style="margin-top:0.3rem;">{citations}</div>
            </div>
            """, unsafe_allow_html=True)


def _render_empty_state():
    """Render empty state message."""
    st.markdown("""
    <div style="text-align:center;color:#6b7280;padding:2rem;font-size:0.85rem;">
        <b>Document Map RAG</b><br>
        One-shot retrieval using document map. Fast (1-2 LLM calls).
    </div>
    """, unsafe_allow_html=True)


def _handle_input():
    """Handle chat input."""
    query = st.chat_input("Ask question (Map RAG)...", key="input_map")

    if query:
        st.session_state.messages_map.append({"role": "user", "content": query})

        with st.spinner("Retrieving..."):
            response = send_message_map(query)
            if response:
                st.session_state.messages_map.append({
                    "role": "assistant",
                    "content": response["answer"],
                    "citations": response.get("citations", []),
                    "confidence": response.get("confidence", 0.5),
                })

        st.rerun()


def _get_confidence_class(confidence: float) -> str:
    """Get CSS class based on confidence level."""
    if confidence > CONFIDENCE_HIGH:
        return "conf-high"
    elif confidence > CONFIDENCE_MEDIUM:
        return "conf-med"
    return "conf-low"
