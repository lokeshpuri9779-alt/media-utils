import hashlib
import hmac
import os
from unittest.mock import patch
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from astra_v2.promote_staged_art import promote
from astra_v2.gemini_art_semantic_review import CRITERIA


class PromotionTests(unittest.TestCase):
    def test_external_decision_required_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "scene-1.png"
            Image.new("RGB", (540, 960)).save(image)
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            manifest = root / "staging-manifest.json"
            manifest.write_text(json.dumps({"schema": "astra.art.staging.v1",
                "publication_triggered": False, "assets": [{
                    "id": "story-scene-1", "story_content_id": "story",
                    "scene_id": "scene-1", "category": "background",
                    "path": image.name, "sha256": digest,
                    "tags": [], "status": "pending_review"}]}))
            semantic = root / "semantic-review.json"
            semantic.write_text(json.dumps({"schema": "astra.art.semantic-review.v1",
                "story_content_id": "story", "semantic_pass": True,
                "independent_visual_approval": False, "publication_triggered": False,
                "scenes": [{"scene_id": "scene-1", "issues": [],
                            **{key: True for key in CRITERIA}}]}))
            decision = root / "decision.json"
            payload = {"schema": "astra.art.external-approval.v1",
                "story_content_id": "story", "reviewer_id": "reviewer@example.org",
                "decision": "approved", "publication_triggered": False,
                "assets": [{"scene_id": "scene-1", "sha256": digest,
                            "decision": "approved"}]}
            key = "test-reviewer-secret-" + "x" * 32
            def sign():
                body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
                return hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
            decision.write_text(json.dumps({**payload, "signature": sign()}))
            with patch.dict(os.environ, {"ASTRA_ART_APPROVAL_HMAC_KEY": key}):
                with self.assertRaisesRegex(ValueError, "external_approval_hash_mismatch"):
                    payload["assets"][0]["sha256"] = "0" * 64
                    decision.write_text(json.dumps({**payload, "signature": sign()}))
                    promote(manifest, semantic, decision, root / "rejected")
            payload["assets"][0]["sha256"] = digest
            decision.write_text(json.dumps({**payload, "signature": sign()}))
            with patch.dict(os.environ, {"ASTRA_ART_APPROVAL_HMAC_KEY": key}):
                approved = promote(manifest, semantic, decision, root / "accepted")
            self.assertEqual(json.loads(approved.read_text())["assets"][0]["status"], "approved")
            self.assertTrue((root / "accepted" / "validated-bundles" / "story.zip").exists())


if __name__ == "__main__":
    unittest.main()
