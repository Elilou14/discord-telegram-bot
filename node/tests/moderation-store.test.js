import assert from "node:assert/strict";
import { test } from "node:test";

import { insertWarning, loadAllWarnings, openModerationStore } from "../moderation-store.js";

function sampleWarning(overrides = {}) {
  return {
    id: "w1",
    userId: "u1",
    moderatorId: "mod1",
    reason: "spam",
    at: 1000,
    ...overrides,
  };
}

test("moderation-store", async (t) => {
  await t.test("round-trips a warning through insert and load", () => {
    const db = openModerationStore(":memory:");
    insertWarning(db, sampleWarning());
    const all = loadAllWarnings(db);
    assert.equal(all.length, 1);
    assert.equal(all[0].userId, "u1");
    assert.equal(all[0].reason, "spam");
  });

  await t.test("multiple warnings for the same user persist independently", () => {
    const db = openModerationStore(":memory:");
    insertWarning(db, sampleWarning({ id: "w1" }));
    insertWarning(db, sampleWarning({ id: "w2", reason: "insulte" }));
    const all = loadAllWarnings(db);
    assert.equal(all.length, 2);
    assert.deepEqual(all.map((w) => w.reason).sort(), ["insulte", "spam"]);
  });
});
