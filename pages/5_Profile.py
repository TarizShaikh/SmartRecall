import streamlit as st
from utils.auth import require_login

st.set_page_config(page_title='SmartRecall', page_icon='🧠', layout='wide')
from utils.ui import setup_ui, page_header
setup_ui()
require_login()

page_header('Your profile', 'Manage your SmartRecall account and learning workspace.')


# --------------------------------------------------
# User Information
# --------------------------------------------------

username = st.session_state.get(
    "username",
    "User"
)

user_id = st.session_state.get(
    "user_id",
    None
)


st.markdown("### 👤 Account Information")

st.write(
    f"**Username:** {username}"
)

st.write(
    f"**User ID:** {user_id}"
)


st.divider()


# --------------------------------------------------
# Application Information
# --------------------------------------------------

st.markdown("### 🧠 About SmartRecall")

st.write(
    "SmartRecall is an adaptive AI-based memory retention "
    "and revision assistant designed to help students study "
    "more effectively."
)

st.write(
    "It uses uploaded study notes, AI-generated learning "
    "material, quiz performance and a memory retention model "
    "to provide personalised revision support."
)


st.divider()


# --------------------------------------------------
# Logout
# --------------------------------------------------

st.markdown("### 🔐 Account")

if st.button("Logout"):

    st.session_state.pop('_pdf_text_cache', None)
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_id = None

    st.session_state.extracted_text = ""
    st.session_state.subject_name = ""
    st.session_state.file_name = ""
    st.session_state.summary = ""
    st.session_state.flashcards = ""
    st.session_state.quiz_questions = []

    st.switch_page("app.py")

