import streamlit as st
from utils.auth import require_login
from utils.ui import setup_ui, page_header
from utils.study import require_note, persist
from utils.gemini_helper import generate_flashcards, LearningError

st.set_page_config(page_title='SmartRecall · Flashcards', page_icon='🗂️', layout='wide')
setup_ui()
require_login()
page_header('Flashcards', 'Recall the answer first, then reveal it. Work through one idea at a time.')
note = require_note()
cards = st.session_state.get('flashcards', [])
if st.button('Generate new flashcards' if cards else 'Generate flashcards', type='primary'):
    try:
        with st.spinner('Creating five flashcards…'):
            persist('flashcards', generate_flashcards(note['extracted_text']))
        st.session_state.update(card_index=0, card_revealed=False, card_known=[])
        st.rerun()
    except LearningError as error:
        st.error(str(error))
    except Exception:
        st.error('Could not save flashcards. Please try again.')
if cards:
    index = st.session_state.get('card_index',0) % len(cards)
    known = st.session_state.get('card_known', [])
    st.progress((index+1)/len(cards), text=f'Card {index+1} of {len(cards)} · {len(known)} marked remembered')
    with st.container(border=True):
        st.caption('ACTIVE RECALL')
        st.subheader(cards[index]['question'])
        if st.session_state.get('card_revealed'):
            st.divider()
            st.write(cards[index]['answer'])
        elif st.button('Reveal answer', use_container_width=True):
            st.session_state.card_revealed = True
            st.rerun()
    previous, rating, following = st.columns(3)
    if previous.button('← Previous', use_container_width=True):
        st.session_state.update(card_index=(index-1)%len(cards), card_revealed=False)
        st.rerun()
    if rating.button('Remembered ✓', disabled=not st.session_state.get('card_revealed'), use_container_width=True):
        st.session_state.card_known = sorted(set(known+[index]))
        st.session_state.update(card_index=(index+1)%len(cards), card_revealed=False)
        st.rerun()
    if following.button('Next →', use_container_width=True):
        st.session_state.update(card_index=(index+1)%len(cards), card_revealed=False)
        st.rerun()
    if len(known)==len(cards):
        st.success('You have recalled every card in this session. Ready for a quiz?')
    st.page_link('pages/3_Quiz.py', label='Test yourself with a quiz →')
else:
    st.info('Generate a set of cards once; it will be saved with this note.')
