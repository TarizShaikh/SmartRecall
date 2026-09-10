import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from utils import database as db
from utils.gemini_helper import validate_quiz, validate_flashcards, LearningError, _request
from utils.quiz_engine import evaluate_quiz
from utils.study import input_changed
from utils.memory_engine import calculate_retention

QUESTIONS = [dict(question=f'What is concept {i}?',options=['A','B','C','D'],answer='A',explanation='The notes define this concept as A.') for i in range(5)]
CARDS = [dict(question=f'Concept {i}?',answer=f'Definition {i}') for i in range(5)]

class StudyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=db.DATABASE_PATH
        db.DATABASE_PATH=Path(self.tmp.name)/'nested'/'test.db'
        db.initialize_database()
        with db.transaction(write=True) as c:
            self.user=db.sql(c,"INSERT INTO users(username,password_hash) VALUES ('alice','test') RETURNING id").fetchone()[0]
            self.other=db.sql(c,"INSERT INTO users(username,password_hash) VALUES ('bob','test') RETURNING id").fetchone()[0]
        self.note=db.save_note(self.user,'Biology','one.txt','Biology notes '*15)
        self.newer=db.save_note(self.user,'Networks','two.txt','Networks notes '*15)

    def tearDown(self):
        db.DATABASE_PATH=self.old
        self.tmp.cleanup()

    def test_results_use_selected_note_and_submission_is_idempotent(self):
        self.assertTrue(db.save_quiz_attempt(self.user,self.note,80,'same-token',[]))
        self.assertFalse(db.save_quiz_attempt(self.user,self.note,80,'same-token',[]))
        self.assertEqual(len(db.quiz_history(self.user,self.note)),1)
        self.assertEqual(db.quiz_history(self.user,self.newer),[])
        self.assertEqual(db.get_dashboard_statistics(self.user)['quizzes'],1)

    def test_owner_is_checked_on_reads_and_writes(self):
        for action in [lambda:db.get_note(self.other,self.note),lambda:db.save_material(self.other,self.note,'summary','x'),lambda:db.quiz_history(self.other,self.note),lambda:db.save_quiz_attempt(self.other,self.note,90,'unauthorized'),lambda:db.save_revision_task(self.other,self.note,80,date.today().isoformat())]:
            with self.assertRaises(ValueError):action()
        self.assertEqual(db.list_notes(self.other),[])

    def test_material_reopens_and_duplicate_notes_are_not_inserted(self):
        db.save_material(self.user,self.note,'flashcards',CARDS)
        self.assertEqual(db.get_material(self.user,self.note)['flashcards'],CARDS)
        self.assertEqual(db.save_note(self.user,'Biology','one.txt','Biology notes '*15),self.note)
        self.assertEqual(len(db.list_notes(self.user)),2)

    def test_review_completion_is_atomic_and_owned(self):
        self.assertTrue(db.save_revision_task(self.user,self.note,60,date.today().isoformat()))
        self.assertFalse(db.save_revision_task(self.user,self.note,60,date.today().isoformat()))
        task=db.list_revisions(self.user)[0]
        with self.assertRaises(ValueError):db.complete_revision(self.other,task['id'],80)
        self.assertTrue(db.complete_revision(self.user,task['id'],90))
        self.assertFalse(db.complete_revision(self.user,task['id'],90))
        revisions=db.list_revisions(self.user)
        self.assertEqual(sum(r['status']=='Pending' for r in revisions),1)
        self.assertEqual(sum(r['status']=='Completed' for r in revisions),1)
        self.assertEqual([r['revision_date'] for r in revisions if r['status']=='Pending'],[(date.today()+timedelta(days=7)).isoformat()])

    def test_hashing_and_legacy_migration(self):
        a=db.hash_password('StrongPassword123')
        b=db.hash_password('StrongPassword123')
        self.assertNotEqual(a,b)
        self.assertTrue(db.verify_password('StrongPassword123',a))
        self.assertFalse(db.verify_password('wrong',a))
        legacy=hashlib.sha256(b'oldpass').hexdigest()
        with db.transaction(write=True) as c:db.sql(c,'UPDATE users SET password_hash=? WHERE id=?',(legacy,self.user))
        self.assertIsNotNone(db.authenticate_user('alice','oldpass'))
        with db.transaction() as c:stored=db.sql(c,'SELECT password_hash FROM users WHERE id=?',(self.user,)).fetchone()[0]
        self.assertTrue(stored.startswith('pbkdf2_sha256$'))
        self.assertIsNone(db.authenticate_user('alice','wrong'))

    def test_existing_schema_migrates_without_data_loss(self):
        original=db.DATABASE_PATH
        db.DATABASE_PATH=Path(self.tmp.name)/'legacy.db'
        try:
            with sqlite3.connect(db.DATABASE_PATH) as c:
                c.executescript("""
                    CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password_hash TEXT,created_at TEXT);
                    CREATE TABLE subjects(id INTEGER PRIMARY KEY,user_id INTEGER,name TEXT,created_at TEXT);
                    CREATE TABLE notes(id INTEGER PRIMARY KEY,subject_id INTEGER,file_name TEXT,extracted_text TEXT,created_at TEXT);
                    CREATE TABLE quiz_attempts(id INTEGER PRIMARY KEY,note_id INTEGER,score REAL,confidence INTEGER,attempted_at TEXT);
                    CREATE TABLE revision_tasks(id INTEGER PRIMARY KEY,note_id INTEGER,retention_score REAL,revision_date TEXT,status TEXT);
                    INSERT INTO users VALUES (1,'legacy','hash','2026-01-01');
                    INSERT INTO subjects VALUES (1,1,'Biology','2026-01-01');
                    INSERT INTO notes VALUES (1,1,'old.txt','Retained text','2026-01-01');
                    INSERT INTO quiz_attempts VALUES (1,1,70,NULL,'2026-01-01');
                """)
            c.close()
            db.initialize_database()
            c.close()
            db.initialize_database()
            self.assertEqual(db.get_note(1,1)['extracted_text'],'Retained text')
            self.assertEqual(db.quiz_history(1,1)[0]['score'],70)
            db.save_material(1,1,'summary','New summary')
            self.assertEqual(db.get_material(1,1)['summary'],'New summary')
        finally:
            db.DATABASE_PATH=original

