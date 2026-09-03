/**
 * Pure moderation logic -- no network, no timers, no globals. The
 * bot layer owns its own banned-word list and thresholds (config,
 * not hardcoded here) and supplies the message history; this module
 * only decides what to do with it.
 */

import crypto from "node:crypto";

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Whole-word, case-insensitive match against any entry in `bannedWords`. */
export function containsBannedWord(text, bannedWords) {
  const normalized = text.toLowerCase();
  return bannedWords.some((word) => {
    const pattern = new RegExp(`\\b${escapeRegExp(word.toLowerCase())}\\b`, "u");
    return pattern.test(normalized);
  });
}

/**
 * True if the most recent `maxMessages` timestamps (including the
 * one just sent) all landed within `windowMs` of each other -- i.e.
 * the user posted that many messages faster than the window allows.
 */
export function isFlooding(timestamps, { maxMessages = 5, windowMs = 10_000 } = {}) {
  if (timestamps.length < maxMessages) return false;
  const recent = timestamps.slice(-maxMessages);
  return recent[recent.length - 1] - recent[0] < windowMs;
}

/**
 * Combines the banned-word and flood checks into one verdict for an
 * incoming message. Banned words take priority (delete on sight);
 * flooding recommends a mute; otherwise no action.
 */
export function evaluateMessage({ text, timestamp, recentTimestamps = [], bannedWords = [], floodOptions = {} }) {
  if (containsBannedWord(text, bannedWords)) {
    return { action: "delete", reason: "mot-interdit" };
  }
  if (isFlooding([...recentTimestamps, timestamp], floodOptions)) {
    return { action: "mute", reason: "flood" };
  }
  return { action: "none", reason: null };
}

function defaultIdGenerator() {
  return crypto.randomUUID();
}

export function addWarning(warnings, { userId, moderatorId, reason, now = Date.now() }, idGenerator = defaultIdGenerator) {
  return [...warnings, { id: idGenerator(), userId, moderatorId, reason, at: now }];
}

export function warningCount(warnings, userId) {
  return warnings.filter((w) => w.userId === userId).length;
}

/**
 * What a moderator should do once a user hits N warnings. Mute at
 * `thresholds.mute`, kick at `thresholds.kick` and beyond ("kick"
 * wins over "mute" once both thresholds are met).
 */
export function recommendedAction(count, thresholds = { mute: 3, kick: 5 }) {
  if (count >= thresholds.kick) return "kick";
  if (count >= thresholds.mute) return "mute";
  return "none";
}
