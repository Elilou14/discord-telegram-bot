import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reminders_logic import (
    active_reminders_for_user,
    cancel_reminder,
    create_reminder,
    due_reminders,
    mark_sent,
    parse_duration,
    parse_when,
)


class ParseDurationTests(unittest.TestCase):
    def test_parses_seconds_minutes_hours_days(self):
        self.assertEqual(parse_duration("45s"), 45)
        self.assertEqual(parse_duration("10m"), 600)
        self.assertEqual(parse_duration("2h"), 7200)
        self.assertEqual(parse_duration("1d"), 86400)

    def test_rejects_unknown_formats(self):
        self.assertIsNone(parse_duration("soon"))
        self.assertIsNone(parse_duration("10"))
        self.assertIsNone(parse_duration("10y"))
        self.assertIsNone(parse_duration(""))


class ParseWhenTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, 12, 0, 0)

    def test_relative_duration_resolves_against_now(self):
        result = parse_when("10m", self.now)
        self.assertEqual((result - self.now).total_seconds(), 600)

    def test_absolute_datetime(self):
        result = parse_when("2026-03-15 09:30", self.now)
        self.assertEqual((result.year, result.month, result.day, result.hour, result.minute), (2026, 3, 15, 9, 30))

    def test_absolute_datetime_accepts_a_t_separator(self):
        result = parse_when("2026-03-15T09:30", self.now)
        self.assertIsNotNone(result)

    def test_rejects_out_of_range_month_day_hour_minute(self):
        self.assertIsNone(parse_when("2026-13-01 10:00", self.now))
        self.assertIsNone(parse_when("2026-01-32 10:00", self.now))
        self.assertIsNone(parse_when("2026-01-01 24:00", self.now))
        self.assertIsNone(parse_when("2026-01-01 10:60", self.now))

    def test_rejects_garbage(self):
        self.assertIsNone(parse_when("whenever", self.now))


class CreateReminderTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, 12, 0, 0)
        self.fixed_id = lambda: "fixed-id"

    def test_builds_a_valid_reminder(self):
        reminder = create_reminder(
            "u1", "c1", "  boire de l'eau  ", "10m", now=self.now, id_generator=self.fixed_id
        )
        self.assertEqual(reminder["id"], "fixed-id")
        self.assertEqual(reminder["user_id"], "u1")
        self.assertEqual(reminder["message"], "boire de l'eau")
        self.assertEqual(reminder["due_at"], (self.now.timestamp() + 600))
        self.assertFalse(reminder["sent"])

    def test_rejects_an_empty_message(self):
        with self.assertRaises(ValueError):
            create_reminder("u1", "c1", "   ", "10m", now=self.now, id_generator=self.fixed_id)

    def test_rejects_an_unparseable_when(self):
        with self.assertRaises(ValueError):
            create_reminder("u1", "c1", "hey", "whenever", now=self.now, id_generator=self.fixed_id)

    def test_rejects_a_when_already_in_the_past(self):
        with self.assertRaises(ValueError):
            create_reminder("u1", "c1", "hey", "2020-01-01 00:00", now=self.now, id_generator=self.fixed_id)


class ActiveRemindersForUserTests(unittest.TestCase):
    def test_filters_to_the_users_own_unsent_reminders_soonest_first(self):
        reminders = [
            {"id": "a", "user_id": "u1", "due_at": 300, "sent": False},
            {"id": "b", "user_id": "u2", "due_at": 100, "sent": False},
            {"id": "c", "user_id": "u1", "due_at": 100, "sent": False},
            {"id": "d", "user_id": "u1", "due_at": 50, "sent": True},
        ]
        result = active_reminders_for_user(reminders, "u1")
        self.assertEqual([r["id"] for r in result], ["c", "a"])


class DueRemindersTests(unittest.TestCase):
    def test_returns_unsent_reminders_whose_time_has_come(self):
        now = datetime.fromtimestamp(1.0)
        reminders = [
            {"id": "a", "due_at": 0.5, "sent": False},
            {"id": "b", "due_at": 1.5, "sent": False},
            {"id": "c", "due_at": 0.5, "sent": True},
        ]
        result = due_reminders(reminders, now)
        self.assertEqual([r["id"] for r in result], ["a"])


class CancelReminderTests(unittest.TestCase):
    def test_removes_the_matching_pending_reminder(self):
        reminders = [
            {"id": "a", "user_id": "u1", "sent": False},
            {"id": "b", "user_id": "u1", "sent": False},
        ]
        result = cancel_reminder(reminders, "a", "u1")
        self.assertEqual([r["id"] for r in result], ["b"])

    def test_no_op_for_an_unknown_id(self):
        reminders = [{"id": "a", "user_id": "u1", "sent": False}]
        self.assertIs(cancel_reminder(reminders, "missing", "u1"), reminders)

    def test_no_op_for_another_users_reminder(self):
        reminders = [{"id": "a", "user_id": "u1", "sent": False}]
        self.assertIs(cancel_reminder(reminders, "a", "u2"), reminders)

    def test_no_op_for_an_already_sent_reminder(self):
        reminders = [{"id": "a", "user_id": "u1", "sent": True}]
        self.assertIs(cancel_reminder(reminders, "a", "u1"), reminders)


class MarkSentTests(unittest.TestCase):
    def test_marks_the_matching_reminder_sent_without_mutating_others(self):
        reminders = [{"id": "a", "sent": False}, {"id": "b", "sent": False}]
        result = mark_sent(reminders, "a")
        self.assertTrue(result[0]["sent"])
        self.assertFalse(result[1]["sent"])
        self.assertFalse(reminders[0]["sent"])  # original untouched


if __name__ == "__main__":
    unittest.main()
