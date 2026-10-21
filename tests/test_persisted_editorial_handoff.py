import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from astra_v2.editorial_creative_source import load_editorial_stories
from astra_v2.creative import CreativeSkip


class PersistentEditorialHandoffTests(unittest.TestCase):
    def test_missing_one_persistent_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "publisher.json").write_text("{}")
            (base / "history.json").write_text("{}")
            (base / "stories.json").write_text('{"stories":[]}')
            (base / "reviews.json").write_text('{"reviews":[]}')
            (base / "persist-stories.json").write_text('{"stories":[]}')
            env = {
                "ASTRA_EDITORIAL_STORIES_FILE": str(base / "stories.json"),
                "ASTRA_EDITORIAL_REVIEWS_FILE": str(base / "reviews.json"),
                "ASTRA_PUBLISHER_STATE_PATH": str(base / "publisher.json"),
                "ASTRA_STORY_HISTORY_PATH": str(base / "history.json"),
                "ASTRA_PERSISTED_EDITORIAL_STORIES_FILE": str(base / "persist-stories.json"),
                "ASTRA_PERSISTED_EDITORIAL_REVIEWS_FILE": str(base / "persist-reviews.json"),
            }
            with patch.dict(os.environ, env):
                with patch("astra_v2.proposal_history.load_history", return_value=[]):
                    with self.assertRaisesRegex(CreativeSkip, "incomplete_pair"):
                        load_editorial_stories()

    def test_valid_persistent_pair_runs_same_approval_gate(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for name, payload in {
                "publisher.json": {}, "history.json": {},
                "stories.json": {"stories":[]}, "reviews.json":{"reviews":[]},
                "persist-stories.json":{"stories":[]}, "persist-reviews.json":{"reviews":[]},
            }.items():
                (base / name).write_text(json.dumps(payload))
            env = {
                "ASTRA_EDITORIAL_STORIES_FILE": str(base / "stories.json"),
                "ASTRA_EDITORIAL_REVIEWS_FILE": str(base / "reviews.json"),
                "ASTRA_PUBLISHER_STATE_PATH": str(base / "publisher.json"),
                "ASTRA_STORY_HISTORY_PATH": str(base / "history.json"),
                "ASTRA_PERSISTED_EDITORIAL_STORIES_FILE": str(base / "persist-stories.json"),
                "ASTRA_PERSISTED_EDITORIAL_REVIEWS_FILE": str(base / "persist-reviews.json"),
            }
            with patch.dict(os.environ, env):
                with patch("astra_v2.proposal_history.load_history", return_value=[]):
                    self.assertEqual(load_editorial_stories(), [])


if __name__ == "__main__":
    unittest.main()
