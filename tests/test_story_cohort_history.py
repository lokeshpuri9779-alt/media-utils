import unittest
from astra_v2.story_cohort_history import append, LIMIT


class CohortHistoryTests(unittest.TestCase):
    def setUp(self):
        self.cohort = {"new": {"total": 100, "issue:narrative_duplicate": 4}, "approved_for_production": 0, "publication_enabled": False}

    def test_append_and_idempotency(self):
        first = append({"runs": []}, self.cohort, "123", "1", "abc")
        self.assertEqual(first["runs"][0]["duplicate_rate"], .04)
        self.assertEqual(append(first, self.cohort, "123", "1", "abc"), first)

    def test_bounded(self):
        history = {"runs": []}
        for i in range(LIMIT + 5):
            history = append(history, self.cohort, str(i), "1", "abc")
        self.assertEqual(len(history["runs"]), LIMIT)
        self.assertEqual(history["runs"][0]["run_id"], "5")

    def test_empty_cohort_and_safety(self):
        c = dict(self.cohort, new={"total": 0})
        self.assertIsNone(append({"runs": []}, c, "1", "1", "abc")["runs"][0]["duplicate_rate"])
        with self.assertRaises(ValueError):
            append({"runs": []}, dict(self.cohort, publication_enabled=True), "1", "1", "abc")
