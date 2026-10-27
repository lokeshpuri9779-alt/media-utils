"""Studio preview must validate compositor evidence, not a removed log marker."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.studio_preview_asset_gate import verify_asset_pack_use


class StudioPreviewAssetGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root / "studio-preview.mp4"
        self.video.write_bytes(b"test encoded media for hash linkage")
        self.sha = hashlib.sha256(self.video.read_bytes()).hexdigest()
        self.receipt = self.root / "asset-usage.json"
        self.log = self.root / "render.log"

    def write_receipt(self, used=1, video_hash=None):
        shots = [
            {"shot": 1, "status": "composited", "pixel_changed": True,
             "asset": {"sha256": "a" * 64}},
            {"shot": 2, "status": "scene_unresolved", "pixel_changed": False,
             "asset": None},
        ]
        data = {"shot_count": 2, "composited_shots": used,
                "video_sha256": video_hash or self.sha, "shots": shots}
        self.receipt.write_text(json.dumps(data), encoding="utf-8")
        self.log.write_text("rendering\nASTRA_ASSET_USAGE_RECEIPT=" + json.dumps({
            "path": str(self.receipt), "shot_count": 2,
            "composited_shots": used, "video_sha256": video_hash or self.sha
        }) + "\n", encoding="utf-8")

    def test_verified_compositing_linked_to_actual_video_passes(self):
        self.write_receipt()
        report = verify_asset_pack_use(self.log, self.video)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["composited_shots"], 1)
        self.assertEqual(report["semantic_quality"], "not_verified")

    def test_zero_backgrounds_fail_closed(self):
        self.write_receipt(used=0)
        with self.assertRaisesRegex(ValueError, "no_verified_composited_backgrounds"):
            verify_asset_pack_use(self.log, self.video)

    def test_receipt_cannot_claim_unobserved_compositing(self):
        self.write_receipt(used=2)
        with self.assertRaisesRegex(ValueError, "compositor_receipt_shot_mismatch"):
            verify_asset_pack_use(self.log, self.video)

    def test_mp4_hash_mismatch_fails_closed(self):
        self.write_receipt(video_hash="b" * 64)
        with self.assertRaisesRegex(ValueError, "compositor_receipt_mp4_mismatch"):
            verify_asset_pack_use(self.log, self.video)

    def test_missing_receipt_marker_fails_closed(self):
        self.log.write_text("only legacy selection marker\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "expected_exactly_one_compositor_receipt"):
            verify_asset_pack_use(self.log, self.video)

    def test_missing_receipt_file_fails_closed(self):
        self.write_receipt()
        self.receipt.unlink()
        with self.assertRaisesRegex(ValueError, "missing_compositor_receipt_file"):
            verify_asset_pack_use(self.log, self.video)


if __name__ == "__main__":
    unittest.main()
