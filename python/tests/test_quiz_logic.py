import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quiz_logic import (
    advance_question,
    current_question,
    is_session_complete,
    pick_questions,
    standings,
    start_session,
    submit_answer,
)


def make_bank():
    return [
        {"id": "q1", "category": "geo", "question": "Q1", "choices": ["a", "b", "c", "d"], "answerIndex": 0},
        {"id": "q2", "category": "geo", "question": "Q2", "choices": ["a", "b", "c", "d"], "answerIndex": 1},
        {"id": "q3", "category": "science", "question": "Q3", "choices": ["a", "b", "c", "d"], "answerIndex": 2},
        {"id": "q4", "category": "science", "question": "Q4", "choices": ["a", "b", "c", "d"], "answerIndex": 3},
    ]


def seeded_rng(seed):
    state = {"n": seed}

    def rng():
        state["n"] = (state["n"] * 1103515245 + 12345) & 0x7FFFFFFF
        return state["n"] / 0x7FFFFFFF

    return rng


class PickQuestionsTests(unittest.TestCase):
    def test_returns_the_requested_count_with_no_repeats(self):
        picked = pick_questions(make_bank(), 3, rng=seeded_rng(1))
        self.assertEqual(len(picked), 3)
        self.assertEqual(len({q["id"] for q in picked}), 3)

    def test_caps_at_the_pool_size_when_count_exceeds_it(self):
        picked = pick_questions(make_bank(), 10, rng=seeded_rng(1))
        self.assertEqual(len(picked), 4)

    def test_filters_by_category(self):
        picked = pick_questions(make_bank(), 4, category="science", rng=seeded_rng(1))
        self.assertEqual(len(picked), 2)
        self.assertTrue(all(q["category"] == "science" for q in picked))

    def test_deterministic_with_a_seeded_rng(self):
        a = pick_questions(make_bank(), 4, rng=seeded_rng(42))
        b = pick_questions(make_bank(), 4, rng=seeded_rng(42))
        self.assertEqual([q["id"] for q in a], [q["id"] for q in b])


class SessionLifecycleTests(unittest.TestCase):
    def test_starts_at_question_0_not_complete(self):
        session = start_session("c1", make_bank()[:2], now=1000)
        self.assertEqual(current_question(session)["id"], "q1")
        self.assertFalse(is_session_complete(session))

    def test_advancing_past_the_last_question_completes_it(self):
        session = start_session("c1", make_bank()[:1], now=1000)
        session = advance_question(session)
        self.assertIsNone(current_question(session))
        self.assertTrue(is_session_complete(session))


class SubmitAnswerTests(unittest.TestCase):
    def test_correct_answer_increments_the_users_score(self):
        session = start_session("c1", make_bank(), now=1000)
        next_session, status = submit_answer(session, "u1", 0)  # q1's answerIndex is 0
        self.assertEqual(status, "correct")
        self.assertEqual(next_session["scores"]["u1"], 1)

    def test_incorrect_answer_does_not_increment_the_score(self):
        session = start_session("c1", make_bank(), now=1000)
        next_session, status = submit_answer(session, "u1", 1)  # wrong for q1
        self.assertEqual(status, "incorrect")
        self.assertEqual(next_session["scores"].get("u1", 0), 0)

    def test_a_user_cant_answer_the_same_question_twice(self):
        session = start_session("c1", make_bank(), now=1000)
        first_session, _ = submit_answer(session, "u1", 0)
        second_session, status = submit_answer(first_session, "u1", 0)
        self.assertEqual(status, "already-answered")
        self.assertIs(second_session, first_session)

    def test_different_users_can_both_answer_the_same_question(self):
        session = start_session("c1", make_bank(), now=1000)
        after_u1, _ = submit_answer(session, "u1", 0)
        after_u2, status = submit_answer(after_u1, "u2", 1)
        self.assertEqual(status, "incorrect")
        self.assertEqual(after_u2["scores"]["u1"], 1)

    def test_submitting_after_the_session_is_complete_reports_complete(self):
        session = start_session("c1", make_bank()[:1], now=1000)
        session = advance_question(session)
        result_session, status = submit_answer(session, "u1", 0)
        self.assertEqual(status, "complete")
        self.assertIs(result_session, session)

    def test_does_not_mutate_the_original_session(self):
        session = start_session("c1", make_bank(), now=1000)
        submit_answer(session, "u1", 0)
        self.assertEqual(session["scores"], {})
        self.assertEqual(session["answered_by"], {})


class AdvanceQuestionTests(unittest.TestCase):
    def test_moves_to_the_next_question_and_resets_who_answered(self):
        session = start_session("c1", make_bank(), now=1000)
        answered, _ = submit_answer(session, "u1", 0)
        advanced = advance_question(answered)
        self.assertEqual(current_question(advanced)["id"], "q2")
        self.assertEqual(advanced["answered_by"], {})
        self.assertEqual(advanced["scores"]["u1"], 1)  # score carries over


class StandingsTests(unittest.TestCase):
    def test_sorts_by_score_descending(self):
        session = start_session("c1", make_bank(), now=1000)
        session, _ = submit_answer(session, "u1", 0)  # correct
        session, _ = submit_answer(session, "u2", 0)  # correct
        session = advance_question(session)
        session, _ = submit_answer(session, "u2", 1)  # correct -> u2: 2
        session, _ = submit_answer(session, "u1", 0)  # incorrect -> u1 stays at 1

        result = standings(session)
        self.assertEqual(result, [{"user_id": "u2", "score": 2}, {"user_id": "u1", "score": 1}])

    def test_empty_when_no_one_has_scored(self):
        session = start_session("c1", make_bank(), now=1000)
        self.assertEqual(standings(session), [])


if __name__ == "__main__":
    unittest.main()
