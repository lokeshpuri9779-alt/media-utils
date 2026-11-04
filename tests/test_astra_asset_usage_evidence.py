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
                                        fiction_preload_coverage_rejection, preflight_fiction_backgrounds)
from astra_v2.visual_artifact_backdrop import apply_pack_background
from astra_errors import CreativeReject, StoryBackgroundPreflightReject
from astra_v2.creative import record_background_preflight_gap


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

    def test_background_preflight_reports_possible_not_approved(self):
        with patch.dict(os.environ, {"ASTRA_ASSET_PACK_ROOT": str(self.root)}):
            with patch("astra_v2.quality_asset_selector.select_assets",
                       return_value=[{"id": "forest-art"}]) as selector:
                report = preflight_fiction_backgrounds([
                    {"story_environment": "forest"},
                    {"story_environment": "forest"},
                ], genre="fiction")
        self.assertEqual(report["status"], "possible")
        self.assertEqual(report["missing_shots"], [])
        self.assertEqual(report["semantic_quality"], "not_verified")
        self.assertFalse(report["publication_approval"])
        selector.assert_called_once()

    def test_background_preflight_rejects_unresolved_scene_without_guessing(self):
        with patch.dict(os.environ, {"ASTRA_ASSET_PACK_ROOT": str(self.root)}):
            with patch("astra_v2.quality_asset_selector.select_assets") as selector:
                report = preflight_fiction_backgrounds([
                    {"story_environment": "unrecognized dreamworld"},
                ], genre="fiction")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["missing_shots"],
                         [{"shot": 1, "reason": "scene_unresolved"}])
        selector.assert_not_called()

    def test_background_preflight_rejects_verified_pack_without_scene_art(self):
        with patch.dict(os.environ, {"ASTRA_ASSET_PACK_ROOT": str(self.root)}):
            with patch("astra_v2.quality_asset_selector.select_assets", return_value=[]):
                report = preflight_fiction_backgrounds([
                    {"story_environment": "railway"},
                ], genre="fiction")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["missing_shots"], [
            {"shot": 1, "reason": "no_matching_background", "scene": "railway"}])

    def test_background_preflight_blocks_partial_and_caches_missing_scene(self):
        def matching(root, *, kind, tags, video_format, limit):
            return [{"id": "forest-art"}] if tags == ("forest",) else []

        with patch.dict(os.environ, {"ASTRA_ASSET_PACK_ROOT": str(self.root)}):
            with patch("astra_v2.quality_asset_selector.select_assets",
                       side_effect=matching) as selector:
                report = preflight_fiction_backgrounds([
                    {"story_environment": "forest"},
                    {"story_environment": "railway"},
                    {"story_environment": "railway"},
                ], genre="fiction")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["missing_shots"], [
            {"shot": 2, "reason": "no_matching_background", "scene": "railway"},
            {"shot": 3, "reason": "no_matching_background", "scene": "railway"},
        ])
        self.assertEqual(selector.call_count, 2)
        self.assertFalse(report["publication_approval"])

    def test_background_preflight_missing_pack_and_opt_out(self):
        with patch.dict(os.environ, {"ASTRA_ASSET_PACK_ROOT": str(self.root / "missing")}):
            report = preflight_fiction_backgrounds([
                {"story_environment": "railway"}], genre="fiction")
        self.assertEqual(report["reason"], "verified_asset_pack_missing")
        self.assertFalse(report["publication_approval"])
        self.assertIsNone(preflight_fiction_backgrounds(
            [{"story_environment": "railway"}], genre="current"))
        with patch.dict(os.environ, {"ASTRA_ASSET_PACK_AUDIT": "0"}):
            self.assertIsNone(preflight_fiction_backgrounds(
                [{"story_environment": "railway"}], genre="fiction"))

    def test_background_preflight_runs_before_media_acquisition_and_encoding(self):
        source = (Path(__file__).resolve().parents[1] /
                  "studio_renderer.py").read_text(encoding="utf-8")
        preflight_at = source.index("preflight_fiction_backgrounds(plan, genre=genre)")
        media_at = source.index("    assets=asset_manifest(ch,plan)")
        encoder_at = source.index("    with tempfile.TemporaryDirectory(", media_at)
        self.assertLess(preflight_at, media_at)
        self.assertLess(media_at, encoder_at)
        self.assertIn("fiction_compositor_coverage_rejection(story, rendered)",
                      (Path(__file__).resolve().parents[1] /
                       "astra_v2/creative.py").read_text(encoding="utf-8"))

    def test_background_rejection_keeps_failing_closed_and_review_only(self):
        report = {"status": "blocked", "reason": "missing_backgrounds",
                  "shot_count": 4, "missing_shots": [
                      {"shot": 1, "reason": "scene_unresolved"}]}
        exc = StoryBackgroundPreflightReject(report)
        self.assertIsInstance(exc, CreativeReject)
        self.assertFalse(exc.report["publication_approval"])
        self.assertEqual(exc.report["semantic_quality"], "not_verified")
        with self.assertRaises(ValueError):
            StoryBackgroundPreflightReject({"status": "possible"})

    def test_structured_background_gap_reports_missing_shots_without_approval(self):
        selection = {"background_preflight_rejected": 0, "background_review_gaps": []}
        report = {"status": "blocked", "reason": "missing_backgrounds",
                  "shot_count": 3, "missing_shots": [
                      {"shot": 1, "reason": "scene_unresolved"},
                      {"shot": 3, "reason": "no_matching_background", "scene": "railway"}]}
        with patch("builtins.print"):
            gap = record_background_preflight_gap(selection,
                {"content_id": "story-gap"}, report)
        self.assertEqual(selection["background_preflight_rejected"], 1)
        self.assertEqual(selection["background_review_gaps"], [gap])
        self.assertEqual([s["shot"] for s in gap["missing_shots"]], [1, 3])
        self.assertFalse(gap["publication_approval"])
        self.assertEqual(gap["semantic_quality"], "not_verified")

    def test_review_gap_does_not_remove_final_compositor_gate(self):
        renderer = (Path(__file__).resolve().parents[1] /
                    "studio_renderer.py").read_text(encoding="utf-8")
        self.assertIn("raise StoryBackgroundPreflightReject(background_check)", renderer)
        creative = (Path(__file__).resolve().parents[1] /
                    "astra_v2/creative.py").read_text(encoding="utf-8")
        self.assertIn("except StoryBackgroundPreflightReject as exc:", creative)
        self.assertIn("fiction_compositor_coverage_rejection(story, rendered)", creative)

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
