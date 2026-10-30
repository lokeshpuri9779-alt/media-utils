"""Production receipt must describe actual per-shot background compositing."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from astra_v2.asset_usage_audit import (begin, finish, fiction_compositor_coverage_rejection,
                                        fiction_preload_coverage_rejection)
from astra_v2.visual_artifact_backdrop import apply_pack_background


class AssetUsageEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "art").mkdir()
        entries = []
        for name, tags, colour in (
            ("forest-art", ["forest"], (145, 185, 75)),
            ("railway-art", ["railway"], (50, 100, 155)),
        ):
            path = self.root / "art" / (name + ".png")
            Image.new("RGB", (360, 640), colour).save(path)
            entries.append({"id": name, "path": "art/" + path.name,
                            "kind": "background", "license": "original",
                            "source": "ASTRA verified-test-generated",
                            "artist": "ASTRA test", "tags": tags})
        (self.root / "art" / "manifest.json").write_text(
            json.dumps({"assets": entries}), encoding="utf-8")
        self.environment = patch.dict(os.environ, {
            "ASTRA_ASSET_PACK_ENABLED": "1",
            "ASTRA_ASSET_PACK_AUDIT": "1",
            "ASTRA_ASSET_AUDIT_DIR": str(self.root / "receipts"),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def video(self):
        path = self.root / "short.mp4"
        path.write_bytes(b"test encoded media bytes")
        return path

    def test_receipt_links_verified_asset_to_actual_compositor_pixels_and_video(self):
        begin({"content_id": "story-01", "title": "Forest arrival"}, 2)
        base = Image.new("RGB", (360, 640), (5, 10, 15))
        first = apply_pack_background(base, {"story_environment": "forest"},
                                      "scene-01", root=self.root, shot_number=1)
        self.assertNotEqual(first.tobytes(), base.tobytes())
        # Repeated frames must not create duplicate receipts.
        apply_pack_background(base, {"story_environment": "forest"},
                              "scene-01", root=self.root, shot_number=1)
        apply_pack_background(base, {"visual_prompt": "a machine malfunction"},
                              "scene-02", root=self.root, shot_number=2)
        receipt = finish(self.video(), renderer="studio-test", expected_shots=2)
        report = json.loads(Path(receipt["path"]).read_text(encoding="utf-8"))
        self.assertEqual(report["shot_count"], 2)
        self.assertEqual(report["composited_shots"], 1)
        self.assertEqual(report["statuses"], {"composited": 1, "scene_unresolved": 1})
        self.assertEqual(report["shots"][0]["asset"]["id"], "forest-art")
        expected = hashlib.sha256((self.root / "art" / "forest-art.png").read_bytes()).hexdigest()
        self.assertEqual(report["shots"][0]["asset"]["sha256"], expected)
        self.assertTrue(report["shots"][0]["pixel_changed"])
        self.assertIsNone(report["shots"][1]["asset"])
        self.assertEqual(report["video_sha256"], hashlib.sha256(b"test encoded media bytes").hexdigest())
        self.assertIsNone(finish(self.video(), renderer="studio-test"))

    def test_missing_compositor_shot_blocks_success_claim(self):
        begin({"content_id": "story-missing"}, 2)
        apply_pack_background(Image.new("RGB", (360, 640)),
                              {"story_environment": "forest"},
                              "one", root=self.root, shot_number=1)
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            finish(self.video(), renderer="studio-test")

    def test_manifest_loss_fails_closed(self):
        begin({"content_id": "missing-pack"}, 1)
        apply_pack_background(Image.new("RGB", (360, 640)),
                              {"story_environment": "forest"}, "one",
                              root=self.root / "missing", shot_number=1)
        with self.assertRaisesRegex(RuntimeError, "missing validated pack"):
            finish(self.video(), renderer="studio-test")

    def test_unmatched_asset_is_not_reported_as_used(self):
        begin({"content_id": "no-background"}, 1)
        apply_pack_background(Image.new("RGB", (360, 640)),
                              {"story_environment": "desert"}, "one",
                              root=self.root, shot_number=1)
        receipt = finish(self.video(), renderer="studio-test")
        report = json.loads(Path(receipt["path"]).read_text())
        self.assertEqual(report["composited_shots"], 0)
        self.assertEqual(report["shots"][0]["status"], "no_matching_background")
        self.assertFalse(report["shots"][0]["pixel_changed"])

    def test_audited_fiction_rejects_partial_scene_coverage_before_upload(self):
        story = {"genre": "fiction", "content_id": "railway-ledger"}
        receipt = {"shot_count": 4, "composited_shots": 1,
                   "asset_coverage_status": "partial"}
        self.assertEqual(
            fiction_compositor_coverage_rejection(story, {"asset_pack_usage": receipt}),
            "fiction_scene_background_coverage_incomplete")

    def test_audited_fiction_requires_complete_valid_receipt(self):
        story = {"genre": "fiction"}
        for report in ({}, {"asset_pack_usage": None},
                       {"asset_pack_usage": {"shot_count": True, "composited_shots": 1}},
                       {"asset_pack_usage": {"shot_count": 4, "composited_shots": 5}}):
            with self.subTest(report=report):
                self.assertIsNotNone(fiction_compositor_coverage_rejection(story, report))
        self.assertIsNone(fiction_compositor_coverage_rejection(
            story, {"asset_pack_usage": {"shot_count": 4, "composited_shots": 4}}))

    def test_coverage_gate_does_not_change_current_events_or_disabled_audits(self):
        partial = {"asset_pack_usage": {"shot_count": 4, "composited_shots": 1}}
        self.assertIsNone(fiction_compositor_coverage_rejection(
            {"genre": "current"}, partial))
        with patch.dict(os.environ, {"ASTRA_ASSET_PACK_AUDIT": "0"}):
            self.assertIsNone(fiction_compositor_coverage_rejection(
                {"genre": "fiction"}, partial))

    def test_fiction_preload_requires_hash_bound_full_coverage(self):
        valid = {"genre": "fiction", "format": "short", "content_id": "railway",
                 "sha256": "a" * 64,
                 "asset_pack_usage": {"shot_count": 4, "composited_shots": 4,
                                      "video_sha256": "a" * 64,
                                      "asset_coverage_status": "full",
                                      "statuses": {"composited": 4}}}
        self.assertIsNone(fiction_preload_coverage_rejection(valid))
        for changes in (
            {"asset_pack_usage": None},
            {"sha256": "b" * 64},
            {"asset_pack_usage": {**valid["asset_pack_usage"], "composited_shots": 1}},
            {"asset_pack_usage": {**valid["asset_pack_usage"], "asset_coverage_status": "partial"}},
            {"asset_pack_usage": {**valid["asset_pack_usage"], "statuses": {"composited": 3, "scene_unresolved": 1}}},
        ):
            with self.subTest(changes=changes):
                self.assertIsNotNone(fiction_preload_coverage_rejection({**valid, **changes}))
        self.assertIsNone(fiction_preload_coverage_rejection({**valid, "genre": "current"}))
        with patch.dict(os.environ, {"ASTRA_ASSET_PACK_AUDIT": "0"}):
            self.assertIsNone(fiction_preload_coverage_rejection({**valid, "asset_pack_usage": None}))

    def test_preload_workflow_enables_fiction_audit(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/astra-v2-preload.yml").read_text(encoding="utf-8")
        self.assertIn("ASTRA_ASSET_PACK_AUDIT: '1'", workflow)

    def test_opt_out_produces_no_receipt(self):
        with patch.dict(os.environ, {"ASTRA_ASSET_PACK_AUDIT": "0"}):
            self.assertFalse(begin({"content_id": "none"}, 1))
            self.assertIsNone(finish(self.video(), renderer="studio-test"))


if __name__ == "__main__":
    unittest.main()
