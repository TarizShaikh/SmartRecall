import streamlit as st

from utils.gemini_helper import generate_quiz
from utils.auth import require_login
from utils.database import (
    save_quiz_attempt,
    get_latest_note
)


# --------------------------------------------------
# Authentication
# --------------------------------------------------

st.set_page_config(page_title='SmartRecall', page_icon='🧠', layout='wide')
from utils.ui import setup_ui, page_header
setup_ui()
require_login()


# --------------------------------------------------
# Page Header
# --------------------------------------------------

page_header('Practice quiz', 'Find out what has stuck with a quiz built from your study notes.')


# --------------------------------------------------
# Check Study Material
# --------------------------------------------------

if not st.session_state.get("extracted_text"):

    st.info(
        "No study notes are currently loaded. "
        "Go to **Study Notes**, upload a PDF, "
        "and then return here."
    )

else:

    st.success(
        f"Notes loaded: "
        f"{st.session_state.get('file_name', 'Uploaded PDF')}"
    )


    # --------------------------------------------------
    # Generate Quiz
    # --------------------------------------------------

    if st.button("Generate MCQ Quiz"):

        try:

            with st.spinner(
                "SmartRecall is creating your MCQ quiz..."
            ):

                st.session_state.quiz_questions = generate_quiz(
                    st.session_state.extracted_text
                )

            # Clear previous answers
            for number in range(10):

                answer_key = f"answer_{number}"

                if answer_key in st.session_state:

                    del st.session_state[answer_key]

            st.rerun()

        except Exception as error:

            st.error(
                f"Could not generate quiz: {error}"
            )


    # --------------------------------------------------
    # Display Quiz
    # --------------------------------------------------

    if st.session_state.get("quiz_questions"):

        st.divider()

        st.header("AI-Generated MCQ Quiz")


        with st.form("mcq_quiz_form"):

            selected_answers = []


            for index, question_data in enumerate(
                st.session_state.quiz_questions
            ):

                question_number = index + 1

                answer = st.radio(
                    f"{question_number}. "
                    f"{question_data['question']}",

                    question_data["options"],

                    index=None,

                    key=f"answer_{index}"
                )

                selected_answers.append(answer)


            submit_quiz = st.form_submit_button(
                "Submit Quiz"
            )


        # --------------------------------------------------
        # Evaluate Quiz
        # --------------------------------------------------

        if submit_quiz:

            correct_answers = 0


            for index, question_data in enumerate(
                st.session_state.quiz_questions
            ):

                if (
                    selected_answers[index]
                    == question_data["answer"]
                ):

                    correct_answers += 1


            total_questions = len(
                st.session_state.quiz_questions
            )


            score = round(
                (
                    correct_answers
                    / total_questions
                ) * 100,
                1
            )


            # Save score in session
            st.session_state.last_quiz_score = score


            # --------------------------------------------------
            # Save Quiz Attempt to Database
            # --------------------------------------------------

            try:

                latest_note = get_latest_note(
                    st.session_state.user_id
                )

                if latest_note:

                    note_id = latest_note[0]

                    save_quiz_attempt(
                        note_id,
                        score
                    )

            except Exception as error:

                st.warning(
                    f"Quiz result could not be saved: {error}"
                )


            # --------------------------------------------------
            # Display Result
            # --------------------------------------------------

            st.success(
                f"Your score: {score}% "
                f"({correct_answers}/{total_questions})"
            )


            if score >= 85:

                st.success(
                    "Excellent performance! 🌟"
                )

            elif score >= 70:

                st.info(
                    "Good performance! Keep revising regularly. 👍"
                )

            elif score >= 50:

                st.warning(
                    "You have a basic understanding. "
                    "More revision is recommended."
                )

            else:

                st.error(
                    "You should revise this topic before "
                    "attempting another quiz."
                )


            # --------------------------------------------------
            # Correct Answers
            # --------------------------------------------------

            with st.expander(
                "View correct answers"
            ):

                for index, question_data in enumerate(
                    st.session_state.quiz_questions
                ):

                    st.write(
                        f"{index + 1}. "
                        f"{question_data['answer']}"
                    )
