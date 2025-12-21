"""Document Map viewer tab."""
import streamlit as st
from api import load_document_map


def render_doc_map_tab():
    """Render the document map viewer interface."""
    col_load_map, col_info_map = st.columns([1, 4])

    with col_load_map:
        if st.button("Load Map", use_container_width=True):
            load_document_map()

    doc_map = st.session_state.document_map

    if not doc_map:
        st.markdown(
            "<div style='color:#6b7280;text-align:center;padding:2rem;'>"
            "Click 'Load Map' to view the document map structure</div>",
            unsafe_allow_html=True
        )
        return

    with col_info_map:
        last_updated = doc_map.get('last_updated', 'N/A')
        st.markdown(
            f"<span style='color:#6b7280;font-size:0.75rem;'>"
            f"Last updated: {last_updated}</span>",
            unsafe_allow_html=True
        )

    _render_corpus_summary(doc_map)
    _render_main_content(doc_map)


def _render_corpus_summary(doc_map: dict):
    """Render the corpus summary section."""
    if not doc_map.get('corpus_summary'):
        return

    st.markdown(f"""
    <div class="map-section">
        <div class="map-section-title">Corpus Summary</div>
        <div class="map-summary-box">{doc_map['corpus_summary']}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_main_content(doc_map: dict):
    """Render documents and cross-references in two columns."""
    col_docs_map, col_xrefs = st.columns([3, 2])

    with col_docs_map:
        _render_documents(doc_map)

    with col_xrefs:
        _render_cross_references(doc_map)


def _render_documents(doc_map: dict):
    """Render the documents list."""
    docs = doc_map.get('documents', [])
    st.markdown(f"""
    <div class="map-section">
        <div class="map-section-title">Documents ({len(docs)})</div>
    </div>
    """, unsafe_allow_html=True)

    for doc in docs:
        _render_document_card(doc)


def _render_document_card(doc: dict):
    """Render a single document card."""
    topics_html = _build_topics_html(doc)
    entities_html = _build_entities_html(doc)
    chunks_html = _build_chunks_html(doc)

    essence = doc.get('essence', '')
    essence_display = essence[:200] + ('...' if len(essence) > 200 else '')

    st.markdown(f"""
    <div class="map-doc-card">
        <div class="map-doc-title">{doc.get('filename', 'Unknown')}</div>
        <div class="map-doc-essence">{essence_display}</div>
        <div class="map-doc-meta">
            Type: {doc.get('type', 'other')} |
            Size: {doc.get('size_class', '?')} |
            ID: {doc.get('id', '?')[:12]}
        </div>
        {topics_html}
        {entities_html}
        {chunks_html}
    </div>
    """, unsafe_allow_html=True)


def _build_topics_html(doc: dict) -> str:
    """Build HTML for document topics."""
    if not doc.get('topics'):
        return ""

    topics = ''.join(
        f'<span class="map-topic">{t}</span>'
        for t in doc['topics'][:8]
    )
    return f'<div class="map-topics">{topics}</div>'


def _build_entities_html(doc: dict) -> str:
    """Build HTML for document entities."""
    if not doc.get('entities'):
        return ""

    html = ""
    for etype, elist in doc['entities'].items():
        if not elist:
            continue

        entities = ''.join(
            f'<span class="map-entity">{e}</span>'
            for e in elist[:6]
        )
        html += f'''
        <div class="map-entity-section">
            <div class="map-entity-type">{etype}</div>
            <div class="map-entity-list">{entities}</div>
        </div>
        '''
    return html


def _build_chunks_html(doc: dict) -> str:
    """Build HTML for document chunks preview."""
    if not doc.get('chunks'):
        return ""

    html = '<div style="margin-top:0.3rem;">'
    for chunk in doc['chunks'][:3]:
        section = chunk.get("section", "?")
        context = chunk.get("context", "")[:60]
        html += f'<div class="map-chunk">{section} - {context}...</div>'

    if len(doc['chunks']) > 3:
        remaining = len(doc["chunks"]) - 3
        html += f'<div class="map-chunk">... +{remaining} more chunks</div>'

    html += '</div>'
    return html


def _render_cross_references(doc_map: dict):
    """Render cross-references section."""
    xrefs = doc_map.get('cross_references', {})
    by_topic = xrefs.get('by_topic', {})
    by_entity = xrefs.get('by_entity', {})

    if by_topic:
        _render_xref_section("Cross-Refs by Topic", by_topic)

    if by_entity:
        _render_xref_section("Cross-Refs by Entity", by_entity, margin_top=True)

    if not by_topic and not by_entity:
        st.markdown(
            "<div style='color:#6b7280;font-size:0.8rem;'>"
            "No cross-references yet</div>",
            unsafe_allow_html=True
        )


def _render_xref_section(title: str, xrefs: dict, margin_top: bool = False):
    """Render a cross-reference section."""
    style = 'style="margin-top:0.5rem;"' if margin_top else ''

    st.markdown(f"""
    <div class="map-section" {style}>
        <div class="map-section-title">{title} ({len(xrefs)})</div>
    </div>
    """, unsafe_allow_html=True)

    for key, doc_ids in list(xrefs.items())[:10]:
        docs_str = ', '.join(d[:8] for d in doc_ids)
        st.markdown(f"""
        <div class="map-xref-row">
            <span class="map-xref-key">{key[:25]}</span>
            <span class="map-xref-docs">{docs_str}</span>
        </div>
        """, unsafe_allow_html=True)
