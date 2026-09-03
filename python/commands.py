"""
Command handlers -- each receives python-telegram-bot's (update,
context), with our shared mutable state living in context.bot_data
(see bot.py for how it's built). The rules themselves (validation,
scoring, flood/word checks) all live in the pure *_logic modules; this
file is just wiring, and it can't be exercised without a real bot
token, unlike everything it calls.
"""

import asyncio
from datetime import datetime, timedelta

from telegram import ChatPermissions

from moderation_logic import add_warning, recommended_action, warning_count
from moderation_store import insert_warning
from quiz_logic import advance_question, current_question, pick_questions, standings, start_session, submit_answer
from reminders_logic import active_reminders_for_user, cancel_reminder, create_reminder, parse_duration
from reminders_store import delete_reminder, insert_reminder
from telegram_format import build_quiz_keyboard, build_quiz_message, format_reminder_list, format_standings

QUESTION_DURATION_SECONDS = 15
QUIZ_QUESTION_COUNT = 5


async def _is_chat_admin(update, context):
    """Telegram has no declarative per-command permission gate like Discord's
    slash commands, so /warn, /mute and /clear check chat admin status themselves."""
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in ("administrator", "creator")


async def run_quiz_round(bot, chat_id, session_key, ctx):
    session = ctx["quiz_sessions"].get(session_key)
    if session is None:
        return  # cancelled or superseded

    question = current_question(session)
    if question is None:
        final_standings = standings(session)
        await bot.send_message(
            chat_id=chat_id,
            text=f"Quiz termine ! Classement :\n{format_standings(final_standings, lambda uid: f'joueur {uid}')}",
        )
        ctx["quiz_sessions"].pop(session_key, None)
        return

    await bot.send_message(
        chat_id=chat_id,
        text=build_quiz_message(question, session["current_index"], len(session["questions"])),
        reply_markup=build_quiz_keyboard(question, session_key),
    )

    await asyncio.sleep(QUESTION_DURATION_SECONDS)

    latest = ctx["quiz_sessions"].get(session_key)
    if latest is None:
        return  # session ended early

    await bot.send_message(
        chat_id=chat_id, text=f"Bonne reponse : {question['choices'][question['answerIndex']]}"
    )
    ctx["quiz_sessions"][session_key] = advance_question(latest)
    await run_quiz_round(bot, chat_id, session_key, ctx)


async def remind_command(update, context):
    ctx = context.bot_data
    if len(context.args) < 2:
        await update.message.reply_text(
            'Usage : /remind <quand> <message> (ex: /remind 10m "boire de l\'eau")'
        )
        return
    try:
        reminder = create_reminder(
            user_id=str(update.effective_user.id),
            channel_id=str(update.effective_chat.id),
            message=" ".join(context.args[1:]),
            when=context.args[0],
        )
    except ValueError as err:
        await update.message.reply_text(f"Erreur : {err}")
        return

    insert_reminder(ctx["reminder_db"], reminder)
    ctx["reminders"].append(reminder)
    due = datetime.fromtimestamp(reminder["due_at"]).strftime("%Y-%m-%d %H:%M")
    await update.message.reply_text(f"Rappel programme pour {due}.")


async def remind_list_command(update, context):
    ctx = context.bot_data
    active = active_reminders_for_user(ctx["reminders"], str(update.effective_user.id))
    await update.message.reply_text(format_reminder_list(active))


async def remind_cancel_command(update, context):
    ctx = context.bot_data
    if not context.args:
        await update.message.reply_text("Usage : /remind_cancel <id>")
        return

    short_id = context.args[0]
    user_id = str(update.effective_user.id)
    match = next(
        (r for r in active_reminders_for_user(ctx["reminders"], user_id) if r["id"].startswith(short_id)), None
    )
    if match is None:
        await update.message.reply_text("Rappel introuvable.")
        return

    ctx["reminders"] = cancel_reminder(ctx["reminders"], match["id"], user_id)
    delete_reminder(ctx["reminder_db"], match["id"])
    await update.message.reply_text("Rappel annule.")


