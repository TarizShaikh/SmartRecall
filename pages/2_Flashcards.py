import streamlit as st

from utils.gemini_helper import generate_flashcards
from utils.auth import require_login

st.set_page_config(page_title='SmartRecall', page_icon='🧠', layout='wide')
from utils.ui import setup_ui, page_header
setup_ui()
require_login()

page_header('Flashcards', 'Practise key concepts from your uploaded notes with active recall.')


# --------------------------------------------------
# Check for uploaded notes
# --------------------------------------------------

if not st.session_state.get("extracted_text"):

    st.info(
        "No study notes are currently loaded. "
        "Go to **Study Notes**, upload a PDF, and then return here."
    )

else:

    st.success(
        f"Notes loaded: "
        f"{st.session_state.get('file_name', 'Uploaded PDF')}"
    )


    # --------------------------------------------------
    # Generate Flashcards
    # --------------------------------------------------

    if st.button(
        "Generate Flashcards"
    ):

        try:

            with st.spinner(
                "SmartRecall is creating flashcards..."
            ):

                flashcards = generate_flashcards(
                    st.session_state.extracted_text
                )


            st.session_state.flashcards = flashcards


        except Exception as error:

            st.error(
                f"Could not generate flashcards: {error}"
            )


    # --------------------------------------------------
    # Display Flashcards
    # --------------------------------------------------

    if st.session_state.get("flashcards"):

        st.divider()

        st.subheader(
            "AI Flashcards"
        )

        st.markdown(
            st.session_state.flashcards
        )
