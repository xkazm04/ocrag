"""OCR file uploader component."""
import streamlit as st
from typing import Optional


def render_uploader() -> tuple[Optional[bytes], Optional[str], list[str], list[str]]:
    """
    Render file upload section.

    Returns:
        Tuple of (file_bytes, filename, selected_engines, languages)
    """
    st.markdown("### Upload Document")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload image or PDF",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        help="Supported: PNG, JPG, WEBP, PDF (max 50MB)",
        label_visibility="collapsed"
    )

    file_bytes = None
    filename = None

    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name

        # Show preview for images
        if uploaded_file.type.startswith("image/"):
            st.image(file_bytes, caption=filename, width=300)
        else:
            st.info(f"📄 {filename} ({len(file_bytes) // 1024} KB)")

    # Engine selection
    st.markdown("### Select Engines")

    engines_by_category = {
        "LLM APIs": [
            ("gpt", "GPT-4o"),
            ("gemini", "Gemini 2.0 Flash"),
            ("mistral", "Mistral OCR"),
        ],
        "Open LLM": [
            ("qwen", "Qwen2 VL 72B"),
        ],
        "Traditional": [
            ("paddle", "PaddleOCR"),
            ("easy", "EasyOCR"),
            ("surya", "Surya OCR"),
        ]
    }

    selected_engines = []

    cols = st.columns(3)
    for idx, (category, engines) in enumerate(engines_by_category.items()):
        with cols[idx]:
            st.markdown(f"**{category}**")
            for engine_id, engine_name in engines:
                if st.checkbox(engine_name, value=True, key=f"engine_{engine_id}"):
                    selected_engines.append(engine_id)

    # Language selection
    st.markdown("### Languages")
    lang_options = {
        "en": "English",
        "de": "German",
        "fr": "French",
        "es": "Spanish",
        "cs": "Czech",
        "zh": "Chinese",
    }

    languages = st.multiselect(
        "Document languages",
        options=list(lang_options.keys()),
        default=["en"],
        format_func=lambda x: lang_options[x],
        label_visibility="collapsed"
    )

    if not languages:
        languages = ["en"]

    return file_bytes, filename, selected_engines, languages