class LogicTests(unittest.TestCase):
    def test_new_upload_clears_previous_results(self):
        state={'_input_identity':'old','active_note_id':4,'summary':'old','flashcards':CARDS,'quiz_result':{},'answer_1':'A','logged_in':True,'username':'alice'}
        self.assertTrue(input_changed(state,'new'))
        self.assertNotIn('active_note_id',state)
        self.assertNotIn('summary',state)
        self.assertNotIn('answer_1',state)
        self.assertTrue(state['logged_in'])
        self.assertFalse(input_changed(state,'new'))

    def test_incomplete_and_invalid_quizzes_are_rejected(self):
        with self.assertRaises(ValueError):evaluate_quiz(QUESTIONS,['A',None,'A','A','A'])
        with self.assertRaises(LearningError):validate_quiz([])
        broken=json.loads(json.dumps(QUESTIONS));broken[0]['answer']='Z'
        with self.assertRaises(LearningError):validate_quiz(broken)
        broken=json.loads(json.dumps(QUESTIONS));broken[0]['options']=['A','A','B','C']
        with self.assertRaises(LearningError):validate_quiz(broken)
        self.assertEqual(evaluate_quiz(QUESTIONS,['A','B','A','A','A'])['score'],80)
        self.assertEqual(validate_flashcards(CARDS),CARDS)

    def test_retention_boundaries_and_decay(self):
        self.assertEqual(calculate_retention(0,0),100)
        self.assertGreater(calculate_retention(10,90),calculate_retention(10,40))
        self.assertLess(calculate_retention(10,90),calculate_retention(1,90))
        self.assertGreaterEqual(calculate_retention(1000,0),0)

    def test_error_messages_do_not_disclose_credentials(self):
        class FakeClient:
            @property
            def models(self):return self
            def generate_content(self,**kwargs):raise RuntimeError('credential-secret-here')
        with patch.dict(os.environ,{'GEMINI_API_KEY':'private-key'}),patch('utils.gemini_helper._client',return_value=FakeClient()):
            with self.assertRaises(LearningError) as caught:_request('Study notes '*20,'Summarize')
        self.assertNotIn('credential-secret-here',str(caught.exception))
        self.assertNotIn('private-key',str(caught.exception))

if __name__=='__main__':unittest.main()

