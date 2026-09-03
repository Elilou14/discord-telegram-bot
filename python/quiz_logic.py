"""
Pure quiz logic -- no network, no timers, no globals. Mirrors
node/quiz-logic.js function-for-function. A session is a plain dict;
every function takes one in and returns a new one (or derived data)
out, which is what makes it testable with plain unittest regardless
of which chat platform is driving it.
"""

import random
import time


def _shuffle(items, rng):
    copy = list(items)
    for i in range(len(copy) - 1, 0, -1):
        j = int(rng() * (i + 1))
        copy[i], copy[j] = copy[j], copy[i]
    return copy


def pick_questions(bank, count, category=None, rng=random.random):
    """`count` random questions from `bank`, no repeats, optionally filtered by category."""
    pool = [q for q in bank if q["category"] == category] if category else bank
    return _shuffle(pool, rng)[: min(count, len(pool))]


def start_session(channel_id, questions, now=None):
    return {
        "channel_id": channel_id,
        "questions": questions,
        "current_index": 0,
        "scores": {},
        "answered_by": {},
        "started_at": now if now is not None else time.time(),
    }


def current_question(session):
    if session["current_index"] < len(session["questions"]):
        return session["questions"][session["current_index"]]
    return None


def is_session_complete(session):
    return session["current_index"] >= len(session["questions"])


def submit_answer(session, user_id, choice_index):
    """
    Records `user_id`'s answer to the current question. Returns
    (session, status) where status is "correct", "incorrect",
    "already-answered" (a user only gets one try per question), or
    "complete" (no current question -- the session already ended).
    The session itself is returned unchanged for "already-answered"
    and "complete", same object, since nothing actually happened.
    """
    question = current_question(session)
    if question is None:
        return session, "complete"
    if user_id in session["answered_by"]:
        return session, "already-answered"

    correct = choice_index == question["answerIndex"]
    scores = dict(session["scores"])
    if correct:
        scores[user_id] = scores.get(user_id, 0) + 1

    next_session = {
        **session,
        "scores": scores,
        "answered_by": {**session["answered_by"], user_id: choice_index},
    }

    return next_session, ("correct" if correct else "incorrect")


def advance_question(session):
    """Moves to the next question, resetting who has answered."""
    return {**session, "current_index": session["current_index"] + 1, "answered_by": {}}


def standings(session):
    """[{user_id, score}], highest score first."""
    entries = [{"user_id": user_id, "score": score} for user_id, score in session["scores"].items()]
    return sorted(entries, key=lambda e: e["score"], reverse=True)
