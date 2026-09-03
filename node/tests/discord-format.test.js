import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildQuizComponents,
  buildQuizEmbed,
  formatReminderFired,
  formatReminderList,
  formatStandings,
} from "../discord-format.js";

const sampleQuestion = {
  id: "q1",
  category: "geo",
  question: "Capitale de la France ?",
  choices: ["Lyon", "Paris", "Marseille", "Nice"],
  answerIndex: 1,
};

test("buildQuizEmbed", async (t) => {
  await t.test("has a title, the question text, and 4 lettered fields", () => {
    const json = buildQuizEmbed(sampleQuestion, 0, 5).toJSON();
    assert.equal(json.title, "Question 1/5");
    assert.equal(json.description, "Capitale de la France ?");
    assert.equal(json.fields.length, 4);
    assert.deepEqual(
      json.fields.map((f) => f.name),
      ["A", "B", "C", "D"]
    );
    assert.equal(json.fields[1].value, "Paris");
  });
});

test("buildQuizComponents", async (t) => {
  await t.test("one row with 4 buttons, custom ids carry the session and choice index", () => {
    const [row] = buildQuizComponents(sampleQuestion, "session-1");
    const json = row.toJSON();
    assert.equal(json.components.length, 4);
    assert.deepEqual(
      json.components.map((b) => b.custom_id),
      ["quiz:session-1:0", "quiz:session-1:1", "quiz:session-1:2", "quiz:session-1:3"]
    );
    assert.deepEqual(
      json.components.map((b) => b.label),
      ["A", "B", "C", "D"]
    );
  });
});

test("formatReminderFired", async (t) => {
  await t.test("mentions the user and includes the message", () => {
    const text = formatReminderFired({ userId: "u1", message: "boire de l'eau" });
    assert.ok(text.includes("<@u1>"));
    assert.ok(text.includes("boire de l'eau"));
  });
});

test("formatReminderList", async (t) => {
  await t.test("empty list has a friendly message", () => {
    assert.equal(formatReminderList([]), "Vous n'avez aucun rappel actif.");
  });

  await t.test("lists each reminder with a short id", () => {
    const text = formatReminderList([{ id: "abcdefgh12345", message: "test", dueAt: 1_000_000 }]);
    assert.ok(text.includes("test"));
    assert.ok(text.includes("abcdefgh"));
    assert.ok(!text.includes("12345")); // only the first 8 chars of the id
  });
});

test("formatStandings", async (t) => {
  await t.test("empty standings has a friendly message", () => {
    assert.equal(formatStandings([], (id) => id), "Personne n'a encore marque de points.");
  });

  await t.test("lists each entry with a resolved display name and pluralized points", () => {
    const text = formatStandings(
      [
        { userId: "u1", score: 3 },
        { userId: "u2", score: 1 },
      ],
      (id) => `<@${id}>`
    );
    assert.ok(text.includes("<@u1> -- 3 pts"));
    assert.ok(text.includes("<@u2> -- 1 pt"));
    assert.ok(!text.includes("1 pts")); // singular for exactly 1
  });
});
