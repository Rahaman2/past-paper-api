import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "waitlist.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the waitlist table if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                whatsapp TEXT NOT NULL,
                grade TEXT NOT NULL,
                subject TEXT NOT NULL,
                preference TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def insert_entry(name: str, whatsapp: str, grade: str, subject: str,
                 preference: str, email: Optional[str] = None) -> int:
    """Insert a waitlist entry and return the new row id."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO waitlist (name, whatsapp, grade, subject, preference, email)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, whatsapp, grade, subject, preference, email),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_entries() -> list[dict]:
    """Return all waitlist entries as a list of dicts, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM waitlist ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
