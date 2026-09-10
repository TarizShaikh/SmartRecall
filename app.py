from html import escape
from datetime import date
import streamlit as st
from utils.database import (initialize_database, get_dashboard_statistics, get_recent_notes,
                            get_recent_quiz_attempts, get_upcoming_revisions, authenticate_user, register_user)
from utils.ui import setup_ui, empty_state, activity_row

st.set_page_config(page_title="SmartRecall · Overview", page_icon="🧠", layout="wide")
for key, value in {'logged_in': False, 'username': '', 'user_id': None, 'extracted_text': '',
                   'subject_name': '', 'file_name': '', 'summary': '', 'flashcards': '',
                   'quiz_questions': [], 'last_quiz_score': 70}.items():
    if key not in st.session_state:
        st.session_state[key] = value
setup_ui()
if not st.session_state.get('_database_initialized'):
    initialize_database()
    st.session_state['_database_initialized'] = True

if not st.session_state.logged_in:
    intro, account = st.columns([1.2, 1], gap="large")
    with intro:
        st.markdown('<div class="sr-eyebrow">Meet your study companion</div>', unsafe_allow_html=True)
        st.title('Learn more.\nRemember longer.')
        st.write('Turn your study notes into focused practice, and build a revision routine that works for you.')
        st.markdown('<div class="sr-hero"><div class="sr-eyebrow">A simpler way to study</div><h2>Small sessions.<br>Lasting knowledge.</h2><p>Move from reading to remembering with summaries, flashcards and quizzes built around your notes.</p></div>', unsafe_allow_html=True)
        for title, description in [('01 · Bring your notes', 'Upload a PDF and create a concise study summary.'), ('02 · Put recall into practice', 'Review flashcards and test yourself with a quiz.'), ('03 · Keep it fresh', 'Use your results to plan your next revision.')]:
            activity_row(title, description)
    with account:
        with st.container(border=True):
            st.subheader('Your next chapter starts here')
            st.caption('Sign in to your personal learning workspace.')
            login, register = st.tabs(['Sign in', 'Create account'])
            with login:
                with st.form('login_form'):
                    username = st.text_input('Username', key='login_username', placeholder='Enter your username')
                    password = st.text_input('Password', type='password', key='login_password', placeholder='Enter your password')
                    submitted = st.form_submit_button('Sign in →', type='primary', use_container_width=True)
                if submitted:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.update(logged_in=True, user_id=user[0], username=user[1])
                        st.rerun()
                    else:
                        st.error('Invalid username or password.')
            with register:
                with st.form('register_form'):
                    new_username = st.text_input('Choose a username', key='register_username')
                    new_password = st.text_input('Choose a password', type='password', key='register_password')
                    confirm_password = st.text_input('Confirm password', type='password', key='confirm_password')
                    create = st.form_submit_button('Create account →', type='primary', use_container_width=True)
                if create:
                    if not new_username.strip():
                        st.warning('Please enter a username.')
                    elif not new_password:
                        st.warning('Please enter a password.')
                    elif new_password != confirm_password:
                        st.warning('Passwords do not match.')
                    elif register_user(new_username.strip(), new_password):
                        st.success('Account created. Open Sign in to get started.')
                    else:
                        st.error('Username already exists.')
    st.stop()

statistics = get_dashboard_statistics(st.session_state.user_id)
st.caption(date.today().strftime('%A, %d %B %Y').upper())
st.title(f"Welcome back, {st.session_state.username}")
st.write('A little progress today. A stronger memory tomorrow.')
st.markdown('<div class="sr-hero"><div class="sr-eyebrow">Your next study session</div><h2>Make room for what matters.</h2><p>Start with your notes, practise what you know, and keep your learning fresh.</p></div>', unsafe_allow_html=True)
for col, label, value in zip(st.columns(4), ['Notes saved', 'Quizzes completed', 'Average quiz score', 'Pending revisions'],
                             [statistics['notes'], statistics['quizzes'], f"{statistics['average_score']}%" if statistics['quizzes'] else '—', statistics['pending_revisions']]):
    col.metric(label, value)
st.write('')
st.subheader('Pick up your learning')
for col, step, title, detail, path, action in zip(st.columns(3), ['01 / PREPARE', '02 / PRACTISE', '03 / REMEMBER'],
    ['Build your study library', 'Test your understanding', 'Plan your next revision'],
    ['Turn PDF notes into a focused summary.', 'Build confidence with active recall.', 'Keep important concepts fresh in your mind.'],
    ['pages/1_Study_Notes.py', 'pages/3_Quiz.py', 'pages/4_Memory_Revision.py'],
    ['Open study notes →', 'Start a quiz →', 'View revision plan →']):
    with col:
        with st.container(border=True):
            st.caption(step)
            st.subheader(title)
            st.caption(detail)
            st.page_link(path, label=action)
st.write('')
main, side = st.columns([1.65, 1], gap='large')
with main:
    with st.container(border=True):
        st.subheader('Your study activity')
        notes_tab, quizzes_tab = st.tabs(['Recent notes', 'Quiz results'])
        with notes_tab:
            notes = get_recent_notes(st.session_state.user_id)
            if notes:
                for subject, filename, created in notes:
                    activity_row(filename, f'{subject} · Saved {created}')
            else:
                empty_state('Your library starts with one note', 'Upload and save a PDF to see it here.')
            st.page_link('pages/1_Study_Notes.py', label='Go to study notes →')
        with quizzes_tab:
            quizzes = get_recent_quiz_attempts(st.session_state.user_id)
            if quizzes:
                for subject, score, attempted in quizzes:
                    status = 'Excellent' if score >= 85 else 'Good progress' if score >= 70 else 'Keep practising'
                    activity_row(f'{subject} · {score}%', f'{status} · {attempted}')
            else:
                empty_state('See your progress take shape', 'Complete your first quiz to see your results here.')
            st.page_link('pages/3_Quiz.py', label='Open practice quiz →')
with side:
    with st.container(border=True):
        st.subheader('Coming up next')
        revisions = get_upcoming_revisions(st.session_state.user_id)
        if revisions:
            for subject, retention, revision_date, status in revisions:
                activity_row(subject, f'{revision_date} · {retention}% estimated retention · {status}')
        else:
            empty_state('A clear schedule', 'Save a revision recommendation to plan your next session.')
        st.page_link('pages/4_Memory_Revision.py', label='Manage revision →')
    with st.container(border=True):
        st.subheader('Learning snapshot')
        if statistics['quizzes']:
            score = float(statistics['average_score'])
            st.progress(max(0.0, min(score / 100, 1.0)))
            st.caption(f'{score:g}% average across {statistics["quizzes"]} quiz attempts')
            st.write('Keep building on your progress.' if score >= 70 else 'Revisit your notes, then try another quiz.')
        else:
            st.caption('Your average quiz score will appear here after your first attempt.')


