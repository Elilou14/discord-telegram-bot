import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { test } from "node:test";

const dataPath = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "data", "questions.json");
const questions = JSON.parse(readFileSync(dataPath, "utf8"));

test("questions.json", async (t) => {
  await t.test("has a reasonable number of questions", () => {
    assert.ok(questions.length >= 20);
  });

  await t.test("every question has exactly 4 choices and a valid answerIndex", () => {
    for (const q of questions) {
      assert.equal(q.choices.length, 4, `${q.id} should have 4 choices`);
      assert.ok(q.answerIndex >= 0 && q.answerIndex < 4, `${q.id} answerIndex out of range`);
    }
  });

  await t.test("every id is unique", () => {
    const ids = questions.map((q) => q.id);
    assert.equal(new Set(ids).size, ids.length);
  });

  await t.test("has at least 3 categories", () => {
    const categories = new Set(questions.map((q) => q.category));
    assert.ok(categories.size >= 3);
  });
});
