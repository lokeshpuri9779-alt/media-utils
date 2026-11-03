"""Negative-control tests for two-story review manifest integrity.

Fixtures are deliberately synthetic. Real PNG/MP4 data is verified by the two
isolated CPU render workflows, not certified by these tests.
"""
from __future__ import annotations

import copy
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import experimental_story_review_manifest as manifest


def write(directory, filename, document):
    (directory / filename).write_text(
        json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")


def fixture(directory, profile):
    cfg = manifest.PROFILES[profile]
    n = cfg["frame_count"]
    png = (
        b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
        + struct.pack(">II", 384, 576) + b"\x08\x02\x00\x00\x00"
        + b"\x00" * 20
    )
    sha = hashlib.sha256(png).hexdigest()
    for i in range(n):
        (directory / f"frame_{i:03d}.png").write_bytes(png)
    (directory / cfg["video"]).write_bytes(b"\x00" * 4100)
    safety = dict(approved=False, published=False, production_ready=False,
                  paid_apis_used=False)
    frames = [
        dict(frame=i, sha256=sha) for i in range(n)
    ]
    review = dict(safety, success=True, editorial_review_required=True,
                  frames=frames, checks=dict(success=True),
                  story_id=cfg["story_id"], plot_fingerprint="hash123")
    action = dict(safety, profile=profile, passed=True, manual_review_required=True,
                  semantic_quality="not_verified", checks=dict(correct=True))
    visual = dict(safety, checks=dict(pixels=True))
    negative = dict(safety, all_corruptions_rejected=True,
                    negative_case_count=cfg["negative_count"])
    if profile == "frog":
        visual.update(profile=profile, passed=True,
                      manual_visual_review_required=True,
                      semantic_quality="not_verified")
        negative.update(manual_visual_review_required=True)
        object_checks = {
            "review_only_fixed_camera_trace": True,
            "magnet_golden_pixels_present": True,
            "gold_cluster_travels_leftward_to_clip": True,
            "airplane_bright_pixels_present": True,
            "paper_region_moves_right_after_contact": True,
            "seed_brown_blob_before_soil": True,
            "seed_pixel_path_advances_toward_pot": True,
            "sprout_pixels_follow_seed_transfer": True,
        }
        write(directory, cfg["object_audit"],
              dict(safety, passed=True, checks=object_checks,
                   manual_visual_review_required=True,
                   semantic_quality="not_verified"))
        write(directory, cfg["object_negative"],
              dict(safety, source_passed=True, all_corruptions_rejected=True,
                   negative_case_count=cfg["object_negative_count"],
                   cases=[{"case": str(i), "rejected": True}
                          for i in range(cfg["object_negative_count"])],
                   manual_visual_review_required=True,
                   semantic_quality="not_verified"))
    else:
        visual.update(passes_fixed_pixel_checks=True,
                      manual_editorial_review_required=True,
                      visual_semantic_quality="not_verified")
        negative.update(manual_review_required=True)
        write(directory, "shot_plan.json",
              dict(safety, story_id=cfg["story_id"], plot_fingerprint="hash123"))
    write(directory, "review.json", review)
    write(directory, "action_contract.json", action)
    write(directory, cfg["audit"], visual)
    write(directory, cfg["negative"], negative)
    return cfg


class ReviewManifestTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.video_patch = patch.object(
            manifest, "get_video",
            return_value=dict(codec_name="h264", width=384, height=576,
                              r_frame_rate="8/1", nb_frames="20")
        )
        self.mock_video = self.video_patch.start()
        self.addCleanup(self.video_patch.stop)
        # The synthetic PNG/MP4 fixtures are deliberately not decodable.
        # Live CPU-render workflows exercise the real pixel decoder.
        self.fidelity_patch = patch.object(
            manifest, "compare_video",
            return_value={"passed": True, "mean_rgb_mae": 1.0,
                          "max_frame_rgb_mae": 1.5, "worst_frame": 0}
        )
        self.mock_fidelity = self.fidelity_patch.start()
        self.addCleanup(self.fidelity_patch.stop)

    def configure(self, profile):
        cfg = fixture(self.root, profile)
        self.mock_video.return_value["nb_frames"] = str(cfg["frame_count"])
        return cfg

    def test_both_distinct_stories_pass_review_packet(self):
        for profile in ("frog", "lighthouse"):
            with self.subTest(profile=profile):
                with tempfile.TemporaryDirectory() as td:
                    directory = Path(td)
                    fixture(directory, profile)
                    self.mock_video.return_value["nb_frames"] = str(
                        manifest.PROFILES[profile]["frame_count"])
                    result = manifest.build(directory, profile)
                    self.assertTrue(result["technical_evidence_passed"], result)
                    self.assertTrue(all(result["checks"].values()))
                    self.assertFalse(result["approved"])
                    self.assertFalse(result["production_ready"])
                    self.assertEqual(result["approval"], "manual_review_required")

    def test_missing_frog_object_pixels_fail_closed(self):
        cfg = self.configure("frog")
        (self.root / cfg["object_audit"]).unlink()
        with self.assertRaises(FileNotFoundError):
            manifest.build(self.root, "frog")

    def test_false_frog_object_motion_rejected(self):
        cfg = self.configure("frog")
        name = cfg["object_audit"]
        data = json.loads((self.root / name).read_text())
        data["checks"]["gold_cluster_travels_leftward_to_clip"] = False
        write(self.root, name, data)
        result = manifest.build(self.root, "frog")
        self.assertIn("frog_object_pixel_tracking", result["failed_checks"])

    def test_fabricated_frog_object_controls_rejected(self):
        cfg = self.configure("frog")
        name = cfg["object_negative"]
        data = json.loads((self.root / name).read_text())
        data["cases"][2]["rejected"] = False
        write(self.root, name, data)
        result = manifest.build(self.root, "frog")
        self.assertIn("frog_object_negative_controls", result["failed_checks"])

    def test_rejects_missing_visual_evidence(self):
        cfg = self.configure("frog")
        (self.root / cfg["audit"]).unlink()
        with self.assertRaises(FileNotFoundError):
            manifest.build(self.root, "frog")

    def test_rejects_visual_audit_failure(self):
        cfg = self.configure("frog")
        path = self.root / cfg["audit"]
        data = json.loads(path.read_text())
        data["passed"] = False
        write(self.root, cfg["audit"], data)
        result = manifest.build(self.root, "frog")
        self.assertFalse(result["technical_evidence_passed"])
        self.assertIn("visual_pixel_audit", result["failed_checks"])

    def test_rejects_unsafe_gate_in_any_report(self):
        cfg = self.configure("frog")
        for name in ("review.json", "action_contract.json", cfg["audit"],
                     cfg["negative"]):
            with self.subTest(name=name):
                path = self.root / name
                data = json.loads(path.read_text())
                data["published"] = True
                write(self.root, name, data)
                result = manifest.build(self.root, "frog")
                self.assertIn("all_source_gates_closed", result["failed_checks"])
                data["published"] = False
                write(self.root, name, data)

    def test_rejects_lighthouse_png_hash_mismatch(self):
        self.configure("lighthouse")
        path = self.root / "frame_003.png"
        original = path.read_bytes()
        path.write_bytes(original + b"tamper")
        result = manifest.build(self.root, "lighthouse")
        self.assertIn("lighthouse_existing_frame_hashes_match",
                      result["failed_checks"])

    def test_rejects_fake_video_codec(self):
        self.configure("frog")
        self.mock_video.return_value["codec_name"] = "mpeg4"
        result = manifest.build(self.root, "frog")
        self.assertIn("video_matches_story_frames", result["failed_checks"])

    def test_rejects_valid_mp4_with_wrong_visual_content(self):
        # Codec, dimensions, timing and file digest can all look correct,
        # while the MP4 actually depicts unrelated or blank frames.
        self.configure("frog")
        self.mock_fidelity.return_value = {
            "passed": False, "mean_rgb_mae": 50.0,
            "max_frame_rgb_mae": 80.0, "worst_frame": 0
        }
        result = manifest.build(self.root, "frog")
        self.assertFalse(result["technical_evidence_passed"])
        self.assertIn("encoded_video_pixels_match_png_sequence",
                      result["failed_checks"])
        self.assertFalse(result["approved"])

    def test_rejects_missing_frame(self):
        self.configure("frog")
        (self.root / "frame_031.png").unlink()
        result = manifest.build(self.root, "frog")
        self.assertIn("exact_frame_files", result["failed_checks"])

    def test_rejects_fabricated_negative_result(self):
        cfg = self.configure("lighthouse")
        name = cfg["negative"]
        data = json.loads((self.root / name).read_text())
        data["all_corruptions_rejected"] = False
        write(self.root, name, data)
        result = manifest.build(self.root, "lighthouse")
        self.assertIn("negative_controls_rejected", result["failed_checks"])

    def test_rejects_incorrect_story_identity(self):
        self.configure("frog")
        data = json.loads((self.root / "review.json").read_text())
        data["story_id"] = "unrelated-story"
        write(self.root, "review.json", data)
        result = manifest.build(self.root, "frog")
        self.assertIn("correct_story_profile", result["failed_checks"])

    def test_unknown_profile_is_not_accepted(self):
        with self.assertRaises(ValueError):
            manifest.build(self.root, "arbitrary-third-story")


if __name__ == "__main__":
    unittest.main()
