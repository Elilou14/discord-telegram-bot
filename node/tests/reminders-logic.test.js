import assert from "node:assert/strict";
import { test } from "node:test";

import {
  activeRemindersForUser,
  cancelReminder,
  createReminder,
  dueReminders,
  markSent,
  parseDuration,
  parseWhen,
} from "../reminders-logic.js";

test("parseDuration", async (t) => {
  await t.test("parses seconds/minutes/hours/days", () => {
    assert.equal(parseDuration("45s"), 45_000);
    assert.equal(parseDuration("10m"), 600_000);
    assert.equal(parseDuration("2h"), 7_200_000);
    assert.equal(parseDuration("1d"), 86_400_000);
  });

  await t.test("rejects unknown formats", () => {
    assert.equal(parseDuration("soon"), null);
    assert.equal(parseDuration("10"), null);
    assert.equal(parseDuration("10y"), null);
    assert.equal(parseDuration(""), null);
  });
});

test("parseWhen", async (t) => {
  const now = new Date(2026, 0, 1, 12, 0, 0);

  await t.test("relative duration resolves against now", () => {
    const result = parseWhen("10m", now);
    assert.equal(result.getTime(), now.getTime() + 600_000);
  });

  await t.test("absolute datetime", () => {
    const result = parseWhen("2026-03-15 09:30", now);
    assert.equal(result.getFullYear(), 2026);
    assert.equal(result.getMonth(), 2);
    assert.equal(result.getDate(), 15);
    assert.equal(result.getHours(), 9);
    assert.equal(result.getMinutes(), 30);
  });

  await t.test("absolute datetime accepts a T separator", () => {
    const result = parseWhen("2026-03-15T09:30", now);
    assert.notEqual(result, null);
  });

  await t.test("rejects out-of-range month/day/hour/minute", () => {
    assert.equal(parseWhen("2026-13-01 10:00", now), null);
    assert.equal(parseWhen("2026-01-32 10:00", now), null);
    assert.equal(parseWhen("2026-01-01 24:00", now), null);
    assert.equal(parseWhen("2026-01-01 10:60", now), null);
  });

  await t.test("rejects garbage", () => {
    assert.equal(parseWhen("whenever", now), null);
  });
});

test("createReminder", async (t) => {
  const now = new Date(2026, 0, 1, 12, 0, 0);
  const fixedId = () => "fixed-id";

  await t.test("builds a valid reminder", () => {
    const reminder = createReminder(
      { userId: "u1", channelId: "c1", message: "  boire de l'eau  ", when: "10m", now },
      fixedId
    );
    assert.equal(reminder.id, "fixed-id");
    assert.equal(reminder.userId, "u1");
    assert.equal(reminder.message, "boire de l'eau"); // trimmed
    assert.equal(reminder.dueAt, now.getTime() + 600_000);
    assert.equal(reminder.sent, false);
  });

  await t.test("rejects an empty message", () => {
    assert.throws(() => createReminder({ userId: "u1", channelId: "c1", message: "   ", when: "10m", now }, fixedId));
  });

  await t.test("rejects an unparseable when", () => {
    assert.throws(() =>
      createReminder({ userId: "u1", channelId: "c1", message: "hey", when: "whenever", now }, fixedId)
    );
  });

  await t.test("rejects a when already in the past", () => {
    assert.throws(() =>
      createReminder({ userId: "u1", channelId: "c1", message: "hey", when: "2020-01-01 00:00", now }, fixedId)
    );
  });
});

test("activeRemindersForUser", async (t) => {
  await t.test("filters to the user's own unsent reminders, soonest first", () => {
    const reminders = [
      { id: "a", userId: "u1", dueAt: 300, sent: false },
      { id: "b", userId: "u2", dueAt: 100, sent: false },
      { id: "c", userId: "u1", dueAt: 100, sent: false },
      { id: "d", userId: "u1", dueAt: 50, sent: true },
    ];
    const result = activeRemindersForUser(reminders, "u1");
    assert.deepEqual(result.map((r) => r.id), ["c", "a"]);
  });
});

test("dueReminders", async (t) => {
  await t.test("returns unsent reminders whose time has come", () => {
    const now = new Date(1000);
    const reminders = [
      { id: "a", dueAt: 500, sent: false },
      { id: "b", dueAt: 1500, sent: false },
      { id: "c", dueAt: 500, sent: true },
    ];
    const result = dueReminders(reminders, now);
    assert.deepEqual(result.map((r) => r.id), ["a"]);
  });
});

test("cancelReminder", async (t) => {
  await t.test("removes the matching pending reminder", () => {
    const reminders = [
      { id: "a", userId: "u1", sent: false },
      { id: "b", userId: "u1", sent: false },
    ];
    const result = cancelReminder(reminders, "a", "u1");
    assert.deepEqual(result.map((r) => r.id), ["b"]);
  });

  await t.test("no-op (same reference) for an unknown id", () => {
    const reminders = [{ id: "a", userId: "u1", sent: false }];
    assert.equal(cancelReminder(reminders, "missing", "u1"), reminders);
  });

  await t.test("no-op for another user's reminder", () => {
    const reminders = [{ id: "a", userId: "u1", sent: false }];
    assert.equal(cancelReminder(reminders, "a", "u2"), reminders);
  });

  await t.test("no-op for an already-sent reminder", () => {
    const reminders = [{ id: "a", userId: "u1", sent: true }];
    assert.equal(cancelReminder(reminders, "a", "u1"), reminders);
  });
});

test("markSent", async (t) => {
  await t.test("marks the matching reminder sent without mutating others", () => {
    const reminders = [
      { id: "a", sent: false },
      { id: "b", sent: false },
    ];
    const result = markSent(reminders, "a");
    assert.equal(result[0].sent, true);
    assert.equal(result[1].sent, false);
    assert.equal(reminders[0].sent, false); // original untouched
  });
});
