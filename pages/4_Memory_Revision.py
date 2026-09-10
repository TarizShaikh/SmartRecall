import calendar
from datetime import date, datetime, timezone
from html import escape
import streamlit as st
from utils.auth import require_login
from utils.ui import setup_ui, page_header
from utils import database as db
from utils.study import activate_note
from utils.memory_engine import calculate_retention, get_revision_date

st.set_page_config(page_title='SmartRecall · Revision plan', page_icon='📅', layout='wide')
setup_ui()
require_login()
page_header('Memory & revision', 'Follow your plan, complete a review, and schedule the next session.')
notes = db.list_notes(st.session_state.user_id)
if not notes:
    st.info('Save your first study note to start planning revisions.')
    st.page_link('pages/1_Study_Notes.py', label='Open study library →')
    st.stop()
ids = [n['id'] for n in notes]
active = st.session_state.get('active_note_id')
selected = st.selectbox('Plan for a note', notes, index=ids.index(active) if active in ids else 0,
    format_func=lambda n:f"{n['subject']} · {n['file_name']} (#{n['id']})")
if st.session_state.get('active_note_id') != selected['id']:
    activate_note(st.session_state.user_id, selected['id'])
note = db.get_note(st.session_state.user_id, selected['id'])
history = db.quiz_history(st.session_state.user_id, note['id'])
latest_score = float(history[0]['score']) if history else None
anchor = str(note.get('last_studied_at') or note['created_at'])[:10]
days = max(0,(datetime.now(timezone.utc).date()-date.fromisoformat(anchor)).days)
summary, experiment = st.tabs(['Your recommendation','Explore the estimate'])
with summary:
    if latest_score is None:
        st.info('Take a quiz for this note to get a recommendation based on your result.')
        st.page_link('pages/3_Quiz.py', label='Open practice quiz →')
    else:
        retention = calculate_retention(days, latest_score)
        next_date = get_revision_date(latest_score)
        a,b,c = st.columns(3)
        a.metric('Latest quiz', f'{latest_score:g}%')
        b.metric('Estimated retention', f'{retention:g}%')
        c.metric('Next session if planned today', next_date.strftime('%d %b'))
        st.caption(f'{days} days since this note was last studied or reviewed. Dates use UTC.')
        if st.button('Save revision plan', type='primary'):
            if db.save_revision_task(st.session_state.user_id, note['id'], retention, next_date.isoformat()):
                st.success('Revision added to your calendar.')
            else:
                st.info('This note already has a pending session. Complete it below to schedule the next one.')
with experiment:
    simulated = st.slider('Try a quiz score', 0,100,int(latest_score if latest_score is not None else 70))
    import pandas as pd
    curve = pd.DataFrame({'Days since study':range(31),'Estimated retention (%)':[calculate_retention(d,simulated) for d in range(31)]}).set_index('Days since study')
    st.line_chart(curve, color='#B3A3FF')
    st.caption('This exploration does not change your results or revision plan.')
with st.expander('How this estimate works'):
    st.write('The estimate uses an exponential forgetting curve: retention = 100 × exp(-days / strength), where strength = 2 + 12 × quiz_score / 100.')
    st.write('Review intervals are 7 days for scores of 85% or higher, 4 days for 70–84%, 2 days for 50–69%, and 1 day below 50%. Completing a review restarts the study clock.')
    st.caption('These are transparent prototype rules, not a trained prediction model or a scientifically validated measurement of your memory. At day zero the estimate is 100%, regardless of score. Actual retention differs between people and topics.')

revisions = db.list_revisions(st.session_state.user_id)
pending = [r for r in revisions if r['status']=='Pending']
st.divider()
st.subheader('Revision calendar')
month = st.date_input('Choose a month', date.today(), key='calendar_month')
counts = {}
for r in pending:
    counts[r['revision_date']] = counts.get(r['revision_date'],0)+1
weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(month.year,month.month)
html = '<div style="overflow-x:auto"><table style="width:100%;table-layout:fixed;text-align:center"><caption>'+escape(month.strftime('%B %Y'))+'</caption><tr>'
html += ''.join('<th scope="col">'+day+'</th>' for day in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])+'</tr>'
for week in weeks:
    html += '<tr>'
    for day in week:
        count = counts.get(day.isoformat(),0)
        color = '#25213d' if count else '#181e2e'
        label = f'{day.day}' + (f'<br><small>{count} due</small>' if count else '')
        if day == date.today(): label += '<br><small>Today</small>'
        html += f'<td style="background:{color};padding:10px 3px;opacity:{1 if day.month==month.month else 0.4}">{label}</td>'
    html += '</tr>'
st.markdown(html+'</table></div>',unsafe_allow_html=True)
agenda, completed = st.tabs(['Upcoming & overdue','Completed reviews'])
with agenda:
    if not pending:
        st.caption('No pending reviews. Save a plan above after your first quiz.')
    for task in pending:
        due = date.fromisoformat(task['revision_date'])
        label = 'Overdue' if due<date.today() else 'Today' if due==date.today() else 'Upcoming'
        with st.container(border=True):
            st.subheader(f"{task['subject']} · {task['file_name']}")
            st.caption(f"{label} · {due.strftime('%d %b %Y')}")
            score = st.slider('How well did you recall this topic?',0,100,70,key=f"review_score_{task['id']}",help='A self-assessment used only to choose the next review interval; it is not recorded as a quiz result.')
            if st.button('Mark completed & schedule next',key=f"review_done_{task['id']}"):
                db.complete_revision(st.session_state.user_id,task['id'],score)
                st.rerun()
with completed:
    done = [r for r in revisions if r['status']=='Completed']
    for task in reversed(done):
        st.write(f"✓ {task['subject']} · {task['file_name']}")
        st.caption(f"Completed {task['completed_at']}")
    if not done:
        st.caption('Completed reviews will appear here.')

