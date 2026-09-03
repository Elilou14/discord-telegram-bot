/**
 * Pure quiz logic -- no network, no timers, no globals. A session is
 * plain data; every function takes one in and returns a new one (or
 * derived data) out, which is what makes it testable with plain
 * node:test regardless of which chat platform is driving it.
 */

function shuffle(list, rng) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

/** `count` random questions from `bank`, no repeats, optionally filtered by category. */
export function pickQuestions(bank, count, { category = null, rng = Math.random } = {}) {
  const pool = category ? bank.filter((q) => q.category === category) : bank;
  return shuffle(pool, rng).slice(0, Math.min(count, pool.length));
}

export function startSession({ channelId, questions, now = Date.now() }) {
  return {
    channelId,
    questions,
    currentIndex: 0,
    scores: {},
    answeredBy: {},
    startedAt: now,
  };
}

export function currentQuestion(session) {
  return session.currentIndex < session.questions.length ? session.questions[session.currentIndex] : null;
}

export function isSessionComplete(session) {
  return session.currentIndex >= session.questions.length;
}

/**
 * Records `userId`'s answer to the current question. Returns
 * { session, status } where status is "correct", "incorrect",
 * "already-answered" (a user only gets one try per question), or
 * "complete" (no current question -- the session already ended).
 * The session itself is returned unchanged for "already-answered"
 * and "complete", same reference, since nothing actually happened.
 */
export function submitAnswer(session, userId, choiceIndex) {
  const question = currentQuestion(session);
  if (!question) {
    return { session, status: "complete" };
  }
  if (Object.prototype.hasOwnProperty.call(session.answeredBy, userId)) {
    return { session, status: "already-answered" };
  }

  const correct = choiceIndex === question.answerIndex;
  const scores = { ...session.scores };
  if (correct) scores[userId] = (scores[userId] || 0) + 1;

  const nextSession = {
    ...session,
    scores,
    answeredBy: { ...session.answeredBy, [userId]: choiceIndex },
  };

  return { session: nextSession, status: correct ? "correct" : "incorrect" };
}

/** Moves to the next question, resetting who has answered. */
export function advanceQuestion(session) {
  return { ...session, currentIndex: session.currentIndex + 1, answeredBy: {} };
}

/** [{ userId, score }], highest score first. */
export function standings(session) {
  return Object.entries(session.scores)
    .map(([userId, score]) => ({ userId, score }))
    .sort((a, b) => b.score - a.score);
}
