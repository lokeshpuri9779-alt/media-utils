import tempfile
import unittest
from pathlib import Path
from astra_v2.story_history import read_history, evaluate_and_record

def story(words):
    return {"title": words, "scenes": [{"narration": words, "action": "approach"}]}

class StoryHistoryTests(unittest.TestCase):
    def test_selection_skips_repeated_batch_before_finding_new_story(self):
        from astra_v2.story_history import select_novel_stories
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            old = story("A missing lantern returns to its owner.")
            new = story("An astronomer discovers a distant galaxy.")
            evaluate_and_record([old], path)
            result = select_novel_stories([[old, old], [new]], path, limit=1)
            self.assertEqual(result["considered"], 3)
            self.assertEqual(result["stories"], [new])
            self.assertEqual(result["shortfall"], 0)

    def test_history_aware_selection_rejects_repeats(self):
        from astra_v2.story_history import select_novel_stories
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            example = story("A missing lantern returns to its owner.")
            evaluate_and_record([example], path)
            result = select_novel_stories([[example, example]], path, limit=2)
            self.assertEqual(result["considered"], 2)
            self.assertEqual(result["shortfall"], 2)
            self.assertEqual(result["stories"], [])
            self.assertFalse(result["publication_allowed"])

    def test_history_aware_selection_accepts_distinct_candidates(self):
        from astra_v2.story_history import select_novel_stories
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            first = story("A missing lantern returns to its owner.")
            second = story("A broken clock is repaired in a workshop.")
            result = select_novel_stories([[first, second]], path, limit=2)
            self.assertEqual(result["considered"], 2)
            self.assertEqual(len(result["stories"]), 2)
            self.assertEqual(result["shortfall"], 0)

    def test_persists_and_rejects_across_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            first = evaluate_and_record([story("A robot finds a missing key")], path)
            second = evaluate_and_record([story("A robot finds a missing key")], path)
            self.assertEqual(first["recorded"], 1)
            self.assertEqual(second["recorded"], 0)
            self.assertEqual(second["near_duplicates"], 1)
            self.assertEqual(len(read_history(path)), 1)
            self.assertFalse(second["publication_allowed"])

    def test_corrupt_history_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            path.write_text('{"bad":', encoding="utf-8")
            with self.assertRaises(ValueError):
                evaluate_and_record([story("new story")], path)

    def test_malformed_history_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            path.write_text('{"scenes": []}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_history(path)

    def test_missing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(read_history(Path(directory) / "missing.jsonl"), [])

if __name__ == "__main__":
    unittest.main()
