import sqlite3
import hashlib
import os
import logging
from flask import g

log = logging.getLogger('fundaaz.db')

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fundaaz.db')

DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

USE_POSTGRES = bool(DATABASE_URL)


def hash_pwd(pwd: str) -> str:
    return hashlib.sha256((pwd + '_fz_salt').encode()).hexdigest()


def get_db():
    if 'db' not in g:
        if USE_POSTGRES:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=10, sslmode='require')
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


class _Row:
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


def db_execute(query, params=()):
    if USE_POSTGRES:
        import psycopg2.extras
        db  = get_db()
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query.replace('?', '%s'), params)
        return _Cursor(cur)
    else:
        return get_db().execute(query, params)


def db_commit():
    get_db().commit()


def init_db():
    if USE_POSTGRES:
        _init_postgres()
    else:
        _init_sqlite()


def _init_postgres():
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10, sslmode='require')
    cur  = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS admin (
        id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS students (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, class TEXT NOT NULL,
        batch TEXT NOT NULL, subjects TEXT, parent_name TEXT, parent_contact TEXT,
        login_id TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW())''')
    cur.execute('''CREATE TABLE IF NOT EXISTS tests (
        id SERIAL PRIMARY KEY, code TEXT UNIQUE NOT NULL, subject TEXT NOT NULL,
        total_marks INTEGER NOT NULL, class TEXT NOT NULL, batch TEXT NOT NULL,
        date TEXT NOT NULL, chapter TEXT, topic TEXT,
        created_at TIMESTAMP DEFAULT NOW())''')
    cur.execute('''CREATE TABLE IF NOT EXISTS test_results (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL REFERENCES students(id),
        test_id INTEGER NOT NULL REFERENCES tests(id),
        marks INTEGER NOT NULL, entered_at TIMESTAMP DEFAULT NOW())''')
    cur.execute('''CREATE TABLE IF NOT EXISTS notices (
        id SERIAL PRIMARY KEY, type TEXT NOT NULL DEFAULT 'text',
        title TEXT NOT NULL, content TEXT, image_path TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        display_order INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW())''')
    conn.commit()
    cur.execute('SELECT id FROM admin LIMIT 1')
    if not cur.fetchone():
        cur.execute('INSERT INTO admin (username, password) VALUES (%s, %s)',
                    ('admin', hash_pwd('admin123')))
        conn.commit()
    cur.close()
    conn.close()
    log.info('PostgreSQL ready')


def _init_sqlite():
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    db.execute('PRAGMA journal_mode = WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, class TEXT NOT NULL, batch TEXT NOT NULL,
            subjects TEXT, parent_name TEXT, parent_contact TEXT,
            login_id TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL, subject TEXT NOT NULL,
            total_marks INTEGER NOT NULL, class TEXT NOT NULL,
            batch TEXT NOT NULL, date TEXT NOT NULL, chapter TEXT, topic TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id),
            test_id INTEGER NOT NULL REFERENCES tests(id),
            marks INTEGER NOT NULL,
            entered_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT 'text', title TEXT NOT NULL,
            content TEXT, image_path TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);
    ''')
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
    log.info('SQLite ready')


def _seed_demo(db):
    pass
