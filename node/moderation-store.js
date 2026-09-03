/**
 * SQLite persistence for moderation warnings, mirroring
 * reminders-store.js's shape: plain load/save, no business rules.
 */

import { DatabaseSync } from "node:sqlite";

export function openModerationStore(path = "moderation.sqlite") {
  const db = new DatabaseSync(path);
  db.exec(`
    CREATE TABLE IF NOT EXISTS warnings (
      id TEXT PRIMARY KEY,
      userId TEXT NOT NULL,
      moderatorId TEXT NOT NULL,
      reason TEXT NOT NULL,
      at INTEGER NOT NULL
    )
  `);
  return db;
}

export function insertWarning(db, warning) {
  db.prepare(`INSERT INTO warnings (id, userId, moderatorId, reason, at) VALUES (?, ?, ?, ?, ?)`).run(
    warning.id,
    warning.userId,
    warning.moderatorId,
    warning.reason,
    warning.at
  );
}

export function loadAllWarnings(db) {
  return db.prepare(`SELECT * FROM warnings`).all();
}
