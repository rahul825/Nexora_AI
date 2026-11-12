"""Chat history storage: sessions and their messages, kept in a local SQLite file.

SQLite ships with Python, so there is nothing to install. Every function opens its own
short connection, which keeps it safe to call from FastAPI's worker threads.
"""
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "chat_history.db"
SOURCES = ("document", "database")


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL,
                source     TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role       TEXT NOT NULL,          -- 'user' or 'assistant'
                content    TEXT NOT NULL,
                is_error   INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
        """)


def list_sessions() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT s.*, (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS message_count "
            "FROM sessions s ORDER BY s.updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def create_session(source: str = "document", title: str = "New chat") -> dict:
    now = _now()
    session = {"id": uuid.uuid4().hex, "title": title, "source": source,
               "created_at": now, "updated_at": now}
    with _conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title, source, created_at, updated_at) "
            "VALUES (:id, :title, :source, :created_at, :updated_at)", session)
    return {**session, "message_count": 0}


def get_session(session_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        messages = conn.execute(
            "SELECT id, role, content, is_error, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()
    return {**dict(row), "messages": [{**dict(m), "is_error": bool(m["is_error"])} for m in messages]}


def update_session(session_id: str, title: str | None = None, source: str | None = None) -> dict | None:
    with _conn() as conn:
        if title is not None:
            conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
        if source is not None:
            conn.execute("UPDATE sessions SET source = ? WHERE id = ?", (source, session_id))
    return get_session(session_id)


def delete_session(session_id: str) -> bool:
    with _conn() as conn:
        return conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,)).rowcount > 0


def add_message(session_id: str, role: str, content: str, is_error: bool = False) -> dict:
    now = _now()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (session_id, role, content, is_error, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, int(is_error), now))
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    return {"id": cur.lastrowid, "role": role, "content": content, "is_error": is_error, "created_at": now}
