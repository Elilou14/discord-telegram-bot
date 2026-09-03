/**
 * SQLite persistence for reminders, using Node's built-in node:sqlite
 * (no dependency). Kept separate from reminders-logic.js so the
 * rules stay testable without touching a database at all -- this
 * module is just plain load/save.
 */

import { DatabaseSync } from "node:sqlite";

export function openStore(path = "reminders.sqlite") {
  const db = new DatabaseSync(path);
  db.exec(`
    CREATE TABLE IF NOT EXISTS reminders (
      id TEXT PRIMARY KEY,
      userId TEXT NOT NULL,
      channelId TEXT NOT NULL,
      guildId TEXT,
      message TEXT NOT NULL,
      dueAt INTEGER NOT NULL,
      createdAt INTEGER NOT NULL,
      sent INTEGER NOT NULL DEFAULT 0
    )
  `);
  return db;
}

function rowToReminder(row) {
  return {
    id: row.id,
    userId: row.userId,
    channelId: row.channelId,
    guildId: row.guildId,
    message: row.message,
    dueAt: row.dueAt,
    createdAt: row.createdAt,
    sent: Boolean(row.sent),
  };
}

export function insertReminder(db, reminder) {
  db.prepare(
    `INSERT INTO reminders (id, userId, channelId, guildId, message, dueAt, createdAt, sent)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
  ).run(
    reminder.id,
    reminder.userId,
    reminder.channelId,
    reminder.guildId,
    reminder.message,
    reminder.dueAt,
    reminder.createdAt,
    reminder.sent ? 1 : 0
  );
}

export function loadAllReminders(db) {
  return db.prepare(`SELECT * FROM reminders`).all().map(rowToReminder);
}

export function markReminderSent(db, id) {
  db.prepare(`UPDATE reminders SET sent = 1 WHERE id = ?`).run(id);
}

export function deleteReminder(db, id) {
  db.prepare(`DELETE FROM reminders WHERE id = ?`).run(id);
}