async def quiz_command(update, context):
    ctx = context.bot_data
    chat_id = update.effective_chat.id
    session_key = str(chat_id)
    if session_key in ctx["quiz_sessions"]:
        await update.message.reply_text("Un quiz est deja en cours dans ce salon.")
        return

    category = context.args[0] if context.args else None
    questions = pick_questions(ctx["question_bank"], QUIZ_QUESTION_COUNT, category=category)
    if not questions:
        await update.message.reply_text(f'Aucune question pour la categorie "{category}".')
        return

    session = start_session(chat_id, questions)
    ctx["quiz_sessions"][session_key] = session
    await update.message.reply_text(
        f"Quiz lance : {len(questions)} questions, {QUESTION_DURATION_SECONDS}s chacune !"
    )
    await run_quiz_round(context.bot, chat_id, session_key, ctx)


async def quiz_answer_callback(update, context):
    ctx = context.bot_data
    query = update.callback_query
    _, session_key, choice_index_str = query.data.split(":")

    session = ctx["quiz_sessions"].get(session_key)
    if session is None:
        await query.answer("Ce quiz est termine.")
        return

    next_session, status = submit_answer(session, str(query.from_user.id), int(choice_index_str))
    ctx["quiz_sessions"][session_key] = next_session

    messages = {
        "correct": "Bonne reponse !",
        "incorrect": "Mauvaise reponse.",
        "already-answered": "Vous avez deja repondu a cette question.",
        "complete": "Ce quiz est termine.",
    }
    await query.answer(messages[status])


async def warn_command(update, context):
    ctx = context.bot_data
    if not await _is_chat_admin(update, context):
        await update.message.reply_text("Cette commande est reservee aux administrateurs.")
        return
    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text("Usage : repondez au message du membre avec /warn <raison>")
        return

    target = update.message.reply_to_message.from_user
    reason = " ".join(context.args)
    ctx["warnings"] = add_warning(ctx["warnings"], str(target.id), str(update.effective_user.id), reason)
    insert_warning(ctx["moderation_db"], ctx["warnings"][-1])

    count = warning_count(ctx["warnings"], str(target.id))
    action = recommended_action(count, ctx["config"]["warn_thresholds"])
    follow_up = ""
    if action == "mute":
        follow_up = " Ce membre a atteint le seuil de mute recommande."
    elif action == "kick":
        follow_up = " Ce membre a atteint le seuil d'exclusion recommande."

    plural = "s" if count > 1 else ""
    await update.message.reply_text(
        f"{target.first_name} a ete averti ({count} avertissement{plural}).{follow_up}"
    )


async def mute_command(update, context):
    if not await _is_chat_admin(update, context):
        await update.message.reply_text("Cette commande est reservee aux administrateurs.")
        return
    if not update.message.reply_to_message or not context.args:
        await update.message.reply_text("Usage : repondez au message du membre avec /mute <duree> (ex: 10m, 1h)")
        return

    duration_seconds = parse_duration(context.args[0])
    if duration_seconds is None:
        await update.message.reply_text("Duree invalide (ex: 10m, 1h).")
        return

    target = update.message.reply_to_message.from_user
    until = datetime.now() + timedelta(seconds=duration_seconds)
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=target.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until,
    )
    await update.message.reply_text(f"{target.first_name} est reduit au silence pour {context.args[0]}.")


async def clear_command(update, context):
    if not await _is_chat_admin(update, context):
        await update.message.reply_text("Cette commande est reservee aux administrateurs.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage : /clear <nombre> (1-100)")
        return

    count = max(1, min(int(context.args[0]), 100))
    chat_id = update.effective_chat.id
    message_id = update.message.message_id

    deleted = 0
    for offset in range(count):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id - offset)
            deleted += 1
        except Exception:
            pass  # already deleted, too old, or the bot lacks rights -- skip it

    await update.message.reply_text(f"{deleted} message(s) supprime(s).")
