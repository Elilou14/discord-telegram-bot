import assert from "node:assert/strict";
import { test } from "node:test";

import {
  advanceQuestion,
  currentQuestion,
  isSessionComplete,
  pickQuestions,
  standings,
  startSession,
  submitAnswer,
} from "../quiz-logic.js";

function makeBank() {
  return [
    { id: "q1", category: "geo", question: "Q1", choices: ["a", "b", "c", "d"], answerIndex: 0 },
    { id: "q2", category: "geo", question: "Q2", choices: ["a", "b", "c", "d"], answerIndex: 1 },
    { id: "q3", category: "science", question: "Q3", choices: ["a", "b", "c", "d"], answerIndex: 2 },
    { id: "q4", category: "science", question: "Q4", choices: ["a", "b", "c", "d"], answerIndex: 3 },
  ];
}

function seededRng(seed) {
  let state = seed;
  return () => {
    state |= 0;
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

test("pickQuestions", async (t) => {
  await t.test("returns the requested count with no repeats", () => {
    const picked = pickQuestions(makeBank(), 3, { rng: seededRng(1) });
    assert.equal(picked.length, 3);
    assert.equal(new Set(picked.map((q) => q.id)).size, 3);
  });

  await t.test("caps at the pool size when count exceeds it", () => {
    const picked = pickQuestions(makeBank(), 10, { rng: seededRng(1) });
    assert.equal(picked.length, 4);
  });

  await t.test("filters by category", () => {
    const picked = pickQuestions(makeBank(), 4, { category: "science", rng: seededRng(1) });
    assert.equal(picked.length, 2);
    assert.ok(picked.every((q) => q.category === "science"));
  });

  await t.test("deterministic with a seeded rng", () => {
    const a = pickQuestions(makeBank(), 4, { rng: seededRng(42) });
    const b = pickQuestions(makeBank(), 4, { rng: seededRng(42) });
    assert.deepEqual(a.map((q) => q.id), b.map((q) => q.id));
  });
});

test("session lifecycle", async (t) => {
  await t.test("starts at question 0, not complete", () => {
    const session = startSession({ channelId: "c1", questions: makeBank().slice(0, 2), now: 1000 });
    assert.equal(currentQuestion(session).id, "q1");
    assert.equal(isSessionComplete(session), false);
  });

  await t.test("advancing past the last question completes it", () => {
    let session = startSession({ channelId: "c1", questions: makeBank().slice(0, 1), now: 1000 });
    session = advanceQuestion(session);
    assert.equal(currentQuestion(session), null);
    assert.equal(isSessionComplete(session), true);
  });
});

test("submitAnswer", async (t) => {
  await t.test("correct answer increments the user's score", () => {
    const session = startSession({ channelId: "c1", questions: makeBank(), now: 1000 });
    const { session: next, status } = submitAnswer(session, "u1", 0); // q1's answerIndex is 0
    assert.equal(status, "correct");
    assert.equal(next.scores.u1, 1);
  });

  await t.test("incorrect answer does not increment the score", () => {
    const session = startSession({ channelId: "c1", questions: makeBank(), now: 1000 });
    const { session: next, status } = submitAnswer(session, "u1", 1); // wrong for q1
    assert.equal(status, "incorrect");
    assert.equal(next.scores.u1 ?? 0, 0);
  });

  await t.test("a user can't answer the same question twice", () => {
    const session = startSession({ channelId: "c1", questions: makeBank(), now: 1000 });
    const first = submitAnswer(session, "u1", 0);
    const second = submitAnswer(first.session, "u1", 0);
    assert.equal(second.status, "already-answered");
    assert.equal(second.session, first.session); // no-op, same reference
  });

  await t.test("different users can both answer the same question", () => {
    const session = startSession({ channelId: "c1", questions: makeBank(), now: 1000 });
    const afterU1 = submitAnswer(session, "u1", 0).session;
    const { session: afterU2, status } = submitAnswer(afterU1, "u2", 1);
    assert.equal(status, "incorrect");
    assert.equal(afterU2.scores.u1, 1);
  });

  await t.test("submitting after the session is complete reports complete", () => {
    let session = startSession({ channelId: "c1", questions: makeBank().slice(0, 1), now: 1000 });
    session = advanceQuestion(session);
    const result = submitAnswer(session, "u1", 0);
    assert.equal(result.status, "complete");
    assert.equal(result.session, session); // no-op, same reference
  });

  await t.test("does not mutate the original session", () => {
    const session = startSession({ channelId: "c1", questions: makeBank(), now: 1000 });
    submitAnswer(session, "u1", 0);
    assert.deepEqual(session.scores, {});
    assert.deepEqual(session.answeredBy, {});
  });
});

test("advanceQuestion", async (t) => {
  await t.test("moves to the next question and resets who answered", () => {
    const session = startSession({ channelId: "c1", questions: makeBank(), now: 1000 });
    const answered = submitAnswer(session, "u1", 0).session;
    const advanced = advanceQuestion(answered);
    assert.equal(currentQuestion(advanced).id, "q2");
    assert.deepEqual(advanced.answeredBy, {});
    assert.equal(advanced.scores.u1, 1); // score carries over
  });
});

test("standings", async (t) => {
  await t.test("sorts by score descending", () => {
    let session = startSession({ channelId: "c1", questions: makeBank(), now: 1000 });
    session = submitAnswer(session, "u1", 0).session; // correct (q1 answerIndex 0)
    session = submitAnswer(session, "u2", 0).session; // correct (q1 answerIndex 0)
    session = advanceQuestion(session);
    session = submitAnswer(session, "u2", 1).session; // correct (q2 answerIndex 1) -> u2: 2
    session = submitAnswer(session, "u1", 0).session; // incorrect -> u1 stays at 1

    const result = standings(session);
    assert.deepEqual(result, [
      { userId: "u2", score: 2 },
      { userId: "u1", score: 1 },
    ]);
  });

  await t.test("empty when no one has scored", () => {
    const session = startSession({ channelId: "c1", questions: makeBank(), now: 1000 });
    assert.deepEqual(standings(session), []);
  });
});
