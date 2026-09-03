import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reminders_store import delete_reminder, insert_reminder, load_all_reminders, mark_reminder_sent, open_store


def sample_reminder(**overrides):
    reminder = {
        "id": "r1",
        "user_id": "u1",
        "channel_id": "c1",
        "guild_id": "g1",
        "message": "boire de l'eau",
        "due_at": 123456.0,
        "created_at": 100.0,
        "sent": False,
    }
    reminder.update(overrides)
    return reminder


class RemindersStoreTests(unittest.TestCase):
    def test_round_trips_a_reminder_through_insert_and_load(self):
        conn = open_store(":memory:")
        insert_reminder(conn, sample_reminder())
        all_reminders = load_all_reminders(conn)
        self.assertEqual(len(all_reminders), 1)
        self.assertEqual(all_reminders[0], sample_reminder())

    def test_guild_id_can_be_none_a_dm_reminder(self):
        conn = open_store(":memory:")
        insert_reminder(conn, sample_reminder(id="r2", guild_id=None))
        [loaded] = load_all_reminders(conn)
        self.assertIsNone(loaded["guild_id"])

    def test_mark_reminder_sent_flips_sent_to_true(self):
        conn = open_store(":memory:")
        insert_reminder(conn, sample_reminder())
        mark_reminder_sent(conn, "r1")
        [loaded] = load_all_reminders(conn)
        self.assertTrue(loaded["sent"])

    def test_delete_reminder_removes_it(self):
        conn = open_store(":memory:")
        insert_reminder(conn, sample_reminder())
        delete_reminder(conn, "r1")
        self.assertEqual(load_all_reminders(conn), [])

    def test_multiple_reminders_persist_independently(self):
        conn = open_store(":memory:")
        insert_reminder(conn, sample_reminder(id="r1"))
        insert_reminder(conn, sample_reminder(id="r2", user_id="u2"))
        all_reminders = load_all_reminders(conn)
        self.assertEqual(len(all_reminders), 2)
        self.assertEqual(sorted(r["id"] for r in all_reminders), ["r1", "r2"])


if __name__ == "__main__":
    unittest.main()
