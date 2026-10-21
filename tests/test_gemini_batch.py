import unittest
from astra_v2.gemini_batch import generate_batch


class BatchTests(unittest.TestCase):
    def test_unique_inventory(self):
        def fake(ids, titles, history):
            n = len(history)
            return {"content_id": "story-" + str(n), "title": "Story " + str(n)}
        result = generate_batch(4, generator=fake)
        self.assertEqual(result["generated"], 4)
        self.assertEqual(result["status"], "unreviewed")

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            generate_batch(51)

    def test_rate_limit_stops(self):
        def fail(*args):
            raise RuntimeError("Gemini HTTP 429")
        result = generate_batch(10, generator=fail)
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["generated"], 0)


if __name__ == "__main__":
    unittest.main()
