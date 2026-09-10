"""Database access for Daily Goals.

Production uses Supabase Postgres (DATABASE_URL / SUPABASE_DB_URL). Locally, if
that URL is not set, a SQLite file is used so `py app.py` still works offline.
SQL in the app stays SQLite-shaped (`?` placeholders); Postgres gets `%s`.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from queue import Empty, Full, Queue

try:
    from psycopg.errors import UniqueViolation
except ImportError:
    UniqueViolation = None

INTEGRITY_ERRORS = (sqlite3.IntegrityError,)
if UniqueViolation is not None:
    INTEGRITY_ERRORS += (UniqueViolation,)

POSTGRES_SCHEMA = Path(__file__).parent / "supabase" / "migrations" / "001_daily_goals.sql"
MIGRATIONS_DIR = Path(__file__).parent / "supabase" / "migrations"


def _load_dotenv():
    path = Path(__file__).parent / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
USING_POSTGRES = bool(DATABASE_URL)

if os.environ.get("RENDER") and not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Running on Render without it means every account and "
        "goal is stored on disk that gets wiped on the next deploy. In the Supabase "
        "dashboard copy Project Settings → Database → URI (use the pooler URI, port "
        "6543, and add ?sslmode=require if it is missing) into Render's Environment "
        "tab as DATABASE_URL, then redeploy."
    )


class _Result:
    def __init__(self, rows):
        self.rows = rows


class _SqliteDB:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cur = self._conn.execute(sql, params)
        rows = []
        if cur.description:
            rows = cur.fetchall()
        self._conn.commit()
        return _Result(rows)

    def close(self):
        self._conn.close()


class _PostgresDB:
    def __init__(self, conn):
        self._conn = conn
        self._broken = False

    def execute(self, sql, params=()):
        pg_sql = sql.replace("?", "%s")
        try:
            with self._conn.cursor() as cur:
                cur.execute(pg_sql, params)
                rows = cur.fetchall() if cur.description else []
            return _Result(rows)
        except Exception as exc:
            if self._conn is None or self._conn.closed or type(exc).__name__ in {"OperationalError", "InterfaceError"}:
                self._broken = True
            raise

    def close(self):
        _release_pg(self._conn, broken=self._broken)
        self._conn = None


def _postgres_conninfo(url):
    if "sslmode=" not in url and "supabase.co" in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


# Opening TLS to Supabase on every Flask request is the main reason the UI
# waits on empty charts and study screens. Reuse a few connections per worker.
_PG_POOL_SIZE = max(1, min(8, int(os.environ.get("DB_POOL_SIZE", "4"))))
_pg_pool = None
_pg_pool_lock = threading.Lock()


class _PgPool:
    def __init__(self, size):
        self.size = size
        self.q = Queue(maxsize=size)
        self.created = 0
        self.lock = threading.Lock()

    def get(self):
        try:
            return self._alive(self.q.get_nowait())
        except Empty:
            pass
        with self.lock:
            if self.created < self.size:
                self.created += 1
                try:
                    return _new_pg_conn()
                except Exception:
                    self.created -= 1
                    raise
        return self._alive(self.q.get(timeout=12))

    def put(self, conn, broken=False):
        if conn is None:
            return
        if broken or conn.closed:
            self._drop(conn)
            return
        try:
            self.q.put_nowait(conn)
        except Full:
            self._drop(conn)

    def _alive(self, conn):
        if conn is not None and not conn.closed:
            return conn
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
        try:
            return _new_pg_conn()
        except Exception:
            with self.lock:
                self.created = max(0, self.created - 1)
            raise

    def _drop(self, conn):
        try:
            if conn is not None and not conn.closed:
                conn.close()
        except Exception:
            pass
        with self.lock:
            self.created = max(0, self.created - 1)


def _pg_pool_get():
    global _pg_pool
    if _pg_pool is None:
        with _pg_pool_lock:
            if _pg_pool is None:
                _pg_pool = _PgPool(_PG_POOL_SIZE)
    return _pg_pool


def _new_pg_conn():
    import psycopg
    from psycopg.rows import dict_row

    conn = psycopg.connect(
        _postgres_conninfo(DATABASE_URL),
        autocommit=True,
        row_factory=dict_row,
        prepare_threshold=None,
    )
    conn.execute("SET search_path TO daily_goals, public")
    return conn


def _release_pg(conn, broken=False):
    if not USING_POSTGRES:
        if conn is not None:
            conn.close()
        return
    _pg_pool_get().put(conn, broken=broken)


def connect_db():
    if USING_POSTGRES:
        return _PostgresDB(_pg_pool_get().get())

    path = os.environ.get("DB_PATH", "daily_goals.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return _SqliteDB(conn)


def query_one(db, sql, params=()):
    rows = db.execute(sql, params).rows
    return rows[0] if rows else None


def query_all(db, sql, params=()):
    return db.execute(sql, params).rows


def _init_sqlite(db):
    db.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL DEFAULT '',
            password_hash TEXT NOT NULL
        )"""
    )
    user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").rows}
    if "email" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_nocase ON users(username COLLATE NOCASE)"
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            text TEXT NOT NULL,
            sort_order INTEGER NOT NULL
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS completions (
            goal_id INTEGER NOT NULL REFERENCES goals(id),
            date TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (goal_id, date)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS synced_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            external_id TEXT NOT NULL,
            date TEXT NOT NULL,
            text TEXT NOT NULL,
            time TEXT NOT NULL DEFAULT '',
            task_type TEXT NOT NULL DEFAULT 'Task',
            done INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, external_id)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS synced_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            external_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            options_json TEXT NOT NULL DEFAULT '[]',
            example TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            due TEXT NOT NULL DEFAULT '0000-00-00',
            interval INTEGER NOT NULL DEFAULT 1,
            ease REAL NOT NULL DEFAULT 2.5,
            reps INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, external_id)
        )"""
    )
    card_columns = {row["name"] for row in db.execute("PRAGMA table_info(synced_cards)").rows}
    if "lapses" not in card_columns:
        db.execute("ALTER TABLE synced_cards ADD COLUMN lapses INTEGER NOT NULL DEFAULT 0")
    db.execute(
        """CREATE TABLE IF NOT EXISTS card_review_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            external_id TEXT NOT NULL,
            confidence INTEGER NOT NULL DEFAULT 3,
            reviewed_at TEXT NOT NULL
        )"""
    )
    review_columns = {row["name"] for row in db.execute("PRAGMA table_info(card_review_events)").rows}
    if "confidence" not in review_columns:
        db.execute("ALTER TABLE card_review_events ADD COLUMN confidence INTEGER NOT NULL DEFAULT 3")
        if "correct" in review_columns:
            db.execute("UPDATE card_review_events SET confidence = CASE WHEN correct = 1 THEN 3 ELSE 1 END")
    if "consumed" not in review_columns:
        db.execute("ALTER TABLE card_review_events ADD COLUMN consumed INTEGER NOT NULL DEFAULT 0")
    db.execute(
        """CREATE TABLE IF NOT EXISTS new_card_intro_state (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            date TEXT NOT NULL,
            ids_json TEXT NOT NULL DEFAULT '[]'
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS synced_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            external_id TEXT NOT NULL,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
            size_bytes INTEGER NOT NULL DEFAULT 0,
            content BLOB NOT NULL,
            UNIQUE(user_id, external_id)
        )"""
    )
    card_columns = {row["name"] for row in db.execute("PRAGMA table_info(synced_cards)").rows}
    if "queue" not in card_columns:
        db.execute("ALTER TABLE synced_cards ADD COLUMN queue INTEGER NOT NULL DEFAULT 0")
    if "due_at" not in card_columns:
        db.execute("ALTER TABLE synced_cards ADD COLUMN due_at TEXT NOT NULL DEFAULT ''")
    if "learn_step" not in card_columns:
        db.execute("ALTER TABLE synced_cards ADD COLUMN learn_step INTEGER NOT NULL DEFAULT 0")
    if "source" not in card_columns:
        db.execute("ALTER TABLE synced_cards ADD COLUMN source TEXT NOT NULL DEFAULT 'desktop'")
    db.execute("UPDATE synced_cards SET queue = 2 WHERE reps > 0 AND queue = 0")
    db.execute(
        """CREATE TABLE IF NOT EXISTS srs_settings (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            new_per_day INTEGER NOT NULL DEFAULT 20,
            reviews_per_day INTEGER NOT NULL DEFAULT 200,
            notify_enabled INTEGER NOT NULL DEFAULT 1,
            notify_hour INTEGER NOT NULL DEFAULT 9
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS srs_day_counts (
            user_id INTEGER NOT NULL REFERENCES users(id),
            date TEXT NOT NULL,
            new_shown INTEGER NOT NULL DEFAULT 0,
            reviews_shown INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, date)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS lesson_progress (
            user_id INTEGER NOT NULL REFERENCES users(id),
            course_slug TEXT NOT NULL,
            lesson_slug TEXT NOT NULL,
            grammar_done INTEGER NOT NULL DEFAULT 0,
            cards_added INTEGER NOT NULL DEFAULT 0,
            exercises_correct INTEGER NOT NULL DEFAULT 0,
            exercises_total INTEGER NOT NULL DEFAULT 0,
            answers_json TEXT NOT NULL DEFAULT '{}',
            completed INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (user_id, course_slug, lesson_slug)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS user_prefs (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            lang TEXT NOT NULL DEFAULT 'en'
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_goals_user_id ON goals(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_synced_tasks_user_date ON synced_tasks(user_id, date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_synced_cards_user_id ON synced_cards(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_lesson_progress_user_id ON lesson_progress(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_synced_books_user_id ON synced_books(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_completions_date ON completions(date)")
    db.execute(
        """CREATE TABLE IF NOT EXISTS book_highlights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            book_id INTEGER NOT NULL REFERENCES synced_books(id),
            start_offset INTEGER NOT NULL DEFAULT 0,
            end_offset INTEGER NOT NULL DEFAULT 0,
            color TEXT NOT NULL DEFAULT 'yellow',
            snippet TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT ''
        )"""
    )
    book_columns = {row["name"] for row in db.execute("PRAGMA table_info(synced_books)").rows}
    if "source" not in book_columns:
        db.execute("ALTER TABLE synced_books ADD COLUMN source TEXT NOT NULL DEFAULT 'desktop'")
    if "storage_key" not in book_columns:
        db.execute("ALTER TABLE synced_books ADD COLUMN storage_key TEXT NOT NULL DEFAULT ''")


def _split_sql(sql):
    statements = []
    buf = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buf).strip()
            if statement:
                statements.append(statement)
            buf = []
    leftover = "\n".join(buf).strip()
    if leftover:
        statements.append(leftover)
    return statements


def init_db():
    db = connect_db()
    try:
        if USING_POSTGRES:
            # Schema is applied via supabase/migrations (MCP / SQL editor), not by the
            # limited app role at process start.
            db.execute("SELECT 1 FROM users LIMIT 0")
        else:
            _init_sqlite(db)
    finally:
        db.close()
