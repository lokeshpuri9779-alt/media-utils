"""Persisted novelty history must block reused structures across calls."""
import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.persisted_plot_proposals import proposals_with_history
from astra_v2.plot_first_proposals import proposals, structural_key


class PersistedStructuralHistoryTests(unittest.TestCase):
    def test_saved_structure_excluded(self):
        original = proposals(limit=1)[0]
        with tempfile.TemporaryDirectory() as directory:
            publisher = Path(directory) / "publisher.json"
            story = Path(directory) / "history.json"
            publisher.write_text("{}", encoding="utf-8")
            story.write_text(json.dumps({"stories": [original]}), encoding="utf-8")
            first = proposals_with_history(limit=3, publisher_path=publisher,
                                           story_path=story)
            second = proposals_with_history(limit=3, publisher_path=publisher,
                                            story_path=story)
            self.assertEqual(first, second)
            self.assertNotIn(structural_key(original),
                             [structural_key(item) for item in first])
            self.assertTrue(all(not item["production_ready"] for item in first))

    def test_invalid_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            story = Path(directory) / "history.json"
            story.write_text('{"stories":"invalid"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                proposals_with_history(limit=1, publisher_path=Path(directory) / "missing.json",
                                       story_path=story)


if __name__ == "__main__":
    unittest.main()
