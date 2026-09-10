import hashlib
import streamlit as st


def extract_text_from_pdf(uploaded_file):
    """Reuse the current PDF's extracted text within this user's session."""
    content = uploaded_file.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    cached = st.session_state.get('_pdf_text_cache')
    if cached and cached['digest'] == digest:
        return cached['text']

    import fitz  # Load the PDF parser only when a PDF is uploaded.
    with fitz.open(stream=content, filetype='pdf') as document:
        text = ''.join(page.get_text() for page in document).strip()
    st.session_state['_pdf_text_cache'] = {'digest': digest, 'text': text}
    return text
