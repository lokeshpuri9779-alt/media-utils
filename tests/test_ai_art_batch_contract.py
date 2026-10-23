"""Offline contract checks for the real editorial-to-image batch path."""
import json
import unittest
from pathlib import Path

from astra_v2.story_art_direction import illustration_requests


class AIArtworkBatchContractTests(unittest.TestCase):
    def test_existing_editorial_stories_produce_scene_requests(self):
        source = Path("editorial/reviewed_stories.json")
        data = json.loads(source.read_text(encoding="utf-8"))
        self.assertIsInstance(data.get("stories"), list)
        eligible = [s for s in data["stories"] if isinstance(s, dict)
                    and s.get("production_ready") and s.get("content_id")
                    and s.get("story_beats")]
        self.assertTrue(eligible, "No eligible story in the checked-in editorial fixture")
        for story in eligible:
            requests = illustration_requests(story)
            self.assertEqual(len(requests), len(story["story_beats"]))
            self.assertEqual([r["scene_id"] for r in requests],
                             [f"{i:03d}" for i in range(1, len(requests) + 1)])
            self.assertTrue(all(r["story_content_id"] == story["content_id"]
                                for r in requests))

    def test_manual_batch_is_fail_closed_and_does_not_publish(self):
        workflow = Path(".github/workflows/astra-ai-art-batch.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("inputs.confirm_free == 'FREE'", workflow)
        self.assertIn("ASTRA_OMNI_IMAGE_ALLOW_PAID: '0'", workflow)
        self.assertIn("preproduce(", workflow)
        self.assertIn("review_only.json", workflow)
        self.assertNotIn("youtube-upload", workflow.lower())
        self.assertNotIn("publish_video(", workflow)


if __name__ == "__main__":
    unittest.main()
