import json
import os
import unittest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "questions.json")

with open(DATA_PATH, encoding="utf-8") as f:
    QUESTIONS = json.load(f)


class QuestionsDataTests(unittest.TestCase):
    def test_has_a_reasonable_number_of_questions(self):
        self.assertGreaterEqual(len(QUESTIONS), 20)

    def test_every_question_has_exactly_4_choices_and_a_valid_answer_index(self):
        for q in QUESTIONS:
            self.assertEqual(len(q["choices"]), 4, f"{q['id']} should have 4 choices")
            self.assertTrue(0 <= q["answerIndex"] < 4, f"{q['id']} answerIndex out of range")

    def test_every_id_is_unique(self):
        ids = [q["id"] for q in QUESTIONS]
        self.assertEqual(len(set(ids)), len(ids))

    def test_has_at_least_3_categories(self):
        categories = {q["category"] for q in QUESTIONS}
        self.assertGreaterEqual(len(categories), 3)


if __name__ == "__main__":
    unittest.main()
