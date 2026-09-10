import streamlit as st
from utils.auth import require_login
from utils.ui import setup_ui, page_header
from utils import database as db
from utils.study import activate_note, input_changed, content_identity, persist
from utils.gemini_helper import generate_summary, generate_keywords, LearningError, MAX_NOTE_CHARS

st.set_page_config(page_title='SmartRecall · Study library', page_icon='📚', layout='wide')
setup_ui()
require_login()
page_header('Your study library', 'Add a topic once. Return to its notes, practice, and progress whenever you need it.')
notes = db.list_notes(st.session_state.user_id)
left, right = st.columns([1, 2], gap='large')
with left:
    with st.container(border=True):
        st.subheader('Saved notes')
        query = st.text_input('Find a subject or file', placeholder='Search your library')
        filtered = [n for n in notes if query.casefold() in (n['subject']+' '+n['file_name']).casefold()]
        if filtered:
            selected = st.selectbox('Choose a note', filtered, format_func=lambda n:f"{n['subject']} · {n['file_name']} (#{n['id']})")
            if st.button('Open selected note', use_container_width=True):
                activate_note(st.session_state.user_id, selected['id'])
                st.session_state.pop('_input_identity', None)
                st.session_state['upload_version'] = st.session_state.get('upload_version',0)+1
                st.rerun()
        else:
            st.caption('No matching notes yet. Add your first topic on the right.')
        if st.session_state.get('active_note_id'):
            st.caption(f"ACTIVE · {st.session_state.get('file_name', '')}")
            st.page_link('pages/2_Flashcards.py', label='Practise flashcards →')
            st.page_link('pages/3_Quiz.py', label='Take a quiz →')
with right:
    with st.expander('Add study material', expanded=not st.session_state.get('active_note_id')):
        version = st.session_state.get('upload_version',0)
        mode = st.radio('Input type', ['Upload PDF or TXT','Paste text'], horizontal=True, key=f'input_mode_{version}')
        subject = st.text_input('Subject', placeholder='For example: Database fundamentals', key=f'input_subject_{version}', max_chars=120)
        content, filename = b'', ''
        if mode == 'Upload PDF or TXT':
            uploaded = st.file_uploader('Choose study notes', type=['pdf','txt'], key=f'input_file_{version}', max_upload_size=10)
            if uploaded:
                content, filename = uploaded.getvalue(), uploaded.name
        else:
            filename = st.text_input('Note title', value='My study notes', key=f'input_title_{version}', max_chars=120) + '.txt'
            content = st.text_area('Paste your notes', height=180, max_chars=MAX_NOTE_CHARS, key=f'input_text_{version}').encode('utf-8')
        # A newly selected document must not show the previous document's results.
        if content:
            input_changed(st.session_state, content_identity(subject, filename, content))
        st.caption('Up to 10 MB per file and 40,000 extracted characters. Scanned PDFs need OCR before upload.')
        if st.button('Save and open notes', type='primary', disabled=not content):
            try:
                if not subject.strip():
                    raise ValueError('Enter a subject first.')
                if len(content) > 10*1024*1024:
                    raise ValueError('Choose a file smaller than 10 MB.')
                with st.spinner('Reading and saving your notes…'):
                    if mode == 'Upload PDF or TXT' and filename.lower().endswith('.pdf'):
                        from utils.pdf_reader import extract_text_from_pdf
                        text = extract_text_from_pdf(uploaded)
                    else:
                        text = content.decode('utf-8-sig')
                    if len(text.strip()) < 80:
                        raise ValueError('Add at least 80 characters of readable study text. Scanned PDFs need OCR first.')
                    if len(text) > MAX_NOTE_CHARS:
                        raise ValueError('Split this document into smaller topics of at most 40,000 characters.')
                    note_id = db.save_note(st.session_state.user_id, subject.strip(), filename, text)
                    activate_note(st.session_state.user_id, note_id)
                    st.session_state['upload_version'] = version+1
                    st.session_state.pop('_input_identity', None)
                st.rerun()
            except UnicodeDecodeError:
                st.error('Save your text file using UTF-8 encoding and upload it again.')
            except ValueError as error:
                st.error(str(error))
            except Exception:
                st.error('Could not read or save these notes. Check that the file is readable and try again.')
    if st.session_state.get('active_note_id'):
        note = db.get_note(st.session_state.user_id, st.session_state.active_note_id)
        st.subheader(note['subject'])
        st.caption(note['file_name'])
        summary_tab, source_tab, history_tab = st.tabs(['Summary & concepts','Original notes','Quiz history'])
        with summary_tab:
            if st.session_state.get('summary'):
                st.markdown(st.session_state.summary)
                st.download_button('Download summary', st.session_state.summary, file_name='study_summary.md', mime='text/markdown')
            if st.button('Regenerate summary' if st.session_state.get('summary') else 'Generate summary', type='primary'):
                try:
                    with st.spinner('Creating your summary…'):
                        persist('summary', generate_summary(note['extracted_text']))
                    st.rerun()
                except LearningError as error:
                    st.error(str(error))
                except Exception:
                    st.error('Could not save the summary. Please retry.')
            st.subheader('Key concepts')
            if st.session_state.get('keywords'):
                st.write(' · '.join(st.session_state.keywords))
            if st.button('Refresh key concepts' if st.session_state.get('keywords') else 'Extract key concepts'):
                try:
                    with st.spinner('Finding the important concepts…'):
                        persist('keywords', generate_keywords(note['extracted_text']))
                    st.rerun()
                except LearningError as error:
                    st.error(str(error))
                except Exception:
                    st.error('Could not save key concepts. Please retry.')
        with source_tab:
            st.text_area('Saved text', note['extracted_text'], height=350, disabled=True)
        with history_tab:
            history = db.quiz_history(st.session_state.user_id, note['id'])
            if history:
                import json
                for attempt in history[:20]:
                    with st.expander(f"{attempt['score']:g}% · {attempt['attempted_at']}"):
                        details = json.loads(attempt['details'] or '[]')
                        for item in details:
                            st.write(item['question'])
                            st.caption(f"Your answer: {item['selected']} · Correct answer: {item['answer']}")
                            st.write(item.get('explanation',''))
                        if not details:
                            st.caption('This older attempt has a score only.')
            else:
                st.info('Complete a quiz for this note to build your history.')
    else:
        st.info('Save a new topic or open a note from your library to begin.')
