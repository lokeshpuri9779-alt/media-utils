import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from astra_v2.creative import CreativeSkip
from astra_v2.editorial_creative_source import load_editorial_stories
from astra_v2.editorial_approval_manifest import story_digest
from astra_v2.story_forge import catalog
from astra_v2.production_story_gate import candidate_issues

class EditorialCreativeSourceTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(load_editorial_stories(), [])

    def test_partial_configuration_fails_closed(self):
        with patch.dict("os.environ", {"ASTRA_EDITORIAL_STORIES_FILE": "stories.json"}, clear=True):
            with self.assertRaises(CreativeSkip):
                load_editorial_stories()

    def test_missing_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "stories.json").write_text('{"stories":[]}', encoding="utf-8")
            (root / "reviews.json").write_text('{"reviews":[]}', encoding="utf-8")
            env = {"ASTRA_EDITORIAL_STORIES_FILE": str(root / "stories.json"),
                   "ASTRA_EDITORIAL_REVIEWS_FILE": str(root / "reviews.json"),
                   "ASTRA_PUBLISHER_STATE_PATH": str(root / "state.json"),
                   "ASTRA_STORY_HISTORY_PATH": str(root / "history.json")}
            with patch.dict("os.environ", env, clear=True):
                with self.assertRaises(CreativeSkip):
                    load_editorial_stories()

    def test_invalid_review_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "stories.json").write_text('{"stories":[]}', encoding="utf-8")
            (root / "reviews.json").write_text('{broken', encoding="utf-8")
            (root / "state.json").write_text('{}', encoding="utf-8")
            (root / "history.json").write_text('{"stories":[]}', encoding="utf-8")
            env = {"ASTRA_EDITORIAL_STORIES_FILE": str(root / "stories.json"),
                   "ASTRA_EDITORIAL_REVIEWS_FILE": str(root / "reviews.json"),
                   "ASTRA_PUBLISHER_STATE_PATH": str(root / "state.json"),
                   "ASTRA_STORY_HISTORY_PATH": str(root / "history.json")}
            with patch.dict("os.environ", env, clear=True):
                with self.assertRaises(CreativeSkip):
                    load_editorial_stories()

    def test_valid_explicit_review_passes_existing_gate(self):
        candidate = next((s for s in catalog(limit=128) if not candidate_issues(s)), None)
        if candidate is None:
            self.skipTest("No eligible authored story")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "stories.json").write_text(json.dumps({"stories":[candidate]}), encoding="utf-8")
            review = {"content_id":candidate["content_id"],"story_sha256":story_digest(candidate),
                      "decision":"approve","reviewer":"test-reviewer","review_notes":"Test fixture only"}
            (root / "reviews.json").write_text(json.dumps({"reviews":[review]}), encoding="utf-8")
            (root / "state.json").write_text('{}', encoding="utf-8")
            (root / "history.json").write_text('{"stories":[]}', encoding="utf-8")
            env = {"ASTRA_EDITORIAL_STORIES_FILE": str(root / "stories.json"),
                   "ASTRA_EDITORIAL_REVIEWS_FILE": str(root / "reviews.json"),
                   "ASTRA_PUBLISHER_STATE_PATH": str(root / "state.json"),
                   "ASTRA_STORY_HISTORY_PATH": str(root / "history.json")}
            with patch.dict("os.environ", env, clear=True):
                self.assertEqual(load_editorial_stories(), [candidate])

if __name__ == "__main__":
    unittest.main()
