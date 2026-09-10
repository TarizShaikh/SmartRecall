import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from utils import database as db
from test_study_workflow import QUESTIONS,CARDS

class PageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=db.DATABASE_PATH
        db.DATABASE_PATH=Path(self.tmp.name)/'app.db'
        db.initialize_database()
        with db.transaction(write=True) as c:
            self.user=db.sql(c,"INSERT INTO users(username,password_hash) VALUES ('tester','unused') RETURNING id").fetchone()[0]
        self.note=db.save_note(self.user,'Biology','Biology.txt','Cells are the basic units of living organisms. '*10)
        db.save_material(self.user,self.note,'quiz',QUESTIONS)
        db.save_material(self.user,self.note,'flashcards',CARDS)

    def tearDown(self):
        db.DATABASE_PATH=self.old
        self.tmp.cleanup()

    def page(self,path):
        app=AppTest.from_file('app.py',default_timeout=30).run()
        if path != 'app.py': app.switch_page(path)
        state=dict(logged_in=True,user_id=self.user,username='tester',active_note_id=self.note,
            extracted_text='Cells are the basic units of living organisms. '*10, file_name='Biology.txt',
            subject_name='Biology',flashcards=CARDS,quiz_questions=QUESTIONS,quiz_token='page-test')
        for key,value in state.items(): app.session_state[key]=value
        app.run()
        self.assertFalse(app.exception,app.exception)
        return app

    def test_library_reopens_saved_material(self):
        app=self.page('pages/1_Study_Notes.py')
        next(b for b in app.button if b.label=='Open selected note').click().run()
        self.assertFalse(app.exception,app.exception)
        self.assertEqual(app.session_state['active_note_id'],self.note)
        self.assertEqual(app.session_state['flashcards'],CARDS)

    def test_pasted_text_creates_and_activates_note(self):
        app=self.page('pages/1_Study_Notes.py')
        next(r for r in app.radio if r.label=='Input type').set_value('Paste text').run()
        next(t for t in app.text_input if t.label=='Subject').set_value('Networking')
        next(t for t in app.text_area if t.label=='Paste your notes').set_value('A router forwards packets between networks. '*10).run()
        self.assertNotIn('active_note_id',app.session_state)
        next(b for b in app.button if b.label=='Save and open notes').click().run()
        self.assertFalse(app.exception,app.exception)
        self.assertNotEqual(app.session_state['active_note_id'],self.note)
        self.assertEqual(app.session_state['quiz_questions'],[])

    def test_flashcard_reveal_and_next(self):
        app=self.page('pages/2_Flashcards.py')
        next(b for b in app.button if b.label=='Reveal answer').click().run()
        self.assertTrue(app.session_state['card_revealed'])
        next(b for b in app.button if b.label=='Remembered ✓').click().run()
        self.assertEqual(app.session_state['card_index'],1)
        self.assertFalse(app.session_state['card_revealed'])
        self.assertFalse(app.exception,app.exception)

    def test_quiz_feedback_persists_once(self):
        app=self.page('pages/3_Quiz.py')
        next(b for b in app.button if b.label=='Submit quiz').click().run()
        self.assertTrue(app.warning)
        for radio in app.radio:radio.set_value('A')
        next(b for b in app.button if b.label=='Submit quiz').click().run()
        self.assertFalse(app.exception,app.exception)
        self.assertEqual(app.session_state['quiz_result']['score'],100)
        app.run()
        self.assertEqual(len(db.quiz_history(self.user,self.note)),1)

    def test_revision_and_profile_render(self):
        db.save_quiz_attempt(self.user,self.note,80,'revision-test',[])
        app=self.page('pages/4_Memory_Revision.py')
        next(b for b in app.button if b.label=='Save revision plan').click().run()
        next(b for b in app.button if b.label=='Mark completed & schedule next').click().run()
        self.assertFalse(app.exception,app.exception)
        self.assertEqual(len(db.list_revisions(self.user)),2)
        profile=self.page('pages/5_Profile.py')
        next(b for b in profile.button if b.label=='Prepare study export').click().run()
        exported=json.loads(profile.session_state['study_export'])
        self.assertEqual(len(exported['notes']),1)
        self.assertNotIn('password',profile.session_state['study_export'])

    def test_landing_and_dashboard(self):
        app=AppTest.from_file('app.py',default_timeout=30).run()
        self.assertFalse(app.exception,app.exception)
        self.assertEqual(len(app.text_input),5)
        app=self.page('app.py')
        self.assertEqual(len(app.metric),4)

if __name__=='__main__':unittest.main()


