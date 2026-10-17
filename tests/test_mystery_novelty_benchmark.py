import unittest
from astra_v2.mystery_novelty_benchmark import benchmark


class MysteryNoveltyBenchmarkTests(unittest.TestCase):
    def test_deterministic_and_read_only(self):
        first = benchmark(history_count=12, sample_start=200, sample_count=8)
        self.assertEqual(first, benchmark(history_count=12, sample_start=200, sample_count=8))
        self.assertEqual(first["publication_approved"], 0)
        self.assertFalse(first["history_mutated"])
        self.assertEqual(first["duplicate_rate"], round(first["duplicate_count"] / 8, 4))
        self.assertEqual(first["duplicate_count"], len(first["duplicate_indices"]))

    def test_reject_overlapping_windows(self):
        with self.assertRaises(ValueError):
            benchmark(history_count=20, sample_start=10, sample_count=5)

    def test_reject_invalid_sizes(self):
        with self.assertRaises(ValueError):
            benchmark(history_count=0)
        with self.assertRaises(ValueError):
            benchmark(sample_count=1001)


if __name__ == "__main__":
    unittest.main()
