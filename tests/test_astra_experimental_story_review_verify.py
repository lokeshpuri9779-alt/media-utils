"""Fail-closed review ZIP/file-integrity checks; no real rendering required.

Real artifact bytes are checked separately by the two CPU workflow jobs.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_astra_experimental_story_review_manifest import fixture
from tools import experimental_story_review_manifest as manifest
from tools import experimental_story_review_verify as verifier

VIDEO = dict(codec_name="h264", width=384, height=576,
             r_frame_rate="8/1", nb_frames="20")


class VerifyReviewPackageTest(unittest.TestCase):
    def setUp(self):
        context = tempfile.TemporaryDirectory()
        self.addCleanup(context.cleanup)
        self.root = Path(context.name)
        for module in (manifest, verifier):
            fake = patch.object(module, "get_video", side_effect=self.fake_video)
            fake.start()
            self.addCleanup(fake.stop)
        # Byte-minimal synthetic fixtures need a mocked decoder. Actual
        # downloaded CPU render artifacts are decoded by the workflows.
        self.fidelity = {"passed": True, "mean_rgb_mae": 1.0,
                         "max_frame_rgb_mae": 1.5, "worst_frame": 0}
        self.fidelity_patches = []
        for module in (manifest, verifier):
            fake = patch.object(module, "compare_video", return_value=self.fidelity)
            mock = fake.start()
            self.fidelity_patches.append(mock)
            self.addCleanup(fake.stop)

    def fake_video(self, path):
        # Probe is mocked only for unit fixtures with minimal dummy MP4 bytes.
        n = 32 if "frog" in path.name else 20
        if path.name == "frog_story_previs.mp4":
            n = 32
        return dict(VIDEO, nb_frames=str(n))

    def prepare(self, profile):
        fixture(self.root, profile)
        packet = manifest.build(self.root, profile)
        self.assertTrue(packet["technical_evidence_passed"], packet)
        (self.root / "story_review_manifest.json").write_text(
            json.dumps(packet, indent=2), encoding="utf-8")
        return verifier.verify(self.root, profile)

    def test_lighthouse_and_frog_packages_pass(self):
        for profile in ("lighthouse", "frog"):
            with self.subTest(profile=profile):
                with tempfile.TemporaryDirectory() as directory:
                    self.root = Path(directory)
                    result = self.prepare(profile)
                    self.assertTrue(result["passed"], result)
                    expected = len(json.loads(
                        (self.root / "story_review_manifest.json").read_text()
                    )["sha256"])
                    self.assertEqual(result["files_verified"], expected)
                    self.assertTrue(result["manual_visual_review_required"])
                    self.assertFalse(result["production_ready"])

    def test_modified_png_rejected_even_when_metadata_claims_success(self):
        self.prepare("frog")
        with (self.root/"frame_014.png").open("ab") as stream:
            stream.write(b"CORRUPT")
        result = verifier.verify(self.root, "frog")
        self.assertFalse(result["passed"])
        self.assertIn("frame_014.png", result["mismatched_files"])

    def test_modified_mp4_rejected(self):
        self.prepare("frog")
        (self.root/"frog_story_previs.mp4").write_bytes(b"another video")
        result = verifier.verify(self.root, "frog")
        self.assertIn("frog_story_previs.mp4", result["mismatched_files"])

    def test_tampered_frog_object_evidence_rejected(self):
        self.prepare("frog")
        name = manifest.PROFILES["frog"]["object_audit"]
        path = self.root / name
        path.write_text(path.read_text() + " ", encoding="utf-8")
        result = verifier.verify(self.root, "frog")
        self.assertIn(name, result["mismatched_files"])

    def test_removed_frog_object_controls_rejected(self):
        self.prepare("frog")
        name = manifest.PROFILES["frog"]["object_negative"]
        (self.root / name).unlink()
        result = verifier.verify(self.root, "frog")
        self.assertIn(name, result["mismatched_files"])

    def test_modified_audit_rejected(self):
        self.prepare("lighthouse")
        path = self.root/"visual_audit.json"
        path.write_text(path.read_text() + " ", encoding="utf-8")
        result = verifier.verify(self.root, "lighthouse")
        self.assertIn(path.name, result["mismatched_files"])

    def test_rejects_repackaged_video_with_unrelated_frames(self):
        # The manifest hashes may be internally consistent, yet a real
        # encoded MP4 can have the wrong visual content. Independent
        # frame-by-frame decoding must still reject it.
        self.prepare("frog")
        self.fidelity_patches[1].return_value = {
            "passed": False, "mean_rgb_mae": 30.0,
            "max_frame_rgb_mae": 55.0, "worst_frame": 5
        }
        result = verifier.verify(self.root, "frog")
        self.assertFalse(result["passed"])
        self.assertIn("video_pixels_independently_match_png_sequence",
                      result["failed_checks"])
        self.assertIn("manifest_and_independent_fidelity_evidence_agree",
                      result["failed_checks"])

    def test_missing_frame_rejected(self):
        self.prepare("frog")
        (self.root/"frame_031.png").unlink()
        result = verifier.verify(self.root, "frog")
        self.assertIn("frame_031.png", result["mismatched_files"])

    def test_inventory_missing_digest_rejected(self):
        self.prepare("lighthouse")
        path=self.root/"story_review_manifest.json"
        packet=json.loads(path.read_text())
        del packet["sha256"]["frame_003.png"]
        path.write_text(json.dumps(packet),encoding="utf-8")
        result=verifier.verify(self.root,"lighthouse")
        self.assertIn("complete_hash_inventory", result["failed_checks"])

    def test_wrong_profile_rejected(self):
        self.prepare("frog")
        result=verifier.verify(self.root,"lighthouse")
        self.assertFalse(result["passed"])
        self.assertIn("expected_profile_and_story", result["failed_checks"])

    def test_claim_of_approval_rejected(self):
        self.prepare("frog")
        path=self.root/"story_review_manifest.json"
        packet=json.loads(path.read_text())
        packet["approved"]=True
        path.write_text(json.dumps(packet),encoding="utf-8")
        result=verifier.verify(self.root,"frog")
        self.assertIn("manual_review_required",result["failed_checks"])

    def test_unexpected_unhashed_file_rejected(self):
        self.prepare("frog")
        (self.root/"external_video.mp4").write_bytes(b"unlisted")
        result=verifier.verify(self.root,"frog")
        self.assertIn("no_unexpected_files",result["failed_checks"])

    def test_missing_manifest_rejected(self):
        fixture(self.root,"frog")
        with self.assertRaises(ValueError):
            verifier.verify(self.root,"frog")

    def test_malformed_manifest_rejected(self):
        fixture(self.root,"frog")
        (self.root/"story_review_manifest.json").write_text("{oops")
        with self.assertRaises(ValueError):
            verifier.verify(self.root,"frog")


if __name__ == "__main__":
    unittest.main()
