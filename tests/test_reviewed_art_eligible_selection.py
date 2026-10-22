import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.reviewed_art_eligible_selection import select_eligible_art_story
from astra_v2.reviewed_art_lane import story_lane
from astra_v2.reviewed_art_receipt_index import INDEX_SCHEMA
from astra_v2.remote_reviewed_art import SCHEMA as ART_SCHEMA


class Store:
    def __init__(self, path):
        self.path = path
    def verify(self, record):
        return self.path


class EligibleArtSelectionTests(unittest.TestCase):
    def test_only_eligible_story_in_own_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            entries = {"approved": {"schema": ART_SCHEMA, "publication_triggered": False,
                                     "bundle": {"sha256": "a" * 64, "bytes": 1}}}
            path.write_text(json.dumps({"schema": INDEX_SCHEMA, "entries": entries}))
            index = {"schema": INDEX_SCHEMA, "publication_triggered": False,
                     "index": {"sha256": "b" * 64, "bytes": 100}}
            story = {"content_id": "approved", "production_ready": True}
            lane = story_lane(story, 4)
            self.assertEqual(select_eligible_art_story(index, Store(path), [story], lane, 4), "approved")
            self.assertIsNone(select_eligible_art_story(index, Store(path), [story], (lane + 1) % 4, 4))
            self.assertIsNone(select_eligible_art_story(index, Store(path), [], lane, 4))
            self.assertIsNone(select_eligible_art_story(index, Store(path), [{"content_id": "approved"}], lane, 4))


if __name__ == "__main__":
    unittest.main()
