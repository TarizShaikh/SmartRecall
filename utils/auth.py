import streamlit as st
from utils.database import initialize_database


def require_login():
    if not st.session_state.get('logged_in',False):
        st.info('Sign in to access your learning workspace.')
        st.page_link('app.py',label='Go to sign in →')
        st.stop()
    if not st.session_state.get('_database_v2_initialized'):
        initialize_database()
        st.session_state['_database_v2_initialized'] = True
