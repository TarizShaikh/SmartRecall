import os
import sqlite3
import hashlib
from pathlib import Path


# --------------------------------------------------
# Database Configuration
# --------------------------------------------------

BASE_DIRECTORY = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.getenv("SMARTRECALL_DATABASE_PATH", str(BASE_DIRECTORY / "data" / "smartrecall.db")))


# --------------------------------------------------
# Database Connection
# --------------------------------------------------

def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


# --------------------------------------------------
# Initialize Database
# --------------------------------------------------

def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            file_name TEXT NOT NULL,
            extracted_text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER,
            score REAL NOT NULL,
            confidence INTEGER,
            attempted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (note_id) REFERENCES notes(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS revision_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER,
            retention_score REAL NOT NULL,
            revision_date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (note_id) REFERENCES notes(id)
        )
    """)

    connection.commit()
    connection.close()


# --------------------------------------------------
# Password Functions
# --------------------------------------------------

def hash_password(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()


# --------------------------------------------------
# User Registration
# --------------------------------------------------

def register_user(username, password):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        password_hash = hash_password(password)

        cursor.execute(
            """
            INSERT INTO users (
                username,
                password_hash
            )
            VALUES (?, ?)
            """,
            (
                username,
                password_hash
            )
        )

        connection.commit()

        return True

    except sqlite3.IntegrityError:

        return False

    finally:

        connection.close()


# --------------------------------------------------
# User Authentication
# --------------------------------------------------

def authenticate_user(username, password):

    connection = get_connection()
    cursor = connection.cursor()

    password_hash = hash_password(password)

    cursor.execute(
        """
        SELECT id, username
        FROM users
        WHERE username = ?
        AND password_hash = ?
        """,
        (
            username,
            password_hash
        )
    )

    user = cursor.fetchone()

    connection.close()

    return user


# --------------------------------------------------
# Save Notes
# --------------------------------------------------

def save_note(
    user_id,
    subject_name,
    file_name,
    extracted_text
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM subjects
        WHERE name = ?
        AND user_id = ?
        """,
        (
            subject_name,
            user_id
        )
    )

    subject = cursor.fetchone()

    if subject:

        subject_id = subject[0]

    else:

        cursor.execute(
            """
            INSERT INTO subjects (
                user_id,
                name
            )
            VALUES (?, ?)
            """,
            (
                user_id,
                subject_name
            )
        )

        subject_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO notes (
            subject_id,
            file_name,
            extracted_text
        )
        VALUES (?, ?, ?)
        """,
        (
            subject_id,
            file_name,
            extracted_text
        )
    )

    note_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return note_id


# --------------------------------------------------
# Get Latest Note
# --------------------------------------------------

def get_latest_note(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            n.id,
            s.name,
            n.file_name,
            n.created_at
        FROM notes n

        JOIN subjects s
        ON n.subject_id = s.id

        WHERE s.user_id = ?

        ORDER BY n.id DESC

        LIMIT 1
        """,
        (user_id,)
    )

    note = cursor.fetchone()

    connection.close()

    return note


# --------------------------------------------------
# Save Quiz Attempt
# --------------------------------------------------

