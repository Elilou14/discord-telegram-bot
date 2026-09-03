"""
SQLite persistence for reminders, using Python's built-in sqlite3
(no dependency). Kept separate from reminders_logic.py so the rules
stay testable without touching a database at all -- this module is
just plain load/save.
"""

import sqlite3


def open_store(path="reminders.sqlite"):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            guild_id TEXT,
            message TEXT NOT NULL,
            due_at REAL NOT NULL,
            created_at REAL NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    return conn


def _row_to_reminder(row):
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "channel_id": row["channel_id"],
        "guild_id": row["guild_id"],
        "message": row["message"],
        "due_at": row["due_at"],
        "created_at": row["created_at"],
        "sent": bool(row["sent"]),
    }


def insert_reminder(conn, reminder):
    conn.execute(
        """INSERT INTO reminders (id, user_id, channel_id, guild_id, message, due_at, created_at, sent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            reminder["id"],
            reminder["user_id"],
            reminder["channel_id"],
            reminder["guild_id"],
            reminder["message"],
            reminder["due_at"],
            reminder["created_at"],
            1 if reminder["sent"] else 0,
        ),
    )
    conn.commit()


def load_all_reminders(conn):
    rows = conn.execute("SELECT * FROM reminders").fetchall()
    return [_row_to_reminder(row) for row in rows]


def mark_reminder_sent(conn, reminder_id):
    conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()


def delete_reminder(conn, reminder_id):
    conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
