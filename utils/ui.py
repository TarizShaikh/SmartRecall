from html import escape
import streamlit as st

PAGES = [('app.py', 'Overview', '◈'), ('pages/1_Study_Notes.py', 'Study library', '📚'), ('pages/2_Flashcards.py', 'Flashcards', '🗂️'), ('pages/3_Quiz.py', 'Practice quiz', '✏️'), ('pages/4_Memory_Revision.py', 'Memory & revision', '📈'), ('pages/5_Profile.py', 'Your profile', '👤')]

def setup_ui():
    st.markdown('''<style>
    [data-stale="true"] {visibility: hidden;}
    .stApp {background: #0e111b; color: #eef0fa;}
    .block-container {max-width: 1240px; padding-top: 2.5rem; padding-bottom: 3rem;}
    h1,h2,h3 {letter-spacing: -.035em; color: #eef0fa;}
    h1 {font-size: 2.4rem !important;} h2 {font-size: 1.5rem !important;} h3 {font-size: 1.12rem !important;}
    [data-testid="stSidebar"] {background: #151a28; border-right: 1px solid #2b3348;}
    [data-testid="stSidebarNav"] {display:none;}
    [data-testid="stSidebar"] [data-testid="stPageLink"] {padding: .25rem 0;}
    [data-testid="stMetric"] {background: #181e2e; border: 1px solid #2b3348; border-radius: 16px; padding: 20px;}
    [data-testid="stMetricLabel"] {color: #b4bdd3;}
    [data-testid="stMetricValue"] {font-weight: 700;}
    [data-testid="stVerticalBlockBorderWrapper"] > div {border-radius: 16px !important;}
    .stButton button, .stFormSubmitButton button {border-radius: 10px; min-height: 44px; font-weight:600;}
    button:focus-visible, a:focus-visible {outline: 3px solid #b8aaff !important; outline-offset: 3px;}
    [data-testid="stTextInput"] input {min-height: 44px;}
    [data-testid="stTabs"] [role="tablist"] {gap: 24px;}
    .sr-brand {font-size: 24px; font-weight: 800; letter-spacing: -1px; margin-bottom: 4px;}
    .sr-brand span {color:#b3a3ff;}
    .sr-eyebrow {font-size: 11px; font-weight: 700; letter-spacing: .15em; color: #b3a3ff; text-transform: uppercase; margin: 20px 0 12px;}
    .sr-muted {color: #b4bdd3; font-size: 14px; line-height: 1.7;}
    .sr-hero {background: #25213d; border:1px solid #443b63; border-radius: 20px; padding: 30px; margin: 10px 0 24px;}
    .sr-hero h2 {font-size: 30px !important; margin: 0 0 10px;}
    .sr-hero p {color:#cbc4e4; line-height:1.7; margin:0;}
    .sr-row {padding: 16px 0; border-bottom: 1px solid #2b3348;}
    .sr-row strong {display:block; margin-bottom:5px; overflow-wrap:anywhere;}
    .sr-row small {color: #b4bdd3;}
    .sr-empty {padding: 30px 16px; text-align:center; border:1px dashed #45506b; border-radius:14px; margin:12px 0;}
    .sr-empty strong {display:block; margin-bottom:8px;}
    @media(max-width:640px) {.block-container {padding:1.5rem 1rem;} .sr-hero {padding:22px;} h1 {font-size:1.9rem !important;}}
    </style>''', unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('<div class="sr-brand"><span>◈</span> SmartRecall</div><div class="sr-muted">Your learning workspace</div>', unsafe_allow_html=True)
        st.divider()
        if st.session_state.get('logged_in'):
            st.caption('WORKSPACE')
            for path, label, icon in PAGES:
                st.page_link(path, label=label, icon=icon if icon != '◈' else '🏠')
            st.divider()
            st.caption('SIGNED IN AS')
            st.write(st.session_state.get('username', 'Learner'))
            st.markdown('<div class="sr-hero" style="padding:18px;margin-top:24px"><strong>A little, often.</strong><p>Make time for one small revision today.</p></div>', unsafe_allow_html=True)
        else:
            st.caption('LEARN WITH INTENTION')
            st.write('Read. Recall. Remember.')
            st.caption('Your notes, practice and revision, together in one place.')

def page_header(title, subtitle):
    st.markdown('<div class="sr-eyebrow">Your learning workspace</div>', unsafe_allow_html=True)
    st.title(title)
    st.write(subtitle)
    st.divider()

def empty_state(title, description):
    st.markdown(f'<div class="sr-empty"><strong>{escape(title)}</strong><span class="sr-muted">{escape(description)}</span></div>', unsafe_allow_html=True)

def activity_row(title, detail):
    st.markdown(f'<div class="sr-row"><strong>{escape(str(title))}</strong><small>{escape(str(detail))}</small></div>', unsafe_allow_html=True)



