import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.independent_editorial_handoff import handoff
from astra_v2.editorial_approval_manifest import story_digest


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.story = {"content_id": "reviewed-1", "kind": "authored_causal_story",
                      "production_ready": True, "story_beats": []}
        self.record = {"content_id": "reviewed-1", "story_sha256": story_digest(self.story),
                       "decision": "approve", "reviewer": "independent model",
                       "review_notes": "complete review"}

    def test_rejected_story_cannot_export(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder) / "stories.json", Path(folder) / "decisions.json"
            self.assertEqual(handoff(self.story, {"approved": False}, [], a, b), [])
            self.assertFalse(a.exists())
            self.assertFalse(b.exists())

    def test_validated_handoff_writes_existing_manifest_format(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder) / "stories.json", Path(folder) / "decisions.json"
            with patch("astra_v2.independent_editorial_handoff.approved_intake",
                       return_value={"stories": [self.story], "intake_count": 1}):
                result = handoff(self.story, {"approved": True, "record": self.record}, [], a, b)
            self.assertEqual(result, [self.story])
            self.assertEqual(json.loads(a.read_text())["stories"], [self.story])
            self.assertEqual(json.loads(b.read_text())["reviews"], [self.record])

    def test_mismatched_story_hash_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            invalid = dict(self.record, story_sha256="0" * 64)
            with self.assertRaises(ValueError):
                handoff(self.story, {"approved": True, "record": invalid}, [],
                        Path(folder) / "stories.json", Path(folder) / "decisions.json")


if __name__ == "__main__":
    unittest.main()
