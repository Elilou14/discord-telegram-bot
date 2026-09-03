import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from telegram_format import (
    build_quiz_keyboard,
    build_quiz_message,
    format_reminder_fired,
    format_reminder_list,
    format_standings,
)

SAMPLE_QUESTION = {
    "id": "q1",
    "category": "geo",
    "question": "Capitale de la France ?",
    "choices": ["Lyon", "Paris", "Marseille", "Nice"],
    "answerIndex": 1,
}


class BuildQuizMessageTests(unittest.TestCase):
    def test_includes_the_question_number_text_and_lettered_choices(self):
        text = build_quiz_message(SAMPLE_QUESTION, 0, 5)
        self.assertIn("Question 1/5", text)
        self.assertIn("Capitale de la France ?", text)
        self.assertIn("A. Lyon", text)
        self.assertIn("B. Paris", text)
        self.assertIn("D. Nice", text)


class BuildQuizKeyboardTests(unittest.TestCase):
    def test_one_row_with_4_buttons_callback_data_carries_the_session_and_choice_index(self):
        markup = build_quiz_keyboard(SAMPLE_QUESTION, "session-1")
        data = markup.to_dict()
        self.assertEqual(len(data["inline_keyboard"]), 1)
        row = data["inline_keyboard"][0]
        self.assertEqual(len(row), 4)
        self.assertEqual(
            [b["callback_data"] for b in row],
            ["quiz:session-1:0", "quiz:session-1:1", "quiz:session-1:2", "quiz:session-1:3"],
        )
        self.assertEqual([b["text"] for b in row], ["A", "B", "C", "D"])


class FormatReminderFiredTests(unittest.TestCase):
    def test_includes_the_message(self):
        text = format_reminder_fired({"message": "boire de l'eau"})
        self.assertIn("boire de l'eau", text)


class FormatReminderListTests(unittest.TestCase):
    def test_empty_list_has_a_friendly_message(self):
        self.assertEqual(format_reminder_list([]), "Vous n'avez aucun rappel actif.")

    def test_lists_each_reminder_with_a_short_id(self):
        text = format_reminder_list([{"id": "abcdefgh12345", "message": "test", "due_at": 1_000_000.0}])
        self.assertIn("test", text)
        self.assertIn("abcdefgh", text)
        self.assertNotIn("12345", text)  # only the first 8 chars of the id


class FormatStandingsTests(unittest.TestCase):
    def test_empty_standings_has_a_friendly_message(self):
        self.assertEqual(format_standings([], lambda uid: uid), "Personne n'a encore marque de points.")

    def test_lists_each_entry_with_a_resolved_display_name_and_pluralized_points(self):
        text = format_standings(
            [{"user_id": "u1", "score": 3}, {"user_id": "u2", "score": 1}],
            lambda uid: f"@{uid}",
        )
        self.assertIn("@u1 -- 3 pts", text)
        self.assertIn("@u2 -- 1 pt", text)
        self.assertNotIn("1 pts", text)  # singular for exactly 1


if __name__ == "__main__":
    unittest.main()
