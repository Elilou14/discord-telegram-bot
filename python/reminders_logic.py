"""
Pure reminders logic -- no network, no database, no globals. Mirrors
node/reminders-logic.js function-for-function (the design notes live
there); persistence lives in reminders_store.py.

Timestamps here are Python idiomatic: datetime for parsing, then
POSIX seconds (float, via .timestamp()) once stored on a reminder --
the two bots aren't required to agree on a wire format the way the
chess project's engines were, so each side just uses what's natural.
"""

import re
import uuid
from datetime import datetime, timedelta

_DURATION_RE = re.compile(r"^(\d+)(s|m|h|d)$")
_ABSOLUTE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})$")

_MULTIPLIERS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(text):
    """'10m', '2h', '1d', '45s' -> seconds. None if it doesn't match."""
    match = _DURATION_RE.match(text.strip())
    if not match:
        return None
    return int(match.group(1)) * _MULTIPLIERS[match.group(2)]


def parse_when(text, now=None):
    """A relative duration ("10m") or an absolute "YYYY-MM-DD HH:MM"."""
    now = now or datetime.now()
    trimmed = text.strip()

    duration = parse_duration(trimmed)
    if duration is not None:
        return now + timedelta(seconds=duration)

    match = _ABSOLUTE_RE.match(trimmed)
    if not match:
        return None

    year, month, day, hour, minute = (int(g) for g in match.groups())
    if not (1 <= month <= 12 and 1 <= day <= 31 and hour <= 23 and minute <= 59):
        return None

    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


def _default_id_generator():
    return str(uuid.uuid4())


def create_reminder(user_id, channel_id, message, when, guild_id=None, now=None, id_generator=_default_id_generator):
    """
    Validates and builds a new reminder. Raises ValueError on an
    empty message, an unparseable `when`, or a `when` already in the
    past -- these are user-input errors the bot layer should catch
    and show back to the user.
    """
    now = now or datetime.now()

    if not message or not message.strip():
        raise ValueError("Le message du rappel ne peut pas etre vide.")

    due_at = parse_when(when, now)
    if due_at is None:
        raise ValueError(f'Date ou duree invalide : "{when}" (ex: 10m, 2h, 1d, ou 2026-09-10 14:30)')
    if due_at <= now:
        raise ValueError("La date du rappel doit etre dans le futur.")

    return {
        "id": id_generator(),
        "user_id": user_id,
        "channel_id": channel_id,
        "guild_id": guild_id,
        "message": message.strip(),
        "due_at": due_at.timestamp(),
        "created_at": now.timestamp(),
        "sent": False,
    }


def active_reminders_for_user(reminders, user_id):
    """A user's own pending reminders, soonest first."""
    matching = [r for r in reminders if r["user_id"] == user_id and not r["sent"]]
    return sorted(matching, key=lambda r: r["due_at"])


def due_reminders(reminders, now=None):
    """Reminders whose time has come and haven't fired yet."""
    now = now or datetime.now()
    now_ts = now.timestamp()
    return [r for r in reminders if not r["sent"] and r["due_at"] <= now_ts]


def cancel_reminder(reminders, reminder_id, user_id):
    """No-op (same list object) if `reminder_id` isn't a pending reminder owned by `user_id`."""
    for i, r in enumerate(reminders):
        if r["id"] == reminder_id and r["user_id"] == user_id and not r["sent"]:
            return reminders[:i] + reminders[i + 1 :]
    return reminders


def mark_sent(reminders, reminder_id):
    return [dict(r, sent=True) if r["id"] == reminder_id else r for r in reminders]
