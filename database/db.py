"""
database/db.py  — FUNDAAZ

Supports two modes automatically:
  LOCAL (your computer):   SQLite  → fundaaz.db
  PRODUCTION (Render):     PostgreSQL → Supabase

Decided by DATABASE_URL environment variable.
If DATABASE_URL exists → PostgreSQL
If DATABASE_URL missing → SQLite
"""

import sqlite3
import hashlib
import os
import logging #....
from flask import g
import psycopg2

log = logging.getLogger('fundaaz.db') #........

DB_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fundaaz.db')
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Render gives postgres:// but psycopg2 needs postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

USE_POSTGRES = bool(DATABASE_URL)


def hash_pwd(pwd: str) -> str:
    return hashlib.sha256((pwd + '_fz_salt').encode()).hexdigest()


# ── Connection ────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        if USE_POSTGRES:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
            conn.autocommit = False
            g.db = conn
        else:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')
            conn.execute('PRAGMA journal_mode = WAL')
            g.db = conn
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ── Universal query helper ────────────────────────────────────────

class _Row:
    """Wraps a psycopg2 RealDictRow to behave like sqlite3.Row (bracket access)."""
    def __init__(self, d):
        self._d = dict(d) if d else {}
    def __getitem__(self, key):
        return self._d[key]
    def __contains__(self, key):
        return key in self._d
    def keys(self):
        return self._d.keys()
    def get(self, key, default=None):
        return self._d.get(key, default)


class _Cursor:
    """
    Wraps psycopg2 cursor to look like sqlite3 cursor.
    Converts ? placeholders to %s and returns _Row objects.
    """
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        row = self._cur.fetchone()
        return _Row(row) if row else None

    def fetchall(self):
        return [_Row(r) for r in self._cur.fetchall()]

    def __iter__(self):
        for row in self._cur:
            yield _Row(row)


def _pg_query(query, params=()):
    """Convert SQLite query to PostgreSQL and execute."""
    import psycopg2.extras
    db  = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    q   = query.replace('?', '%s')
    cur.execute(q, params)
    return _Cursor(cur)


def db_execute(query, params=()):
    """
    Use this everywhere instead of db.execute() directly.
    Works for both SQLite and PostgreSQL transparently.
    """
    if USE_POSTGRES:
        return _pg_query(query, params)
    else:
        return get_db().execute(query, params)


def db_commit():
    get_db().commit()


# ── Schema initialisation ─────────────────────────────────────────

def init_db():
    if USE_POSTGRES:
        _init_postgres()
    else:
        _init_sqlite()


def _init_postgres():
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    cur  = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS admin (
        id       SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS students (
        id             SERIAL PRIMARY KEY,
        name           TEXT NOT NULL,
        class          TEXT NOT NULL,
        batch          TEXT NOT NULL,
        subjects       TEXT,
        parent_name    TEXT,
        parent_contact TEXT,
        login_id       TEXT UNIQUE NOT NULL,
        password       TEXT NOT NULL,
        created_at     TIMESTAMP DEFAULT NOW()
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS tests (
        id          SERIAL PRIMARY KEY,
        code        TEXT UNIQUE NOT NULL,
        subject     TEXT NOT NULL,
        total_marks INTEGER NOT NULL,
        class       TEXT NOT NULL,
        batch       TEXT NOT NULL,
        date        TEXT NOT NULL,
        chapter     TEXT,
        topic       TEXT,
        created_at  TIMESTAMP DEFAULT NOW()
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS test_results (
        id         SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL REFERENCES students(id),
        test_id    INTEGER NOT NULL REFERENCES tests(id),
        marks      INTEGER NOT NULL,
        entered_at TIMESTAMP DEFAULT NOW()
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS notices (
        id            SERIAL PRIMARY KEY,
        type          TEXT NOT NULL DEFAULT 'text',
        title         TEXT NOT NULL,
        content       TEXT,
        image_path    TEXT,
        is_active     INTEGER NOT NULL DEFAULT 1,
        display_order INTEGER NOT NULL DEFAULT 0,
        created_at    TIMESTAMP DEFAULT NOW(),
        updated_at    TIMESTAMP DEFAULT NOW()
    )''')

    conn.commit()

    # Seed admin only if table is empty
    cur.execute('SELECT id FROM admin LIMIT 1')
    if not cur.fetchone():
        cur.execute('INSERT INTO admin (username, password) VALUES (%s, %s)',
                    ('admin', hash_pwd('admin123')))
        conn.commit()
        log.info('Admin account created in PostgreSQL')

    cur.close()
    conn.close()
    log.info('PostgreSQL (Supabase) tables ready')


def _init_sqlite():
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
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            type          TEXT NOT NULL DEFAULT 'text',
            title         TEXT NOT NULL,
            content       TEXT,
            image_path    TEXT,
            is_active     INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Migrations
    cols = [r[1] for r in db.execute('PRAGMA table_info(tests)').fetchall()]
    if 'chapter' not in cols:
        db.execute('ALTER TABLE tests ADD COLUMN chapter TEXT')
    if 'topic' not in cols:
        db.execute('ALTER TABLE tests ADD COLUMN topic TEXT')

    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if 'notices' not in tables:
        db.execute('''CREATE TABLE notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT 'text', title TEXT NOT NULL,
            content TEXT, image_path TEXT, is_active INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    db.commit()

    if not db.execute('SELECT id FROM admin LIMIT 1').fetchone():
        db.execute('INSERT INTO admin (username, password) VALUES (?,?)',
                   ('admin', hash_pwd('admin123')))
        db.commit()

    if not db.execute('SELECT id FROM students LIMIT 1').fetchone():
        _seed_demo(db)
        db.commit()

    db.close()
    log.info('SQLite database ready (local)')


def _seed_demo(db):
    """
    students = [
        ('Aarav Sharma','10','2024-25','Mathematics,Science,English,Hindi,SST',
         'Ramesh Sharma','9876543210','aarav01',hash_pwd('pass123')),
        ('Priya Verma', '10','2024-25','Mathematics,Science,English,Hindi,SST',
         'Suresh Verma', '9123456789','priya01',hash_pwd('pass123')),
        ('Rajan Patel', '9', '2024-25','Mathematics,Science,English,Hindi',
         'Dinesh Patel', '9988776655','rajan01',hash_pwd('pass123')),
    ]
    for s in students:
        db.execute('''INSERT INTO students
            (name,class,batch,subjects,parent_name,parent_contact,login_id,password)
            VALUES (?,?,?,?,?,?,?,?)''', s)
    tests = [
        ('MATH-T01','Mathematics',100,'10','2024-25','2025-01-10','Algebra','Linear Equations'),
        ('SCI-T01', 'Science',    100,'10','2024-25','2025-01-17','Physics','Laws of Motion'),
        ('ENG-T01', 'English',     50,'10','2024-25','2025-02-05',None,None),
        ('MATH-T02','Mathematics',100,'10','2024-25','2025-02-20','Algebra','Quadratic Equations'),
        ('SCI-T02', 'Science',    100,'10','2024-25','2025-03-01','Physics','Work and Energy'),
    ]
    for t in tests:
        db.execute('''INSERT INTO tests
            (code,subject,total_marks,class,batch,date,chapter,topic)
            VALUES (?,?,?,?,?,?,?,?)''', t)
    for r in [(1,1,88),(1,2,76),(1,3,44),(1,4,92),(1,5,81),
              (2,1,95),(2,2,88),(2,3,48),(3,1,70)]:
        db.execute('INSERT INTO test_results (student_id,test_id,marks) VALUES (?,?,?)', r)
"""
    pass
