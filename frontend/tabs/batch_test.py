"""Batch testing tab for comparing RAG modes."""
import json
import streamlit as st
from api import query_map_rag, query_sql_rag
from state import clear_batch_results
from config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, MAX_ANSWER_PREVIEW


def render_batch_test_tab():
    """Render the batch testing interface."""
    st.markdown("**Compare both RAG modes with batch questions**")

    _render_input_section()
    _render_action_buttons()
    _render_results()


def _render_input_section():
    """Render the input section for questions."""
    col_upload, col_sample = st.columns([3, 2])

    with col_upload:
        st.file_uploader(
            "Upload JSON file with questions",
            type=["json"],
            help='Format: {"questions": ["Q1", "Q2", ...]} or ["Q1", "Q2", ...]',
            label_visibility="collapsed",
            key="batch_file"
        )

    with col_sample:
        with st.expander("Sample Format", expanded=False):
            st.code('''{"questions": [
  "What is the main topic?",
  "Who are the key people?",
  "What metrics are mentioned?"
]}''', language="json")

    st.text_area(
        "Or enter questions (one per line)",
        height=80,
        placeholder="What is the document about?\nWhat are the key findings?",
        label_visibility="collapsed",
        key="manual_questions"
    )


def _render_action_buttons():
    """Render run and clear buttons."""
    col_run, col_clear = st.columns([1, 1])

    with col_run:
        if st.button("Run Batch Test", use_container_width=True, type="primary"):
            _run_batch_test()

    with col_clear:
        if st.button("Clear Results", use_container_width=True):
            clear_batch_results()
            st.rerun()


def _run_batch_test():
    """Execute batch test with provided questions."""
    questions = _parse_questions()

    if not questions:
        st.warning("No questions provided. Upload a JSON file or enter questions manually.")
        return

    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, question in enumerate(questions):
        status_text.markdown(
            f"<div class='batch-progress'>"
            f"Processing {i+1}/{len(questions)}: {question[:50]}...</div>",
            unsafe_allow_html=True
        )
        progress_bar.progress((i + 1) / len(questions))

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


def _parse_questions() -> list:
    """Parse questions from file or manual input."""
    batch_file = st.session_state.get("batch_file")
    manual_questions = st.session_state.get("manual_questions", "")

    if batch_file:
        try:
            content = batch_file.read().decode('utf-8')
            data = json.loads(content)

            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'questions' in data:
                return data['questions']
            else:
                st.error("Invalid format. Expected list or {questions: [...]}")
                return []
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            return []

    if manual_questions.strip():
        return [q.strip() for q in manual_questions.strip().split('\n') if q.strip()]

    return []


def _render_results():
    """Render batch test results."""
    results = st.session_state.batch_results

    if not results:
        _render_empty_state()
        return

    _render_summary(results)
    _render_export_button(results)

    st.markdown("---")

    for i, result in enumerate(results):
        _render_result_card(i, result)


def _render_empty_state():
    """Render empty state message."""
    st.markdown("""
    <div style="text-align:center;color:#6b7280;padding:2rem;font-size:0.85rem;">
        <b>Batch Tester</b><br>
        Upload a JSON file with questions or enter them manually.<br>
        Both RAG modes will be queried for each question to compare results.
    </div>
    """, unsafe_allow_html=True)


