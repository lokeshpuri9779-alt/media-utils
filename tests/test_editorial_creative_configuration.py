"""Regression tests for opt-in editorial source configuration."""
import os
import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.story_forge import catalog
from astra_v2.production_story_gate import candidate_issues
from astra_v2.editorial_approval_manifest import story_digest
from unittest.mock import patch

from astra_v2.creative import CreativeSkip
from astra_v2.editorial_creative_source import load_editorial_stories


class EditorialCreativeConfigurationTests(unittest.TestCase):
    def test_approved_authored_story_enters_creative_source(self):
        story = next((s for s in catalog(limit=128) if not candidate_issues(s)), None)
        if story is None:
            self.skipTest("No authored story passes current production gate")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "stories.json").write_text(json.dumps({"stories": [story]}), encoding="utf-8")
            review = {"content_id": story["content_id"], "story_sha256": story_digest(story),
                      "decision": "approve", "reviewer": "ci-fixture",
                      "review_notes": "Synthetic test approval, not a production decision"}
            (root / "reviews.json").write_text(json.dumps({"reviews": [review]}), encoding="utf-8")
            (root / "state.json").write_text('{"published":{},"pending":{},"reserved":{},"rejected":{}}', encoding="utf-8")
            (root / "history.json").write_text('{"stories":[]}', encoding="utf-8")
            env = {"ASTRA_EDITORIAL_STORIES_FILE": str(root / "stories.json"),
                   "ASTRA_EDITORIAL_REVIEWS_FILE": str(root / "reviews.json"),
                   "ASTRA_PUBLISHER_STATE_PATH": str(root / "state.json"),
                   "ASTRA_STORY_HISTORY_PATH": str(root / "history.json")}
            with patch.dict(os.environ, env):
                self.assertEqual(load_editorial_stories(), [story])
            (root / "history.json").write_text(json.dumps({"stories": [
                {"content_id": "prior-story", "plot_fingerprint": story["plot_fingerprint"]}
            ]}), encoding="utf-8")
            with patch.dict(os.environ, env):
                self.assertEqual(load_editorial_stories(), [])

    def test_malformed_review_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "stories.json").write_text('{"stories":[]}', encoding="utf-8")
            (root / "reviews.json").write_text("{invalid", encoding="utf-8")
            (root / "state.json").write_text('{}', encoding="utf-8")
            (root / "history.json").write_text('{"stories":[]}', encoding="utf-8")
            env = {"ASTRA_EDITORIAL_STORIES_FILE": str(root / "stories.json"),
                   "ASTRA_EDITORIAL_REVIEWS_FILE": str(root / "reviews.json"),
                   "ASTRA_PUBLISHER_STATE_PATH": str(root / "state.json"),
                   "ASTRA_STORY_HISTORY_PATH": str(root / "history.json")}
            with patch.dict(os.environ, env):
                with self.assertRaisesRegex(CreativeSkip, "editorial_intake_unavailable"):
                    load_editorial_stories()

    def test_partial_editorial_configuration_fails_closed(self):
        with patch.dict(os.environ, {
            "ASTRA_EDITORIAL_STORIES_FILE": "missing-stories.json",
            "ASTRA_EDITORIAL_REVIEWS_FILE": "",
        }):
            with self.assertRaisesRegex(CreativeSkip, "editorial_intake_incomplete_configuration"):
                load_editorial_stories()

    def test_missing_history_fails_closed(self):
        with patch.dict(os.environ, {
            "ASTRA_EDITORIAL_STORIES_FILE": "/tmp/absent-editorial-stories.json",
            "ASTRA_EDITORIAL_REVIEWS_FILE": "/tmp/absent-editorial-reviews.json",
            "ASTRA_PUBLISHER_STATE_PATH": "/tmp/absent-editorial-state.json",
            "ASTRA_STORY_HISTORY_PATH": "/tmp/absent-editorial-history.json",
        }):
            with self.assertRaisesRegex(CreativeSkip, "editorial_intake_unavailable"):
                load_editorial_stories()


if __name__ == "__main__":
    unittest.main()
