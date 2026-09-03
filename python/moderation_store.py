"""
SQLite persistence for moderation warnings, mirroring
reminders_store.py's shape: plain load/save, no business rules.
"""

import sqlite3


def open_moderation_store(path="moderation.sqlite"):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS warnings (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            moderator_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            at REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _row_to_warning(row):
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "moderator_id": row["moderator_id"],
        "reason": row["reason"],
        "at": row["at"],
    }


def insert_warning(conn, warning):
    conn.execute(
        "INSERT INTO warnings (id, user_id, moderator_id, reason, at) VALUES (?, ?, ?, ?, ?)",
        (warning["id"], warning["user_id"], warning["moderator_id"], warning["reason"], warning["at"]),
    )
    conn.commit()


def load_all_warnings(conn):
    rows = conn.execute("SELECT * FROM warnings").fetchall()
    return [_row_to_warning(row) for row in rows]
