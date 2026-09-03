import assert from "node:assert/strict";
import { test } from "node:test";

import { loadModerationConfig } from "../config.js";

test("loadModerationConfig", async (t) => {
  await t.test("parses a comma-separated banned word list, trimming whitespace", () => {
    const config = loadModerationConfig({ BANNED_WORDS: "badword,  spam-link ,another" });
    assert.deepEqual(config.bannedWords, ["badword", "spam-link", "another"]);
  });

  await t.test("empty/unset BANNED_WORDS yields an empty list", () => {
    assert.deepEqual(loadModerationConfig({}).bannedWords, []);
    assert.deepEqual(loadModerationConfig({ BANNED_WORDS: "" }).bannedWords, []);
  });

  await t.test("filters out empty entries from trailing commas", () => {
    const config = loadModerationConfig({ BANNED_WORDS: "badword,,other," });
    assert.deepEqual(config.bannedWords, ["badword", "other"]);
  });

  await t.test("defaults flood and warn thresholds when unset", () => {
    const config = loadModerationConfig({});
    assert.deepEqual(config.flood, { maxMessages: 5, windowMs: 10_000 });
    assert.deepEqual(config.warnThresholds, { mute: 3, kick: 5 });
  });

  await t.test("reads numeric overrides from env", () => {
    const config = loadModerationConfig({
      FLOOD_MAX_MESSAGES: "8",
      FLOOD_WINDOW_MS: "5000",
      WARN_MUTE_THRESHOLD: "2",
      WARN_KICK_THRESHOLD: "4",
    });
    assert.deepEqual(config.flood, { maxMessages: 8, windowMs: 5000 });
    assert.deepEqual(config.warnThresholds, { mute: 2, kick: 4 });
  });

  await t.test("falls back to defaults on non-numeric overrides", () => {
    const config = loadModerationConfig({ FLOOD_MAX_MESSAGES: "not-a-number" });
    assert.equal(config.flood.maxMessages, 5);
  });
});
