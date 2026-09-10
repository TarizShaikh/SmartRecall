import streamlit as st

from utils.database import save_note
from utils.gemini_helper import generate_summary
from utils.pdf_reader import extract_text_from_pdf
from utils.auth import require_login

st.set_page_config(page_title='SmartRecall', page_icon='🧠', layout='wide')
from utils.ui import setup_ui, page_header
setup_ui()
require_login()

page_header('Study notes', 'Upload a PDF, create a summary, and save it for your next session.')


# --------------------------------------------------
# Subject
# --------------------------------------------------

subject_name = st.text_input(
    "Subject name",
    placeholder="Example: Database Management Systems"
)


# --------------------------------------------------
# PDF Upload
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Choose a PDF file",
    type=["pdf"]
)


if uploaded_file is not None:

    try:

        # -----------------------------
        # Extract PDF text
        # -----------------------------

        with st.spinner(
            "Reading your PDF notes..."
        ):

            extracted_text = extract_text_from_pdf(
                uploaded_file
            )


        if extracted_text:

            st.success(
                "PDF read successfully!"
            )


            # Save extracted text in session
            # so other pages can use it later.

            st.session_state.extracted_text = extracted_text
            st.session_state.subject_name = subject_name
            st.session_state.file_name = uploaded_file.name


            # -----------------------------
            # Text Preview
            # -----------------------------

            st.subheader(
                "Extracted Text Preview"
            )

            st.text_area(
                "Text from your notes",
                extracted_text[:3000],
                height=300
            )


            st.divider()


            # -----------------------------
            # Generate Summary
            # -----------------------------

            if st.button(
                "Generate AI Summary"
            ):

                try:

                    with st.spinner(
                        "SmartRecall is creating your summary..."
                    ):

                        summary = generate_summary(
                            extracted_text
                        )


                    st.session_state.summary = summary


                except Exception as error:

                    st.error(
                        f"Could not generate summary: {error}"
                    )


            # -----------------------------
            # Display Summary
            # -----------------------------

            if "summary" in st.session_state:

                st.subheader(
                    "AI Study Summary"
                )

                st.markdown(
                    st.session_state.summary
                )


            st.divider()


            # -----------------------------
            # Save Notes
            # -----------------------------

            if st.button(
                "Save Notes"
            ):

                if subject_name.strip():

                    save_note(
                        st.session_state.user_id,
                        subject_name.strip(),
                        uploaded_file.name,
                        extracted_text
                    )

                    st.success(
                        "Your notes were saved successfully!"
                    )

                else:

                    st.warning(
                        "Please enter a subject name first."
                    )


        else:

            st.warning(
                "No readable text was found in this PDF."
            )


    except Exception as error:

        st.error(
            f"Could not read this PDF: {error}"
        )
