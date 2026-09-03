import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from moderation_store import insert_warning, load_all_warnings, open_moderation_store


def sample_warning(**overrides):
    warning = {
        "id": "w1",
        "user_id": "u1",
        "moderator_id": "mod1",
        "reason": "spam",
        "at": 1000.0,
    }
    warning.update(overrides)
    return warning


class ModerationStoreTests(unittest.TestCase):
    def test_round_trips_a_warning_through_insert_and_load(self):
        conn = open_moderation_store(":memory:")
        insert_warning(conn, sample_warning())
        all_warnings = load_all_warnings(conn)
        self.assertEqual(len(all_warnings), 1)
        self.assertEqual(all_warnings[0]["user_id"], "u1")
        self.assertEqual(all_warnings[0]["reason"], "spam")

    def test_multiple_warnings_for_the_same_user_persist_independently(self):
        conn = open_moderation_store(":memory:")
        insert_warning(conn, sample_warning(id="w1"))
        insert_warning(conn, sample_warning(id="w2", reason="insulte"))
        all_warnings = load_all_warnings(conn)
        self.assertEqual(len(all_warnings), 2)
        self.assertEqual(sorted(w["reason"] for w in all_warnings), ["insulte", "spam"])


if __name__ == "__main__":
    unittest.main()
