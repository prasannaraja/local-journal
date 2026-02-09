import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from journal.config import DB_PATH, DATA_DIR


@contextmanager
def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                raw_dump TEXT,
                mood TEXT,
                tags TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                messages TEXT NOT NULL,
                FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
            );
        """)
        conn.commit()


def save_entry(title: str, body: str, raw_dump: str, mood: str, tags: str,
               conversation: list[dict]) -> int:
    """Save a journal entry and its conversation. Returns the entry id."""
    with _connect() as conn:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO entries (title, body, raw_dump, mood, tags, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (title, body, raw_dump, mood, tags, now),
        )
        entry_id = cur.lastrowid
        conn.execute(
            "INSERT INTO conversations (entry_id, messages) VALUES (?, ?)",
            (entry_id, json.dumps(conversation)),
        )
        conn.commit()
        return entry_id


def get_entries() -> list[dict]:
    """List all entries (summary fields)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, mood, tags, created_at FROM entries ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_entry(entry_id: int) -> dict | None:
    """Get a full entry with its conversation."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return None
        entry = dict(row)
        conv = conn.execute(
            "SELECT messages FROM conversations WHERE entry_id = ?", (entry_id,)
        ).fetchone()
        entry["conversation"] = json.loads(conv["messages"]) if conv else []
        return entry


def delete_entry(entry_id: int) -> bool:
    """Delete an entry and its conversation. Returns True if found."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        conn.commit()
        return cur.rowcount > 0
