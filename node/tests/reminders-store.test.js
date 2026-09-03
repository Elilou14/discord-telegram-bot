import assert from "node:assert/strict";
import { test } from "node:test";

import { deleteReminder, insertReminder, loadAllReminders, markReminderSent, openStore } from "../reminders-store.js";

function sampleReminder(overrides = {}) {
  return {
    id: "r1",
    userId: "u1",
    channelId: "c1",
    guildId: "g1",
    message: "boire de l'eau",
    dueAt: 123456,
    createdAt: 100,
    sent: false,
    ...overrides,
  };
}

test("reminders-store", async (t) => {
  await t.test("round-trips a reminder through insert and load", () => {
    const db = openStore(":memory:");
    insertReminder(db, sampleReminder());
    const all = loadAllReminders(db);
    assert.equal(all.length, 1);
    assert.deepEqual(all[0], sampleReminder());
  });

  await t.test("guildId can be null (a DM reminder)", () => {
    const db = openStore(":memory:");
    insertReminder(db, sampleReminder({ id: "r2", guildId: null }));
    const [loaded] = loadAllReminders(db);
    assert.equal(loaded.guildId, null);
  });

  await t.test("markReminderSent flips sent to true", () => {
    const db = openStore(":memory:");
    insertReminder(db, sampleReminder());
    markReminderSent(db, "r1");
    const [loaded] = loadAllReminders(db);
    assert.equal(loaded.sent, true);
  });

  await t.test("deleteReminder removes it", () => {
    const db = openStore(":memory:");
    insertReminder(db, sampleReminder());
    deleteReminder(db, "r1");
    assert.deepEqual(loadAllReminders(db), []);
  });

  await t.test("multiple reminders persist independently", () => {
    const db = openStore(":memory:");
    insertReminder(db, sampleReminder({ id: "r1" }));
    insertReminder(db, sampleReminder({ id: "r2", userId: "u2" }));
    const all = loadAllReminders(db);
    assert.equal(all.length, 2);
    assert.deepEqual(all.map((r) => r.id).sort(), ["r1", "r2"]);
  });
});
