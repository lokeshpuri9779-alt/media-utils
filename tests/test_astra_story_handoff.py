"""Real Studio/publisher metadata round-trip without encoding or uploads."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.anthology_stories import catalog as anthology_catalog
from astra_v2.publication_quality import publication_rejection
from astra_v2.story_handoff import approved_story_context
from astra_v2.preload_queue import prepare


class StoryHandoffTests(unittest.TestCase):
    @staticmethod
    def _story():
        return next(story for story in anthology_catalog()
                    if story["title"] == "The Otter's Floating Library")

    def test_beats_preserved_without_inventing_a_visual(self):
        source = self._story()
        handoff = approved_story_context(source)
        self.assertEqual(handoff["story_beats"], source["story_beats"])
        self.assertTrue(all(beat.get("speech") and beat.get("visual")
                            for beat in handoff["story_beats"]))
        handoff["story_beats"][0]["visual"] = ""
        self.assertTrue(source["story_beats"][0]["visual"],
                        "Handoff should never mutate the approved source")

    @patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"})
    def test_real_story_survives_serialized_archive_and_publisher_gate(self):
        source = self._story()
        candidate = {
            "content_id": source["content_id"], "title": source["title"],
            "genre": source["genre"], "description": "Original reviewed fictional story",
            "synthetic": True, "format": "short", "renderer": "studio-7.3.1",
            **approved_story_context(source),
        }
        self.assertIsNone(publication_rejection(candidate))
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "render.mp4"
            video.write_bytes(b"synthetic-test-data-not-real-mp4")
            with patch("astra_v2.creative.inspect_video", return_value={"seconds": 15.23}):
                archive = prepare(video, candidate)
            restored = json.loads((archive / "candidate.json").read_text(encoding="utf-8"))
            self.assertEqual(restored["story_beats"], source["story_beats"])
            self.assertEqual(restored["kind"], source["kind"])
            self.assertEqual(restored["production_ready"], True)
            self.assertEqual(restored["question"], source["question"])
            self.assertEqual(restored["answer"], source["answer"])
            self.assertIsNone(publication_rejection(restored),
                              "Publisher should revalidate the exact original scenes")

    @patch.dict(os.environ, {"ASTRA_UNIFIED_STORY_ENGINE": "1"})
    def test_dropped_visual_stays_rejected(self):
        source = self._story()
        candidate = {
            "content_id": source["content_id"], "title": source["title"],
            "genre": "fiction", **approved_story_context(source),
        }
        candidate["story_beats"][1].pop("visual")
        rejection = publication_rejection(candidate)
        self.assertIsNotNone(rejection)
        self.assertIn("renderer_incompatible:", rejection)


if __name__ == "__main__":
    unittest.main()
