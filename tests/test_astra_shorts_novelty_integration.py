"""Verify Shorts narration survives candidate and publisher history handoffs."""
import unittest
from pathlib import Path
from astra_v2.shorts_novelty import is_near_duplicate


class NoveltyIntegrationTests(unittest.TestCase):
    def test_saved_history_narration_blocks_rephrased_story(self):
        previous = [{"plot_fingerprint": "old", "story_beats": [
            {"speech": "The little robot found a broken bridge and repaired it before sunrise."}]}]
        candidate = {"plot_fingerprint": "new", "story_beats": [
            {"speech": "The little robot found a damaged bridge and repaired it before sunrise."}]}
        self.assertTrue(is_near_duplicate(candidate, previous))

    def test_history_without_narration_does_not_invent_similarity(self):
        candidate = {"plot_fingerprint": "new", "story_beats": [{"speech": "A robot repaired a bridge."}]}
        self.assertFalse(is_near_duplicate(candidate, [{"plot_fingerprint": "old"}]))

    def test_runtime_handoffs_preserve_narration(self):
        creative = Path("astra_v2/creative.py").read_text()
        publisher = Path("astra_v2/run.py").read_text()
        self.assertIn('"story_beats": meta.get("story_beats") or []', creative)
        self.assertIn('history_narratives.append(record)', creative)
        self.assertIn('not is_near_duplicate(story, history_narratives)', creative)
        self.assertGreaterEqual(publisher.count('"story_beats":'), 3)


if __name__ == "__main__":
    unittest.main()
