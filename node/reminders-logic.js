/**
 * Pure reminders logic -- no network, no database, no globals. Every
 * function takes the current reminder list in and returns a new list
 * (or derived data) out, which is what makes it testable with plain
 * node:test. Persistence lives in reminders-store.js.
 */

import crypto from "node:crypto";

const DURATION_RE = /^(\d+)(s|m|h|d)$/;
const ABSOLUTE_RE = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})$/;

const MULTIPLIERS = { s: 1000, m: 60_000, h: 3_600_000, d: 86_400_000 };

/** "10m", "2h", "1d", "45s" -> milliseconds. null if it doesn't match. */
export function parseDuration(text) {
  const match = DURATION_RE.exec(text.trim());
  if (!match) return null;
  return Number(match[1]) * MULTIPLIERS[match[2]];
}

/**
 * A relative duration ("10m") or an absolute "YYYY-MM-DD HH:MM" (24h,
 * local time), resolved against `now`. null if neither parses.
 */
export function parseWhen(text, now = new Date()) {
  const trimmed = text.trim();

  const duration = parseDuration(trimmed);
  if (duration !== null) {
    return new Date(now.getTime() + duration);
  }

  const match = ABSOLUTE_RE.exec(trimmed);
  if (!match) return null;

  const [, year, month, day, hour, minute] = match.map(Number);
  if (month < 1 || month > 12 || day < 1 || day > 31 || hour > 23 || minute > 59) return null;

  return new Date(year, month - 1, day, hour, minute, 0, 0);
}

function defaultIdGenerator() {
  return crypto.randomUUID();
}

/**
 * Validates and builds a new reminder. Throws on an empty message, an
 * unparseable `when`, or a `when` that's already in the past --
 * these are user-input errors the bot layer should catch and show
 * back to the user, not silent failures.
 */
export function createReminder(
  { userId, channelId, guildId = null, message, when, now = new Date() },
  idGenerator = defaultIdGenerator
) {
  if (!message || !message.trim()) {
    throw new Error("Le message du rappel ne peut pas etre vide.");
  }

  const dueAt = parseWhen(when, now);
  if (dueAt === null) {
    throw new Error(`Date ou duree invalide : "${when}" (ex: 10m, 2h, 1d, ou 2026-09-10 14:30)`);
  }
  if (dueAt.getTime() <= now.getTime()) {
    throw new Error("La date du rappel doit etre dans le futur.");
  }

  return {
    id: idGenerator(),
    userId,
    channelId,
    guildId,
    message: message.trim(),
    dueAt: dueAt.getTime(),
    createdAt: now.getTime(),
    sent: false,
  };
}

/** A user's own pending reminders, soonest first. */
export function activeRemindersForUser(reminders, userId) {
  return reminders.filter((r) => r.userId === userId && !r.sent).sort((a, b) => a.dueAt - b.dueAt);
}

/** Reminders whose time has come and haven't fired yet. */
export function dueReminders(reminders, now = new Date()) {
  const nowMs = now.getTime();
  return reminders.filter((r) => !r.sent && r.dueAt <= nowMs);
}

/** No-op (same reference) if `id` isn't a pending reminder owned by `userId`. */
export function cancelReminder(reminders, id, userId) {
  const index = reminders.findIndex((r) => r.id === id && r.userId === userId && !r.sent);
  if (index === -1) return reminders;
  return [...reminders.slice(0, index), ...reminders.slice(index + 1)];
}

export function markSent(reminders, id) {
  return reminders.map((r) => (r.id === id ? { ...r, sent: true } : r));
}
