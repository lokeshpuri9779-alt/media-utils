import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.reviewed_art_bridge import build_approved_manifest


class ReviewedArtBridgeTests(unittest.TestCase):
    def test_empty_decisions_never_approve(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue, images, decisions = [root / x for x in ("queue.json", "images.json", "decisions.json")]
            queue.write_text(json.dumps({"rewrites": [{"status": "awaiting_independent_editorial_approval",
                "story": {"content_id": "test", "story_beats": [{"speech": "A fox searches."}]}}]}))
            images.write_text(json.dumps({"assets": []}))
            decisions.write_text(json.dumps({"schema_version": 1, "approved_scenes": []}))
            self.assertEqual(build_approved_manifest(queue, images, decisions, root, root), {"assets": []})

    def test_unknown_approval_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue, images, decisions = [root / x for x in ("queue.json", "images.json", "decisions.json")]
            queue.write_text('{"rewrites":[]}')
            images.write_text('{"assets":[]}')
            decisions.write_text(json.dumps({"schema_version": 1, "approved_scenes": [{
                "decision": "approved", "story_content_id": "unknown",
                "scene_id": "001", "sha256": "a" * 64}]}))
            with self.assertRaises(ValueError):
                build_approved_manifest(queue, images, decisions, root, root)


if __name__ == "__main__":
    unittest.main()
