import sqlite3
import hashlib
import os
from flask import g

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fundaaz.db')

def hash_pwd(pwd):
    return hashlib.sha256((pwd + '_fz_salt').encode()).hexdigest()

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
        g.db.execute('PRAGMA journal_mode = WAL')
    return g.db

def init_db():
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    db.execute('PRAGMA journal_mode = WAL')

    db.executescript('''
        CREATE TABLE IF NOT EXISTS admin (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS students (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            class          TEXT NOT NULL,
            batch          TEXT NOT NULL,
            subjects       TEXT,
            parent_name    TEXT,
            parent_contact TEXT,
            login_id       TEXT UNIQUE NOT NULL,
            password       TEXT NOT NULL,
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT UNIQUE NOT NULL,
            subject     TEXT NOT NULL,
            total_marks INTEGER NOT NULL,
            class       TEXT NOT NULL,
            batch       TEXT NOT NULL,
            date        TEXT NOT NULL,
            chapter     TEXT,
            topic       TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS test_results (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id),
            test_id    INTEGER NOT NULL REFERENCES tests(id),
            marks      INTEGER NOT NULL,
            entered_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS notices (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            type         TEXT NOT NULL DEFAULT 'text',
            title        TEXT NOT NULL,
            content      TEXT,
            image_path   TEXT,
            is_active    INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Migrate existing DB: add notices table if missing
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if 'notices' not in tables:
        db.execute('''CREATE TABLE notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT 'text',
            title TEXT NOT NULL,
            content TEXT,
            image_path TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        db.commit()

    # Migrate existing DB: add chapter/topic if missing
    cols = [r[1] for r in db.execute('PRAGMA table_info(tests)').fetchall()]
    if 'chapter' not in cols:
        db.execute('ALTER TABLE tests ADD COLUMN chapter TEXT')
    if 'topic' not in cols:
        db.execute('ALTER TABLE tests ADD COLUMN topic TEXT')
    db.commit()

    if not db.execute('SELECT id FROM admin LIMIT 1').fetchone():
        db.execute('INSERT INTO admin (username, password) VALUES (?,?)',
                   ('admin', hash_pwd('admin123')))
        db.commit()

    if not db.execute('SELECT id FROM students LIMIT 1').fetchone():
        _seed_demo(db)
        db.commit()

    db.close()

def _seed_demo(db):
    pass

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
