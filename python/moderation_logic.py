"""
Pure moderation logic -- no network, no timers, no globals. Mirrors
node/moderation-logic.js function-for-function. The bot layer owns its
own banned-word list and thresholds (config, not hardcoded here) and
supplies the message history; this module only decides what to do
with it.
"""

import re
import time
import uuid


def _escape_regexp(text):
    return re.escape(text)


def contains_banned_word(text, banned_words):
    """Whole-word, case-insensitive match against any entry in `banned_words`."""
    normalized = text.lower()
    return any(
        re.search(rf"\b{_escape_regexp(word.lower())}\b", normalized)
        for word in banned_words
    )


def is_flooding(timestamps, max_messages=5, window_ms=10_000):
    """
    True if the most recent `max_messages` timestamps (including the
    one just sent) all landed within `window_ms` of each other -- i.e.
    the user posted that many messages faster than the window allows.
    """
    if len(timestamps) < max_messages:
        return False
    recent = timestamps[-max_messages:]
    return recent[-1] - recent[0] < window_ms


def evaluate_message(text, timestamp, recent_timestamps=None, banned_words=None, flood_options=None):
    """
    Combines the banned-word and flood checks into one verdict for an
    incoming message. Banned words take priority (delete on sight);
    flooding recommends a mute; otherwise no action.
    """
    recent_timestamps = recent_timestamps or []
    banned_words = banned_words or []
    flood_options = flood_options or {}

    if contains_banned_word(text, banned_words):
        return {"action": "delete", "reason": "mot-interdit"}
    if is_flooding([*recent_timestamps, timestamp], **flood_options):
        return {"action": "mute", "reason": "flood"}
    return {"action": "none", "reason": None}


def _default_id_generator():
    return str(uuid.uuid4())


def add_warning(warnings, user_id, moderator_id, reason, now=None, id_generator=_default_id_generator):
    now = now if now is not None else time.time()
    return [*warnings, {"id": id_generator(), "user_id": user_id, "moderator_id": moderator_id, "reason": reason, "at": now}]


def warning_count(warnings, user_id):
    return sum(1 for w in warnings if w["user_id"] == user_id)


def recommended_action(count, thresholds=None):
    """
    What a moderator should do once a user hits N warnings. Mute at
    `thresholds["mute"]`, kick at `thresholds["kick"]` and beyond
    ("kick" wins over "mute" once both thresholds are met).
    """
    thresholds = thresholds or {"mute": 3, "kick": 5}
    if count >= thresholds["kick"]:
        return "kick"
    if count >= thresholds["mute"]:
        return "mute"
    return "none"
