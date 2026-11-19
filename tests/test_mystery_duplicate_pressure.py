import unittest
from astra_v2.autonomous_story_proposals import (
    CAUSAL_PATHS, MYSTERIES, NARRATIVE_ARCHITECTURES, PRESSURE_ARCS,
)
from astra_v2.mystery_novelty_benchmark import (
    diagnose_duplicate_pressure, measure_sequential_rejection_reasons,
)


class DuplicatePressureTests(unittest.TestCase):
    def test_diagnostics_match_existing_novelty_decisions(self):
        for start, count in ((0, 40), (1000, 40)):
            result = diagnose_duplicate_pressure(start, count)
            baseline = measure_sequential_rejection_reasons(start, count)
            self.assertEqual(result["accepted_count"], baseline["reason_counts"]["accepted"])
            self.assertEqual(result["rejected_count"], count - result["accepted_count"])
            self.assertEqual(result["publication_approved"], 0)
            self.assertFalse(result["history_mutated"])
            self.assertEqual(sum(x["count"] for x in result["collisions"]), result["rejected_count"])
            for row in result["collisions"]:
                self.assertIn(row["mystery"], range(len(MYSTERIES)))
                self.assertIn(row["causal_path"], range(len(CAUSAL_PATHS)))
                self.assertIn(row["pressure_arc"], range(len(PRESSURE_ARCS)))
                self.assertIn(row["architecture"], range(len(NARRATIVE_ARCHITECTURES)))
                self.assertNotIn("plot", row)

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            diagnose_duplicate_pressure(-1, 10)


if __name__ == "__main__":
    unittest.main()
