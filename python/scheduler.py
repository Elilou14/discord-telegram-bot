"""
Polls for due reminders and fires them. Kept separate from bot.py so
the polling interval itself is the only untestable part -- everything
it calls (due_reminders, mark_sent) is pure and already tested in
test_reminders_logic.py.
"""

import asyncio
import logging

from reminders_logic import due_reminders, mark_sent
from reminders_store import mark_reminder_sent
from telegram_format import format_reminder_fired

logger = logging.getLogger(__name__)


async def run_reminder_scheduler(bot, ctx, interval_seconds=15):
    while True:
        await asyncio.sleep(interval_seconds)
        due = due_reminders(ctx["reminders"])
        for reminder in due:
            try:
                await bot.send_message(chat_id=int(reminder["channel_id"]), text=format_reminder_fired(reminder))
            except Exception as err:  # best-effort delivery -- log and keep going
                logger.error("Impossible d'envoyer le rappel %s : %s", reminder["id"], err)
            mark_reminder_sent(ctx["reminder_db"], reminder["id"])
            ctx["reminders"] = mark_sent(ctx["reminders"], reminder["id"])
