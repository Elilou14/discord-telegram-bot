/**
 * Polls for due reminders and fires them. Kept separate from bot.js
 * so the polling interval itself is the only untestable part --
 * everything it calls (dueReminders, markSent) is pure and already
 * tested in reminders-logic.test.js.
 */

import { formatReminderFired } from "./discord-format.js";
import { dueReminders, markSent } from "./reminders-logic.js";
import { markReminderSent } from "./reminders-store.js";

export function startReminderScheduler(client, ctx, intervalMs = 15_000) {
  return setInterval(async () => {
    const due = dueReminders(ctx.reminders);
    for (const reminder of due) {
      try {
        const channel = await client.channels.fetch(reminder.channelId);
        await channel.send(formatReminderFired(reminder));
      } catch (err) {
        console.error(`Impossible d'envoyer le rappel ${reminder.id} :`, err.message);
      }
      markReminderSent(ctx.reminderDb, reminder.id);
      ctx.reminders = markSent(ctx.reminders, reminder.id);
    }
  }, intervalMs);
}
