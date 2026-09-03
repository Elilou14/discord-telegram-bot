import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from moderation_logic import (
    add_warning,
    contains_banned_word,
    evaluate_message,
    is_flooding,
    recommended_action,
    warning_count,
)


class ContainsBannedWordTests(unittest.TestCase):
    def setUp(self):
        self.banned_words = ["badword", "spam-link"]

    def test_matches_case_insensitively(self):
        self.assertTrue(contains_banned_word("this has a BadWord in it", self.banned_words))

    def test_matches_whole_words_only_not_substrings(self):
        self.assertFalse(contains_banned_word("badwording is not the same word", self.banned_words))

    def test_no_match_returns_false(self):
        self.assertFalse(contains_banned_word("a perfectly normal message", self.banned_words))

    def test_escapes_regex_special_characters_in_the_banned_word(self):
        self.assertTrue(contains_banned_word("check out spam-link now", self.banned_words))
        self.assertFalse(contains_banned_word("spam link (without the dash)", self.banned_words))

    def test_empty_banned_list_never_matches(self):
        self.assertFalse(contains_banned_word("badword", []))


class IsFloodingTests(unittest.TestCase):
    def test_false_when_there_are_fewer_messages_than_the_threshold(self):
        self.assertFalse(is_flooding([0, 100, 200], max_messages=5, window_ms=10_000))

    def test_true_when_max_messages_arrive_within_the_window(self):
        timestamps = [0, 100, 200, 300, 400]
        self.assertTrue(is_flooding(timestamps, max_messages=5, window_ms=10_000))

    def test_false_when_the_same_count_is_spread_across_a_longer_time(self):
        timestamps = [0, 5000, 10_000, 15_000, 20_000]
        self.assertFalse(is_flooding(timestamps, max_messages=5, window_ms=10_000))

    def test_only_looks_at_the_most_recent_max_messages(self):
        # The first two are ancient; the last five are within the window.
        timestamps = [-100_000, -90_000, 0, 100, 200, 300, 400]
        self.assertTrue(is_flooding(timestamps, max_messages=5, window_ms=10_000))


class EvaluateMessageTests(unittest.TestCase):
    def test_a_banned_word_means_delete_even_without_flooding(self):
        result = evaluate_message(
            "contains badword here", 1000, recent_timestamps=[], banned_words=["badword"]
        )
        self.assertEqual(result, {"action": "delete", "reason": "mot-interdit"})

    def test_flooding_without_a_banned_word_means_mute(self):
        result = evaluate_message(
            "hello",
            400,
            recent_timestamps=[0, 100, 200, 300],
            banned_words=["badword"],
            flood_options={"max_messages": 5, "window_ms": 10_000},
        )
        self.assertEqual(result, {"action": "mute", "reason": "flood"})

    def test_banned_word_takes_priority_over_flooding(self):
        result = evaluate_message(
            "badword",
            400,
            recent_timestamps=[0, 100, 200, 300],
            banned_words=["badword"],
            flood_options={"max_messages": 5, "window_ms": 10_000},
        )
        self.assertEqual(result["action"], "delete")

    def test_a_clean_non_flooding_message_means_no_action(self):
        result = evaluate_message("hello there", 1000)
        self.assertEqual(result, {"action": "none", "reason": None})


class WarningsTests(unittest.TestCase):
    def test_add_warning_appends_without_mutating_the_original_list(self):
        counter = {"n": 0}

        def fixed_id():
            counter["n"] += 1
            return f"warn-{counter['n']}"

        warnings = []
        next_warnings = add_warning(warnings, "u1", "mod1", "spam", now=1000, id_generator=fixed_id)
        self.assertEqual(len(next_warnings), 1)
        self.assertEqual(len(warnings), 0)
        self.assertEqual(next_warnings[0]["user_id"], "u1")

    def test_warning_count_only_counts_the_given_user(self):
        warnings = [
            {"user_id": "u1", "reason": "a"},
            {"user_id": "u2", "reason": "b"},
            {"user_id": "u1", "reason": "c"},
        ]
        self.assertEqual(warning_count(warnings, "u1"), 2)
        self.assertEqual(warning_count(warnings, "u2"), 1)
        self.assertEqual(warning_count(warnings, "u3"), 0)


class RecommendedActionTests(unittest.TestCase):
    def test_below_threshold_none(self):
        self.assertEqual(recommended_action(1), "none")
        self.assertEqual(recommended_action(2), "none")

    def test_mute_threshold(self):
        self.assertEqual(recommended_action(3), "mute")
        self.assertEqual(recommended_action(4), "mute")

    def test_kick_threshold_and_beyond(self):
        self.assertEqual(recommended_action(5), "kick")
        self.assertEqual(recommended_action(10), "kick")

    def test_custom_thresholds(self):
        self.assertEqual(recommended_action(2, {"mute": 2, "kick": 4}), "mute")
        self.assertEqual(recommended_action(4, {"mute": 2, "kick": 4}), "kick")


if __name__ == "__main__":
    unittest.main()
