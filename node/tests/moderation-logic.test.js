import assert from "node:assert/strict";
import { test } from "node:test";

import {
  addWarning,
  containsBannedWord,
  evaluateMessage,
  isFlooding,
  recommendedAction,
  warningCount,
} from "../moderation-logic.js";

test("containsBannedWord", async (t) => {
  const bannedWords = ["badword", "spam-link"];

  await t.test("matches case-insensitively", () => {
    assert.equal(containsBannedWord("this has a BadWord in it", bannedWords), true);
  });

  await t.test("matches whole words only, not substrings", () => {
    assert.equal(containsBannedWord("badwording is not the same word", bannedWords), false);
  });

  await t.test("no match returns false", () => {
    assert.equal(containsBannedWord("a perfectly normal message", bannedWords), false);
  });

  await t.test("escapes regex special characters in the banned word", () => {
    assert.equal(containsBannedWord("check out spam-link now", bannedWords), true);
    assert.equal(containsBannedWord("spam link (without the dash)", bannedWords), false);
  });

  await t.test("empty banned list never matches", () => {
    assert.equal(containsBannedWord("badword", []), false);
  });
});

test("isFlooding", async (t) => {
  await t.test("false when there are fewer messages than the threshold", () => {
    assert.equal(isFlooding([0, 100, 200], { maxMessages: 5, windowMs: 10_000 }), false);
  });

  await t.test("true when maxMessages arrive within the window", () => {
    const timestamps = [0, 100, 200, 300, 400];
    assert.equal(isFlooding(timestamps, { maxMessages: 5, windowMs: 10_000 }), true);
  });

  await t.test("false when the same count is spread across a longer time", () => {
    const timestamps = [0, 5000, 10_000, 15_000, 20_000];
    assert.equal(isFlooding(timestamps, { maxMessages: 5, windowMs: 10_000 }), false);
  });

  await t.test("only looks at the most recent maxMessages", () => {
    // The first two are ancient; the last five are within the window.
    const timestamps = [-100_000, -90_000, 0, 100, 200, 300, 400];
    assert.equal(isFlooding(timestamps, { maxMessages: 5, windowMs: 10_000 }), true);
  });
});

test("evaluateMessage", async (t) => {
  await t.test("a banned word means delete, even without flooding", () => {
    const result = evaluateMessage({
      text: "contains badword here",
      timestamp: 1000,
      recentTimestamps: [],
      bannedWords: ["badword"],
    });
    assert.deepEqual(result, { action: "delete", reason: "mot-interdit" });
  });

  await t.test("flooding without a banned word means mute", () => {
    const result = evaluateMessage({
      text: "hello",
      timestamp: 400,
      recentTimestamps: [0, 100, 200, 300],
      bannedWords: ["badword"],
      floodOptions: { maxMessages: 5, windowMs: 10_000 },
    });
    assert.deepEqual(result, { action: "mute", reason: "flood" });
  });

  await t.test("banned word takes priority over flooding", () => {
    const result = evaluateMessage({
      text: "badword",
      timestamp: 400,
      recentTimestamps: [0, 100, 200, 300],
      bannedWords: ["badword"],
      floodOptions: { maxMessages: 5, windowMs: 10_000 },
    });
    assert.equal(result.action, "delete");
  });

  await t.test("a clean, non-flooding message means no action", () => {
    const result = evaluateMessage({ text: "hello there", timestamp: 1000 });
    assert.deepEqual(result, { action: "none", reason: null });
  });
});

test("warnings", async (t) => {
  const fixedId = (() => {
    let n = 0;
    return () => `warn-${++n}`;
  })();

  await t.test("addWarning appends without mutating the original list", () => {
    const warnings = [];
    const next = addWarning(warnings, { userId: "u1", moderatorId: "mod1", reason: "spam", now: 1000 }, fixedId);
    assert.equal(next.length, 1);
    assert.equal(warnings.length, 0);
    assert.equal(next[0].userId, "u1");
  });

  await t.test("warningCount only counts the given user", () => {
    const warnings = [
      { userId: "u1", reason: "a" },
      { userId: "u2", reason: "b" },
      { userId: "u1", reason: "c" },
    ];
    assert.equal(warningCount(warnings, "u1"), 2);
    assert.equal(warningCount(warnings, "u2"), 1);
    assert.equal(warningCount(warnings, "u3"), 0);
  });
});

test("recommendedAction", async (t) => {
  await t.test("below threshold: none", () => {
    assert.equal(recommendedAction(1), "none");
    assert.equal(recommendedAction(2), "none");
  });

  await t.test("mute threshold", () => {
    assert.equal(recommendedAction(3), "mute");
    assert.equal(recommendedAction(4), "mute");
  });

  await t.test("kick threshold and beyond", () => {
    assert.equal(recommendedAction(5), "kick");
    assert.equal(recommendedAction(10), "kick");
  });

  await t.test("custom thresholds", () => {
    assert.equal(recommendedAction(2, { mute: 2, kick: 4 }), "mute");
    assert.equal(recommendedAction(4, { mute: 2, kick: 4 }), "kick");
  });
});
