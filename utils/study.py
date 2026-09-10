"""Study selection state; switching documents clears all document-specific UI state."""
import hashlib
import uuid
import streamlit as st
from utils import database as db


def reset_study_state(state):
    for key in list(state):
        if key.startswith(('answer_', 'quiz_', 'card_', 'study_', 'review_')) or key in (
            'active_note_id', 'extracted_text', 'subject_name', 'file_name', 'summary',
            'flashcards', 'keywords', 'last_quiz_score', '_pdf_text_cache'):
            del state[key]


def activate_note(user_id, note_id):
    note = db.get_note(user_id, note_id)
    material = db.get_material(user_id, note_id)
    reset_study_state(st.session_state)
    st.session_state.update(active_note_id=note_id, extracted_text=note['extracted_text'],
        subject_name=note['subject'], file_name=note['file_name'], summary=material.get('summary', ''),
        flashcards=material.get('flashcards', []), keywords=material.get('keywords', []),
        quiz_questions=material.get('quiz', []), quiz_token=uuid.uuid4().hex, card_index=0, card_revealed=False)


def require_note():
    if not st.session_state.get('active_note_id'):
        st.info('Choose a saved note or add study material to get started.')
        st.page_link('pages/1_Study_Notes.py', label='Open study library →')
        st.stop()
    note = db.get_note(st.session_state.user_id, st.session_state.active_note_id)
    st.caption(f"STUDYING · {note['subject']} · {note['file_name']}")
    return note


def persist(kind, value):
    db.save_material(st.session_state.user_id, st.session_state.active_note_id, kind, value)
    st.session_state[{'quiz': 'quiz_questions'}.get(kind, kind)] = value


def input_changed(state, identity):
    """Invalidate material immediately when the upload or pasted content changes."""
    if state.get('_input_identity') != identity:
        reset_study_state(state)
        state['_input_identity'] = identity
        return True
    return False


def content_identity(subject, name, content):
    return hashlib.sha256(subject.encode() + b'\0' + name.encode() + b'\0' + content).hexdigest()
