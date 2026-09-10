"""Owned study records, SQLite storage, and backward-compatible migrations."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

BASE_DIRECTORY = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.getenv('SMARTRECALL_DATABASE_PATH', str(BASE_DIRECTORY / 'data' / 'smartrecall.db')))
PASSWORD_ROUNDS = 600_000


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=15)
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA busy_timeout=15000')
    return connection


def sql(connection, statement, parameters=()):
    return connection.execute(statement, parameters)


@contextmanager
def transaction(write=False):
    connection = get_connection()
    try:
        if write:
            connection.execute('BEGIN IMMEDIATE')
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def initialize_database():
    identity = 'INTEGER PRIMARY KEY AUTOINCREMENT'
    with transaction(write=True) as c:
        statements = [
            f'CREATE TABLE IF NOT EXISTS users (id {identity}, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)',
            f'CREATE TABLE IF NOT EXISTS subjects (id {identity}, user_id INTEGER NOT NULL REFERENCES users(id), name TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)',
            f'CREATE TABLE IF NOT EXISTS notes (id {identity}, subject_id INTEGER REFERENCES subjects(id), file_name TEXT NOT NULL, extracted_text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)',
            f'CREATE TABLE IF NOT EXISTS quiz_attempts (id {identity}, note_id INTEGER REFERENCES notes(id), score REAL NOT NULL, confidence INTEGER, attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)',
            f"CREATE TABLE IF NOT EXISTS revision_tasks (id {identity}, note_id INTEGER REFERENCES notes(id), retention_score REAL NOT NULL, revision_date TEXT NOT NULL, status TEXT DEFAULT 'Pending')",
        ]
        for statement in statements:
            sql(c, statement)
        additions = {
            'notes': {'last_studied_at': 'TEXT'},
            'quiz_attempts': {'attempt_token': 'TEXT', 'details': 'TEXT'},
            'revision_tasks': {'completed_at': 'TEXT'},
        }
        for table, columns in additions.items():
            present = {r[1] for r in sql(c, f'PRAGMA table_info({table})').fetchall()}
            for column, kind in columns.items():
                if column not in present:
                    sql(c, f'ALTER TABLE {table} ADD COLUMN {column} {kind}')
        sql(c, 'CREATE TABLE IF NOT EXISTS learning_material (note_id INTEGER NOT NULL REFERENCES notes(id), kind TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(note_id, kind))')
        for name, expression in [
            ('idx_subject_user', 'subjects(user_id)'), ('idx_note_subject', 'notes(subject_id)'),
            ('idx_quiz_note', 'quiz_attempts(note_id, attempted_at)'), ('idx_revision_note', 'revision_tasks(note_id, status, revision_date)')]:
            sql(c, f'CREATE INDEX IF NOT EXISTS {name} ON {expression}')
        sql(c, 'CREATE UNIQUE INDEX IF NOT EXISTS idx_attempt_token ON quiz_attempts(attempt_token)')


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), PASSWORD_ROUNDS).hex()
    return f'pbkdf2_sha256${PASSWORD_ROUNDS}${salt}${digest}'


def verify_password(password, stored):
    if stored.startswith('pbkdf2_sha256$'):
        try:
            _, rounds, salt, expected = stored.split('$')
            rounds = int(rounds)
            if not 100_000 <= rounds <= 2_000_000:
                return False
            actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), rounds).hex()
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)


def register_user(username, password):
    username = username.strip()
    if not 3 <= len(username) <= 60:
        raise ValueError('Choose a username between 3 and 60 characters.')
    if not 8 <= len(password) <= 256:
        raise ValueError('Choose a password between 8 and 256 characters.')
    password_hash = hash_password(password)
    with transaction(write=True) as c:
        result = sql(c, 'INSERT INTO users(username,password_hash) VALUES (?,?) ON CONFLICT(username) DO NOTHING RETURNING id', (username, password_hash)).fetchone()
        return bool(result)


def authenticate_user(username, password):
    if len(password) > 256:
        return None
    with transaction() as c:
        user = sql(c, 'SELECT id,username,password_hash FROM users WHERE username=?', (username.strip(),)).fetchone()
    if not user or not verify_password(password, user[2]):
        return None
    if not user[2].startswith('pbkdf2_sha256$'):
        upgraded = hash_password(password)
        with transaction(write=True) as c:
            sql(c, 'UPDATE users SET password_hash=? WHERE id=? AND password_hash=?', (upgraded, user[0], user[2]))
    return user[:2]


def owned_note(c, user_id, note_id, lock=False):
    statement = 'SELECT n.id FROM notes n JOIN subjects s ON s.id=n.subject_id WHERE n.id=? AND s.user_id=?'
    if not sql(c, statement, (note_id, user_id)).fetchone():
        raise ValueError('That study note is not available in your account.')


def save_note(user_id, subject_name, file_name, extracted_text):
    if not subject_name.strip() or not extracted_text.strip():
        raise ValueError('A subject and readable notes are required.')
    with transaction(write=True) as c:
        subject = sql(c, 'SELECT id FROM subjects WHERE user_id=? AND name=?', (user_id, subject_name.strip())).fetchone()
        subject_id = subject[0] if subject else sql(c, 'INSERT INTO subjects(user_id,name) VALUES (?,?) RETURNING id', (user_id, subject_name.strip())).fetchone()[0]
        existing = sql(c, 'SELECT id FROM notes WHERE subject_id=? AND file_name=? AND extracted_text=? ORDER BY id DESC LIMIT 1', (subject_id, file_name, extracted_text)).fetchone()
        if existing:
            return existing[0]
        return sql(c, 'INSERT INTO notes(subject_id,file_name,extracted_text,last_studied_at) VALUES (?,?,?,?) RETURNING id', (subject_id, file_name, extracted_text, now())).fetchone()[0]


def records(cursor):
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def list_notes(user_id):
    with transaction() as c:
        return records(sql(c, 'SELECT n.id,s.name AS subject,n.file_name,n.created_at FROM notes n JOIN subjects s ON s.id=n.subject_id WHERE s.user_id=? ORDER BY n.id DESC', (user_id,)))


def get_note(user_id, note_id):
    with transaction() as c:
        owned_note(c, user_id, note_id)
        return records(sql(c, 'SELECT n.*,s.name AS subject FROM notes n JOIN subjects s ON s.id=n.subject_id WHERE n.id=?', (note_id,)))[0]


def get_material(user_id, note_id):
    with transaction() as c:
        owned_note(c, user_id, note_id)
        return {kind: json.loads(payload) for kind, payload in sql(c, 'SELECT kind,payload FROM learning_material WHERE note_id=?', (note_id,)).fetchall()}


def save_material(user_id, note_id, kind, payload):
    if kind not in ('summary', 'flashcards', 'quiz', 'keywords'):
        raise ValueError('Unsupported learning material.')
    with transaction(write=True) as c:
        owned_note(c, user_id, note_id)
        sql(c, 'INSERT INTO learning_material(note_id,kind,payload,updated_at) VALUES (?,?,?,?) ON CONFLICT(note_id,kind) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at', (note_id, kind, json.dumps(payload), now()))


def save_quiz_attempt(user_id, note_id, score, attempt_token, details=None):
    if not 0 <= score <= 100 or not attempt_token:
        raise ValueError('Invalid quiz result.')
    with transaction(write=True) as c:
        owned_note(c, user_id, note_id, lock=True)
        inserted = sql(c, 'INSERT INTO quiz_attempts(note_id,score,attempt_token,details) VALUES (?,?,?,?) ON CONFLICT(attempt_token) DO NOTHING RETURNING id', (note_id, score, attempt_token, json.dumps(details or []))).fetchone()
        if inserted:
            sql(c, 'UPDATE notes SET last_studied_at=? WHERE id=?', (now(), note_id))
        return bool(inserted)


def quiz_history(user_id, note_id):
    with transaction() as c:
        owned_note(c, user_id, note_id)
        return records(sql(c, 'SELECT id,score,attempted_at,details FROM quiz_attempts WHERE note_id=? ORDER BY id DESC', (note_id,)))


def save_revision_task(user_id, note_id, retention_score, revision_date):
    from datetime import date
    date.fromisoformat(revision_date)
    with transaction(write=True) as c:
        owned_note(c, user_id, note_id, lock=True)
        if sql(c, "SELECT id FROM revision_tasks WHERE note_id=? AND status='Pending'", (note_id,)).fetchone():
            return False
        sql(c, 'INSERT INTO revision_tasks(note_id,retention_score,revision_date,status) VALUES (?,?,?,?)', (note_id, retention_score, revision_date, 'Pending'))
        return True


def complete_revision(user_id, task_id, score):
    from utils.memory_engine import get_revision_date
    if not 0 <= score <= 100:
        raise ValueError('Choose a recall score between 0 and 100.')
    with transaction(write=True) as c:
        task = sql(c, 'SELECT note_id FROM revision_tasks WHERE id=?', (task_id,)).fetchone()
        if not task:
            raise ValueError('Revision not found.')
        owned_note(c, user_id, task[0], lock=True)
        updated = sql(c, "UPDATE revision_tasks SET status='Completed',completed_at=? WHERE id=? AND status='Pending'", (now(), task_id)).rowcount
        if not updated:
            return False
        sql(c, 'UPDATE notes SET last_studied_at=? WHERE id=?', (now(), task[0]))
        # One pending task remains even if legacy data contains duplicate schedules.
        if not sql(c, "SELECT id FROM revision_tasks WHERE note_id=? AND status='Pending'", (task[0],)).fetchone():
            sql(c, 'INSERT INTO revision_tasks(note_id,retention_score,revision_date,status) VALUES (?,?,?,?)', (task[0], 100, get_revision_date(score).isoformat(), 'Pending'))
        return True


def list_revisions(user_id):
    with transaction() as c:
        return records(sql(c, 'SELECT rt.*,s.name AS subject,n.file_name FROM revision_tasks rt JOIN notes n ON n.id=rt.note_id JOIN subjects s ON s.id=n.subject_id WHERE s.user_id=? ORDER BY rt.revision_date,rt.id', (user_id,)))


def get_dashboard_statistics(user_id):
    with transaction() as c:
        notes = sql(c, 'SELECT COUNT(*) FROM notes n JOIN subjects s ON s.id=n.subject_id WHERE s.user_id=?', (user_id,)).fetchone()[0]
        quizzes, average = sql(c, 'SELECT COUNT(*),AVG(q.score) FROM quiz_attempts q JOIN notes n ON n.id=q.note_id JOIN subjects s ON s.id=n.subject_id WHERE s.user_id=?', (user_id,)).fetchone()
        pending, upcoming = sql(c, "SELECT COUNT(*),MIN(r.revision_date) FROM revision_tasks r JOIN notes n ON n.id=r.note_id JOIN subjects s ON s.id=n.subject_id WHERE s.user_id=? AND r.status='Pending'", (user_id,)).fetchone()
    return dict(notes=notes, quizzes=quizzes, average_score=round(average or 0, 1), pending_revisions=pending, next_revision=upcoming)


def get_recent_notes(user_id, limit=5):
    return [(n['subject'], n['file_name'], n['created_at']) for n in list_notes(user_id)[:limit]]


def get_recent_quiz_attempts(user_id, limit=5):
    with transaction() as c:
        return sql(c, 'SELECT s.name,q.score,q.attempted_at FROM quiz_attempts q JOIN notes n ON n.id=q.note_id JOIN subjects s ON s.id=n.subject_id WHERE s.user_id=? ORDER BY q.id DESC LIMIT ?', (user_id, limit)).fetchall()


def get_upcoming_revisions(user_id, limit=5):
    return [(r['subject'],r['retention_score'],r['revision_date'],r['status']) for r in list_revisions(user_id) if r['status']=='Pending'][:limit]
