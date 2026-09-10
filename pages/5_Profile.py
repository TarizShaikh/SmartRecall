import json
from datetime import datetime, timezone
import streamlit as st
from utils.auth import require_login
from utils.ui import setup_ui, page_header
from utils import database as db

st.set_page_config(page_title='SmartRecall · Profile', page_icon='👤',layout='wide')
setup_ui()
require_login()
page_header('Your profile','Your account, study records, and project information.')
with st.container(border=True):
    st.subheader(st.session_state.username)
    st.caption('Personal learning workspace')
    stats = db.get_dashboard_statistics(st.session_state.user_id)
    a,b,c = st.columns(3)
    a.metric('Saved notes',stats['notes'])
    b.metric('Quiz attempts',stats['quizzes'])
    c.metric('Pending reviews',stats['pending_revisions'])
with st.container(border=True):
    st.subheader('Keep a copy of your learning')
    st.caption('Export your notes, generated material, quiz history, and revision plan. The export does not contain passwords or API keys.')
    if st.button('Prepare study export'):
        user_id=st.session_state.user_id
        notes=[]
        for item in db.list_notes(user_id):
            note=db.get_note(user_id,item['id'])
            note['material']=db.get_material(user_id,item['id'])
            note['quiz_history']=db.quiz_history(user_id,item['id'])
            notes.append(note)
        st.session_state['study_export']=json.dumps({'format_version':1,'exported_at':datetime.now(timezone.utc).isoformat(),'notes':notes,'revisions':db.list_revisions(user_id)},indent=2,default=str)
    if st.session_state.get('study_export'):
        st.download_button('Download study records',st.session_state.study_export,'smartrecall_study_records.json','application/json')
    st.caption('This deployment uses local SQLite storage. Keep exports of important work; hosted local files may be lost when the service restarts or redeploys.')
with st.expander('About this project'):
    st.write('SmartRecall combines note-based AI summaries, key concepts, flashcards, quizzes, and a rule-based revision planner.')
    st.write('Memory retention is an illustrative estimate based on quiz score and elapsed time. It is not a validated measurement of memory or a trained prediction model.')
    st.caption('AI output can contain errors. Compare important details with your original notes.')
if st.button('Sign out'):
    st.session_state.clear()
    st.switch_page('app.py')