def save_quiz_attempt(
    note_id,
    score,
    confidence=None
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO quiz_attempts (
            note_id,
            score,
            confidence
        )
        VALUES (?, ?, ?)
        """,
        (
            note_id,
            score,
            confidence
        )
    )

    connection.commit()
    connection.close()


# --------------------------------------------------
# Save Revision Task
# --------------------------------------------------

def save_revision_task(
    note_id,
    retention_score,
    revision_date
):

    connection = get_connection()
    cursor = connection.cursor()

    # A note should have only one active revision schedule at a time.
    cursor.execute(
        """
        SELECT id
        FROM revision_tasks
        WHERE note_id = ?
        AND status = 'Pending'
        LIMIT 1
        """,
        (note_id,)
    )

    existing_task = cursor.fetchone()

    if existing_task:

        connection.close()

        return False

    cursor.execute(
        """
        INSERT INTO revision_tasks (
            note_id,
            retention_score,
            revision_date,
            status
        )
        VALUES (?, ?, ?, 'Pending')
        """,
        (
            note_id,
            retention_score,
            revision_date
        )
    )

    connection.commit()
    connection.close()

    return True


# --------------------------------------------------
# Dashboard Statistics
# --------------------------------------------------

def get_dashboard_statistics(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    # Total notes
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM notes n

        JOIN subjects s
        ON n.subject_id = s.id

        WHERE s.user_id = ?
        """,
        (user_id,)
    )

    total_notes = cursor.fetchone()[0]


    # Total quizzes
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM quiz_attempts qa

        JOIN notes n
        ON qa.note_id = n.id

        JOIN subjects s
        ON n.subject_id = s.id

        WHERE s.user_id = ?
        """,
        (user_id,)
    )

    total_quizzes = cursor.fetchone()[0]


    # Average quiz score
    cursor.execute(
        """
        SELECT AVG(qa.score)
        FROM quiz_attempts qa

        JOIN notes n
        ON qa.note_id = n.id

        JOIN subjects s
        ON n.subject_id = s.id

        WHERE s.user_id = ?
        """,
        (user_id,)
    )

    average_score = cursor.fetchone()[0]

    if average_score is None:

        average_score = 0

    else:

        average_score = round(
            average_score,
            1
        )


    # Pending revisions
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM revision_tasks rt

        JOIN notes n
        ON rt.note_id = n.id

        JOIN subjects s
        ON n.subject_id = s.id

        WHERE s.user_id = ?
        AND rt.status = 'Pending'
        """,
        (user_id,)
    )

    pending_revisions = cursor.fetchone()[0]


    # Next revision
    cursor.execute(
        """
        SELECT MIN(rt.revision_date)
        FROM revision_tasks rt

        JOIN notes n
        ON rt.note_id = n.id

        JOIN subjects s
        ON n.subject_id = s.id

        WHERE s.user_id = ?
        AND rt.status = 'Pending'
        """,
        (user_id,)
    )

    next_revision = cursor.fetchone()[0]

    connection.close()

    return {
        "notes": total_notes,
        "quizzes": total_quizzes,
        "average_score": average_score,
        "pending_revisions": pending_revisions,
        "next_revision": next_revision
    }


# --------------------------------------------------
# Recent Notes
# --------------------------------------------------

def get_recent_notes(user_id, limit=5):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            s.name,
            n.file_name,
            n.created_at
        FROM notes n

        JOIN subjects s
        ON n.subject_id = s.id

        WHERE s.user_id = ?

        ORDER BY n.created_at DESC

        LIMIT ?
        """,
        (
            user_id,
            limit
        )
    )

    notes = cursor.fetchall()

    connection.close()

    return notes


# --------------------------------------------------
# Recent Quiz Attempts
# --------------------------------------------------

def get_recent_quiz_attempts(
    user_id,
    limit=5
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            s.name,
            qa.score,
            qa.attempted_at
        FROM quiz_attempts qa

        JOIN notes n
        ON qa.note_id = n.id

        JOIN subjects s
        ON n.subject_id = s.id

        WHERE s.user_id = ?

        ORDER BY qa.attempted_at DESC

        LIMIT ?
        """,
        (
            user_id,
            limit
        )
    )

    attempts = cursor.fetchall()

    connection.close()

    return attempts


# --------------------------------------------------
# Upcoming Revision Tasks
# --------------------------------------------------

def get_upcoming_revisions(
    user_id,
    limit=5
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            s.name,
            rt.retention_score,
            rt.revision_date,
            rt.status
        FROM revision_tasks rt

        JOIN notes n
        ON rt.note_id = n.id

        JOIN subjects s
        ON n.subject_id = s.id

        WHERE s.user_id = ?
        AND rt.status = 'Pending'

        ORDER BY rt.revision_date ASC

        LIMIT ?
        """,
        (
            user_id,
            limit
        )
    )

    revisions = cursor.fetchall()

    connection.close()

    return revisions

