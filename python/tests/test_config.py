import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import load_moderation_config


class LoadModerationConfigTests(unittest.TestCase):
    def test_parses_a_comma_separated_banned_word_list_trimming_whitespace(self):
        config = load_moderation_config({"BANNED_WORDS": "badword,  spam-link ,another"})
        self.assertEqual(config["banned_words"], ["badword", "spam-link", "another"])

    def test_empty_unset_banned_words_yields_an_empty_list(self):
        self.assertEqual(load_moderation_config({})["banned_words"], [])
        self.assertEqual(load_moderation_config({"BANNED_WORDS": ""})["banned_words"], [])

    def test_filters_out_empty_entries_from_trailing_commas(self):
        config = load_moderation_config({"BANNED_WORDS": "badword,,other,"})
        self.assertEqual(config["banned_words"], ["badword", "other"])

    def test_defaults_flood_and_warn_thresholds_when_unset(self):
        config = load_moderation_config({})
        self.assertEqual(config["flood"], {"max_messages": 5, "window_ms": 10_000})
        self.assertEqual(config["warn_thresholds"], {"mute": 3, "kick": 5})

    def test_reads_numeric_overrides_from_env(self):
        config = load_moderation_config(
            {
                "FLOOD_MAX_MESSAGES": "8",
                "FLOOD_WINDOW_MS": "5000",
                "WARN_MUTE_THRESHOLD": "2",
                "WARN_KICK_THRESHOLD": "4",
            }
        )
        self.assertEqual(config["flood"], {"max_messages": 8, "window_ms": 5000})
        self.assertEqual(config["warn_thresholds"], {"mute": 2, "kick": 4})

    def test_falls_back_to_defaults_on_non_numeric_overrides(self):
        config = load_moderation_config({"FLOOD_MAX_MESSAGES": "not-a-number"})
        self.assertEqual(config["flood"]["max_messages"], 5)


if __name__ == "__main__":
    unittest.main()
