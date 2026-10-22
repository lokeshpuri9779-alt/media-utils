import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.asset_readiness_audit import audit_assets


class AssetReadinessAuditTests(unittest.TestCase):
    def test_missing_asset_never_grants_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "queue.json"
            manifest = root / "manifest.json"
            queue.write_text(json.dumps({"rewrites": [{"status": "awaiting_independent_editorial_approval",
                "story": {"content_id": "original-1", "story_beats": [{"speech": "The fox finds a bell."}]}}]}))
            manifest.write_text(json.dumps({"assets": [{"story_content_id": "original-1",
                "scene_id": "001", "status": "review_only", "sha256": "a" * 64,
                "path": "missing.png"}]}))
            result = audit_assets(queue, manifest, root)
            self.assertEqual(result["stories_checked"], 1)
            self.assertEqual(result["file_complete"], 0)
            self.assertFalse(result["stories"][0]["production_ready"])

    def test_complete_file_evidence_still_requires_independent_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "queue.json"
            manifest = root / "manifest.json"
            queue.write_text(json.dumps({"rewrites": [{"status": "awaiting_independent_editorial_approval",
                "story": {"content_id": "original-1", "story_beats": [{"speech": "The fox finds a bell."}]}}]}))
            import hashlib
            data = b"fake image for mocked pixel validator"
            (root / "image.png").write_bytes(data)
            manifest.write_text(json.dumps({"assets": [{"story_content_id": "original-1",
                "scene_id": "001", "status": "review_only",
                "sha256": hashlib.sha256(data).hexdigest(), "path": "image.png"}]}))
            with patch("astra_v2.omniroute_image_assets.image_quality_report",
                       return_value={"passed": True}):
                result = audit_assets(queue, manifest, root)
            self.assertEqual(result["file_complete"], 1)
            self.assertFalse(result["stories"][0]["production_ready"])
            self.assertFalse(result["stories"][0]["renderer_integration_verified"])


if __name__ == "__main__":
    unittest.main()
