import streamlit as st


def require_login():
    if not st.session_state.get("logged_in", False):
        st.warning("Please login to access SmartRecall.")

        if st.button("Go to Login"):
            st.switch_page("app.py")

        st.stop()