def _render_summary(results: list):
    """Render summary statistics."""
    total = len(results)
    avg_map_time = sum(r['map_rag']['time'] for r in results) / total
    avg_sql_time = sum(r['sql_rag']['time'] for r in results) / total
    avg_map_conf = sum(r['map_rag']['confidence'] for r in results) / total
    avg_sql_conf = sum(r['sql_rag']['confidence'] for r in results) / total

    st.markdown(f"""
    <div class="batch-summary">
        <div class="batch-summary-item">
            <div class="batch-summary-value">{total}</div>
            <div class="batch-summary-label">Questions</div>
        </div>
        <div class="batch-summary-item">
            <div class="batch-summary-value">{avg_map_time:.1f}s</div>
            <div class="batch-summary-label">Avg Map Time</div>
        </div>
        <div class="batch-summary-item">
            <div class="batch-summary-value">{avg_sql_time:.1f}s</div>
            <div class="batch-summary-label">Avg SQL Time</div>
        </div>
        <div class="batch-summary-item">
            <div class="batch-summary-value">{avg_map_conf:.0%}</div>
            <div class="batch-summary-label">Avg Map Conf</div>
        </div>
        <div class="batch-summary-item">
            <div class="batch-summary-value">{avg_sql_conf:.0%}</div>
            <div class="batch-summary-label">Avg SQL Conf</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_export_button(results: list):
    """Render export button."""
    export_data = json.dumps(results, indent=2, default=str)
    st.download_button(
        "Export Results (JSON)",
        data=export_data,
        file_name="batch_results.json",
        mime="application/json"
    )


def _render_result_card(index: int, result: dict):
    """Render a single result card."""
    q = result['question']
    map_r = result['map_rag']
    sql_r = result['sql_rag']

    map_conf_class = _get_confidence_class(map_r['confidence'])
    sql_conf_class = _get_confidence_class(sql_r['confidence'])

    map_answer = _truncate_answer(map_r['answer'])
    sql_answer = _truncate_answer(sql_r['answer'])

    st.markdown(f"""
    <div class="batch-result">
        <div class="batch-question">Q{index+1}: {q}</div>
        <div class="batch-answers">
            <div class="batch-answer batch-answer-map">
                <div class="batch-answer-header">
                    <span>Map RAG</span>
                    <span class="{map_conf_class}">
                        {map_r['confidence']:.0%} | {map_r['time']:.1f}s
                    </span>
                </div>
                <div class="batch-answer-content">{map_answer}</div>
                <div class="batch-meta">Citations: {len(map_r.get('citations', []))}</div>
            </div>
            <div class="batch-answer batch-answer-sql">
                <div class="batch-answer-header">
                    <span>SQL RAG</span>
                    <span class="{sql_conf_class}">
                        {sql_r['confidence']:.0%} | {sql_r['time']:.1f}s
                    </span>
                </div>
                <div class="batch-answer-content">{sql_answer}</div>
                <div class="batch-meta">
                    Iterations: {sql_r.get('iterations', 0)} |
                    Queries: {len(sql_r.get('queries', []))}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _render_details_expander(index, map_r, sql_r)


def _render_details_expander(index: int, map_r: dict, sql_r: dict):
    """Render expandable details for a result."""
    with st.expander(f"Details Q{index+1}", expanded=False):
        col_map, col_sql = st.columns(2)

        with col_map:
            st.markdown("**Full Map RAG Answer:**")
            st.markdown(
                f"<div class='code-preview'>{map_r['answer']}</div>",
                unsafe_allow_html=True
            )
            if map_r.get('citations'):
                st.markdown("**Citations:**")
                for c in map_r['citations']:
                    st.markdown(f"- `{c.get('doc_id', '?')}`: {c.get('relevance', 'N/A')}")

        with col_sql:
            st.markdown("**Full SQL RAG Answer:**")
            st.markdown(
                f"<div class='code-preview'>{sql_r['answer']}</div>",
                unsafe_allow_html=True
            )
            if sql_r.get('queries'):
                st.markdown("**SQL Queries:**")
                for q in sql_r['queries']:
                    st.code(q, language="sql")


def _truncate_answer(answer: str) -> str:
    """Truncate answer for display."""
    if not answer:
        return '(Error or empty)'
    if len(answer) > MAX_ANSWER_PREVIEW:
        return answer[:MAX_ANSWER_PREVIEW] + '...'
    return answer


def _get_confidence_class(confidence: float) -> str:
    """Get CSS class based on confidence level."""
    if confidence > CONFIDENCE_HIGH:
        return "conf-high"
    elif confidence > CONFIDENCE_MEDIUM:
        return "conf-med"
    return "conf-low"
