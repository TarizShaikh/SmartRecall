import uuid
import streamlit as st
from utils.auth import require_login
from utils.ui import setup_ui, page_header
from utils.study import require_note, persist
from utils.gemini_helper import generate_quiz, LearningError
from utils.quiz_engine import evaluate_quiz
from utils import database as db

st.set_page_config(page_title='SmartRecall · Practice quiz', page_icon='✏️', layout='wide')
setup_ui()
require_login()
page_header('Practice quiz', 'Check your understanding, then learn from an explanation for every answer.')
note = require_note()
questions = st.session_state.get('quiz_questions', [])
if st.button('Generate a new quiz' if questions else 'Generate quiz', type='primary'):
    try:
        with st.spinner('Preparing five questions with explanations…'):
            generated = generate_quiz(note['extracted_text'])
            persist('quiz', generated)
        for key in list(st.session_state):
            if key.startswith('answer_') or key in ('quiz_result','quiz_saved'):
                del st.session_state[key]
        st.session_state.quiz_token = uuid.uuid4().hex
        st.rerun()
    except LearningError as error:
        st.error(str(error))
    except Exception:
        st.error('Could not save the quiz. Please try again.')
if questions:
    token = st.session_state.setdefault('quiz_token', uuid.uuid4().hex)
    result = st.session_state.get('quiz_result')
    if not result:
        answered = sum(st.session_state.get(f'answer_{token}_{i}') is not None for i in range(len(questions)))
        st.progress(answered/len(questions), text=f'{answered} of {len(questions)} questions answered')
        answers = []
        for i, question in enumerate(questions):
            with st.container(border=True):
                answer = st.radio(f"{i+1}. {question['question']}", question['options'], index=None, key=f'answer_{token}_{i}')
                answers.append(answer)
        if st.button('Submit quiz', type='primary'):
            try:
                st.session_state.quiz_result = evaluate_quiz(questions, answers)
                st.rerun()
            except ValueError as error:
                st.warning(str(error))
    else:
        if not st.session_state.get('quiz_saved'):
            try:
                db.save_quiz_attempt(st.session_state.user_id, note['id'], result['score'], token, result['details'])
                st.session_state.quiz_saved = True
            except Exception:
                st.warning('Your result is shown below, but saving failed. Retry to store it in your history.')
                if st.button('Retry saving result'):
                    st.rerun()
        st.metric('Your score', f"{result['score']:g}%")
        st.write(f"{result['correct']} of {result['total']} correct")
        if st.session_state.get('quiz_saved'):
            st.caption('Saved to this note’s quiz history.')
        for i,item in enumerate(result['details']):
            with st.container(border=True):
                st.subheader(f"{'✓' if item['correct'] else '↻'} {i+1}. {item['question']}")
                st.write(f"Your answer: {item['selected']}")
                if not item['correct']:
                    st.write(f"Correct answer: {item['answer']}")
                st.info(item['explanation'])
        st.page_link('pages/4_Memory_Revision.py', label='Plan your next revision →')
        if st.button('Try this quiz again'):
            st.session_state.quiz_token = uuid.uuid4().hex
            st.session_state.pop('quiz_result',None)
            st.session_state.pop('quiz_saved',None)
            st.rerun()
else:
    st.info('Your generated quiz will be saved with this note for future practice.')
