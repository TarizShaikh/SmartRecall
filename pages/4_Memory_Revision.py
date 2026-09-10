
import streamlit as st

from datetime import datetime

from utils.memory_engine import (
    calculate_retention,
    get_revision_date
)

from utils.auth import require_login

from utils.database import (
    get_latest_note,
    save_revision_task
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

page_header('Memory & revision', 'Understand your estimated retention and plan your next revision.')


# --------------------------------------------------
# Check Study Material
# --------------------------------------------------

latest_note = get_latest_note(
    st.session_state.user_id
)


if not latest_note:

    st.info(
        "No saved study material found. "
        "Go to **Study Notes** and save your notes first."
    )

    st.stop()


# --------------------------------------------------
# Note Information
# --------------------------------------------------

note_id = latest_note[0]
subject_name = latest_note[1]
file_name = latest_note[2]
created_at = latest_note[3]


st.success(
    f"Study material loaded: **{file_name}**"
)

st.write(
    f"**Subject:** {subject_name}"
)


# --------------------------------------------------
# Calculate Days Since Study
# --------------------------------------------------

try:

    saved_date = datetime.strptime(
        created_at,
        "%Y-%m-%d %H:%M:%S"
    ).date()

    today = datetime.now().date()

    days_since_study = (
        today - saved_date
    ).days

except Exception:

    days_since_study = 0


st.write(
    f"📅 **Days since study material was saved:** "
    f"{days_since_study} day(s)"
)


st.divider()


# --------------------------------------------------
# Quiz Score
# --------------------------------------------------

default_score = int(
    st.session_state.get(
        "last_quiz_score",
        70
    )
)

quiz_score = st.slider(
    "Quiz score (%)",
    min_value=0,
    max_value=100,
    value=default_score
)


# --------------------------------------------------
# Memory Retention Calculation
# --------------------------------------------------

retention = calculate_retention(
    days_since_study,
    quiz_score
)


# --------------------------------------------------
# Revision Date
# --------------------------------------------------

revision_date = get_revision_date(
    quiz_score
)


# --------------------------------------------------
# Display Main Metrics
# --------------------------------------------------

metric_1, metric_2 = st.columns(2)


with metric_1:

    st.metric(
        "Estimated retention",
        f"{retention}%"
    )


with metric_2:

    st.metric(
        "Recommended revision",
        revision_date.strftime(
            "%d %B %Y"
        )
    )


st.divider()


# --------------------------------------------------
# Retention Status
# --------------------------------------------------

st.subheader("🧠 Memory Status")


if retention >= 80:

    st.success(
        "Your estimated retention is high. "
        "Continue with spaced revision."
    )

elif retention >= 60:

    st.info(
        "Your memory is beginning to decline. "
        "Revision is recommended soon."
    )

elif retention >= 40:

    st.warning(
        "Your estimated retention is moderate. "
        "You should revise this topic."
    )

else:

    st.error(
        "Your estimated retention is low. "
        "Revision is strongly recommended."
    )


st.divider()


# --------------------------------------------------
# Save Revision Recommendation
# --------------------------------------------------

if st.button(
    "Save Revision Recommendation"
):

    try:

        revision_saved = save_revision_task(
            note_id,
            retention,
            revision_date.strftime(
                "%Y-%m-%d"
            )
        )

        if revision_saved:

            st.success(
                "Revision recommendation saved successfully!"
            )

        else:

            st.info(
                "A pending revision schedule already exists for this note."
            )

    except Exception as error:

        st.error(
            f"Could not save revision recommendation: {error}"
        )


st.divider()


# --------------------------------------------------
# Retention Over Time
# --------------------------------------------------

st.subheader(
    "📈 Retention Over Time"
)


import pandas as pd

chart_data = pd.DataFrame({

    "Day": list(range(0, 31)),

    "Retention (%)": [

        calculate_retention(
            day,
            quiz_score
        )

        for day in range(0, 31)
    ]

}).set_index("Day")


st.line_chart(
    chart_data
)


st.caption(
    "The retention estimate is based on the current quiz score "
    "and the number of days since the topic was studied."
)


st.divider()


# --------------------------------------------------
# Revision Schedule
# --------------------------------------------------

st.subheader(
    "📅 Revision Schedule"
)

st.write(
    f"**Subject:** {subject_name}"
)

st.write(
    f"**Retention:** {retention}%"
)

st.write(
    f"**Recommended revision date:** "
    f"{revision_date.strftime('%d %B %Y')}"
)

st.info(
    "Regular revision helps strengthen memory "
    "and reduce forgetting over time."
)


