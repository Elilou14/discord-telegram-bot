#!/usr/bin/env python3
"""
Telegram bot entry point: wires the Application to the pure logic
modules through a single shared, mutable `ctx` dict kept in
`application.bot_data` (in-memory state kept in sync with SQLite).
This file, commands.py and scheduler.py can't be exercised without a
real bot token -- they're built carefully on top of the fully-tested
core in *_logic.py / *_store.py / telegram_format.py.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from telegram import ChatPermissions
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from commands import (
    clear_command,
    mute_command,
    quiz_answer_callback,
    quiz_command,
    remind_cancel_command,
    remind_command,
    remind_list_command,
    warn_command,
)
from config import load_moderation_config
from moderation_logic import evaluate_message
from moderation_store import load_all_warnings, open_moderation_store
from reminders_store import load_all_reminders
from reminders_store import open_store as open_reminder_store
from scheduler import run_reminder_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


def load_env_file(path=None):
    """A minimal, dependency-free '.env' loader -- optional, production can set real env vars directly."""
    path = path or (BASE_DIR / ".." / ".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


async def on_message(update, context):
    ctx = context.bot_data
    message = update.effective_message
    if message is None or message.from_user is None or message.from_user.is_bot or not message.text:
        return

    user_id = str(message.from_user.id)
    timestamp_ms = message.date.timestamp() * 1000
    timestamps = ctx["recent_message_timestamps"].get(user_id, [])

    verdict = evaluate_message(
        text=message.text,
        timestamp=timestamp_ms,
        recent_timestamps=timestamps,
        banned_words=ctx["config"]["banned_words"],
        flood_options=ctx["config"]["flood"],
    )
    ctx["recent_message_timestamps"][user_id] = [*timestamps, timestamp_ms][-20:]

    if verdict["action"] == "delete":
        await message.delete()
        await context.bot.send_message(
            chat_id=message.chat_id, text=f"{message.from_user.first_name}, message supprime (mot interdit)."
        )
    elif verdict["action"] == "mute":
        until = datetime.now() + timedelta(seconds=60)
        await context.bot.restrict_chat_member(
            chat_id=message.chat_id,
            user_id=message.from_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        await context.bot.send_message(
            chat_id=message.chat_id,
            text=f"{message.from_user.first_name} a ete mis en pause 1 minute (flood detecte).",
        )


async def post_init(application):
    application.bot_data["scheduler_task"] = asyncio.create_task(
        run_reminder_scheduler(application.bot, application.bot_data)
    )


def build_application(token):
    question_bank = json.loads((BASE_DIR / "data" / "questions.json").read_text(encoding="utf-8"))

    application = Application.builder().token(token).post_init(post_init).build()
    application.bot_data.update(
        {
            "config": load_moderation_config(),
            "question_bank": question_bank,
            "reminder_db": open_reminder_store(str(BASE_DIR / "reminders.sqlite")),
            "moderation_db": open_moderation_store(str(BASE_DIR / "moderation.sqlite")),
            "quiz_sessions": {},
            "recent_message_timestamps": {},
        }
    )
    application.bot_data["reminders"] = load_all_reminders(application.bot_data["reminder_db"])
    application.bot_data["warnings"] = load_all_warnings(application.bot_data["moderation_db"])

    application.add_handler(CommandHandler("remind", remind_command))
    application.add_handler(CommandHandler("remind_list", remind_list_command))
    application.add_handler(CommandHandler("remind_cancel", remind_cancel_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CallbackQueryHandler(quiz_answer_callback, pattern=r"^quiz:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    return application


def main():
    load_env_file()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN manquant (voir .env.example).")

    application = build_application(token)
    logger.info("Demarrage du bot Telegram...")
    application.run_polling()


if __name__ == "__main__":
    main()
