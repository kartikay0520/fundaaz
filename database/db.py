"""
database/db.py — FUNDAAZ

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
import logging
from flask import g
import psycopg2

log = logging.getLogger('fundaaz.db')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fundaaz.db')

# 🔥 IMPORTANT FIX: strip spaces (copy-paste issue safe)
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()

# Fix postgres:// → postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

USE_POSTGRES = bool(DATABASE_URL)


def hash_pwd(pwd: str) -> str:
    return hashlib.sha256((pwd + '_fz_salt').encode()).hexdigest()


# ── Connection ────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        if USE_POSTGRES:
            import psycopg2.extras

            # 🔥 FIX: sslmode required for Supabase
            conn = psycopg2.connect(
                DATABASE_URL,
                connect_timeout=10,
                sslmode="require"
            )
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
    """Wraps a psycopg2 RealDictRow to behave like sqlite3.Row"""
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
    """Wrap psycopg2 cursor like sqlite cursor"""

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
    """Convert SQLite query → PostgreSQL"""
    import psycopg2.extras

    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 🔥 convert ? → %s
    q = query.replace('?', '%s')

    cur.execute(q, params)
    return _Cursor(cur)


def db_execute(query, params=()):
    """Universal execute"""
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

    # 🔥 FIX: sslmode required here also
    conn = psycopg2.connect(
        DATABASE_URL,
        connect_timeout=10,
        sslmode="require"
    )
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS admin (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS students (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        class TEXT NOT NULL,
        batch TEXT NOT NULL,
        subjects TEXT,
        parent_name TEXT,
        parent_contact TEXT,
        login_id TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS tests (
        id SERIAL PRIMARY KEY,
        code TEXT UNIQUE NOT NULL,
        subject TEXT NOT NULL,
        total_marks INTEGER NOT NULL,
        class TEXT NOT NULL,
        batch TEXT NOT NULL,
        date TEXT NOT NULL,
        chapter TEXT,
        topic TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS test_results (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL REFERENCES students(id),
        test_id INTEGER NOT NULL REFERENCES tests(id),
        marks INTEGER NOT NULL,
        entered_at TIMESTAMP DEFAULT NOW()
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS notices (
        id SERIAL PRIMARY KEY,
        type TEXT NOT NULL DEFAULT 'text',
        title TEXT NOT NULL,
        content TEXT,
        image_path TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        display_order INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )''')

    conn.commit()

    # Seed admin
    cur.execute('SELECT id FROM admin LIMIT 1')
    if not cur.fetchone():
        cur.execute(
            'INSERT INTO admin (username, password) VALUES (%s, %s)',
            ('admin', hash_pwd('admin123'))
        )
        conn.commit()
        log.info('Admin created (PostgreSQL)')

    cur.close()
    conn.close()
    log.info('PostgreSQL (Supabase) ready')


def _init_sqlite():
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    db.execute('PRAGMA journal_mode = WAL')

    db.executescript('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class TEXT NOT NULL,
            batch TEXT NOT NULL,
            subjects TEXT,
            parent_name TEXT,
            parent_contact TEXT,
            login_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            subject TEXT NOT NULL,
            total_marks INTEGER NOT NULL,
            class TEXT NOT NULL,
            batch TEXT NOT NULL,
            date TEXT NOT NULL,
            chapter TEXT,
            topic TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id),
            test_id INTEGER NOT NULL REFERENCES tests(id),
            marks INTEGER NOT NULL,
            entered_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT 'text',
            title TEXT NOT NULL,
            content TEXT,
            image_path TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    db.commit()
    db.close()
    log.info('SQLite ready (local)')
