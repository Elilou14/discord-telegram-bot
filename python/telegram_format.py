"""
Telegram message text + inline-keyboard builders. python-telegram-bot's
InlineKeyboardButton/InlineKeyboardMarkup are pure data structures --
building one doesn't touch the network -- so this whole module is
testable via `.to_dict()` without a live bot connection. Mirrors
node/discord-format.js, adapted to what Telegram actually offers (no
embeds, no native relative timestamps).
"""

from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CHOICE_LETTERS = ["A", "B", "C", "D"]


def build_quiz_message(question, index, total):
    lines = [f"Question {index + 1}/{total}", "", question["question"], ""]
    lines += [f"{CHOICE_LETTERS[i]}. {choice}" for i, choice in enumerate(question["choices"])]
    return "\n".join(lines)


def build_quiz_keyboard(question, session_id):
    buttons = [
        InlineKeyboardButton(CHOICE_LETTERS[i], callback_data=f"quiz:{session_id}:{i}")
        for i in range(len(question["choices"]))
    ]
    return InlineKeyboardMarkup([buttons])


def format_reminder_fired(reminder):
    return f"⏰ Rappel : {reminder['message']}"


def format_reminder_list(reminders):
    if not reminders:
        return "Vous n'avez aucun rappel actif."
    lines = []
    for i, r in enumerate(reminders):
        due = datetime.fromtimestamp(r["due_at"]).strftime("%Y-%m-%d %H:%M")
        lines.append(f"{i + 1}. {due} -- {r['message']} (id: {r['id'][:8]})")
    return "\n".join(lines)


def format_standings(standings_list, resolve_display_name):
    if not standings_list:
        return "Personne n'a encore marque de points."
    lines = []
    for i, s in enumerate(standings_list):
        points_word = "pt" if s["score"] == 1 else "pts"
        lines.append(f"{i + 1}. {resolve_display_name(s['user_id'])} -- {s['score']} {points_word}")
    return "\n".join(lines)
