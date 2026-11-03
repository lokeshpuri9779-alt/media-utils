"""24-frame reviewer timeline regressions; no actual visual approval."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from astra_v2.review_timeline import (
    beat_sample_schedule, build_review_timeline,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ReviewTimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = b"FAKE_H264_NOT_A_REAL_MP4"
        self.story = {
            "content_id": "qa-fox-01", "title": "The Fox and the Clock",
            "genre": "fiction", "format": "short",
            "sha256": sha(self.video),
            "story_beats": [
                {
                    "speech": f"The fox investigates event {i}.",
                    "visual_prompt": f"The fox watches the clock at beat {i}.",
                    "story_beat": role,
                }
                for i, role in enumerate(
                    ("reveal", "build", "mechanism", "payoff"), 1)
            ],
        }
        self.packet = {
            "content_id": self.story["content_id"],
            "title": self.story["title"],
            "source_mp4_sha256": sha(self.video),
            "story_beat_count": 4,
            "review_status": "pending_independent_visual_inspection",
            "semantic_quality": "not_verified", "publication_approval": False,
            "sample_alignment": "planned_storybeat_midpoints",
            "sample_times_seconds": [2.893, 8.796, 14.742, 20.534],
            "beats": [
                {
                    "beat": i, "speech": beat["speech"],
                    "visual_prompt": beat["visual_prompt"],
                    "story_beat": beat["story_beat"],
                }
                for i, beat in enumerate(self.story["story_beats"], 1)
            ],
        }
        (self.root / "video.mp4").write_bytes(self.video)
        (self.root / "candidate.json").write_text(json.dumps(self.story))
        (self.root / "review.story-review.json").write_text(json.dumps(self.packet))
        self.checks = {"complete_video_reviewed": False,
                       "beat_checks": [{"beat": i, "character_visible": False}
                                       for i in range(1, 5)]}
        (self.root / "completed-checklist.json").write_text(json.dumps(self.checks))

    def run_builder(self):
        def fake_extract(video, timestamp, output):
            self.assertEqual(video, self.root / "video.mp4")
            self.assertTrue(0 < timestamp < 23.4)
            Image.new("RGB", (250, 444), (30, 40, 50)).save(output, "JPEG")
        with patch("astra_v2.review_timeline._duration", return_value=23.4), \
             patch("astra_v2.review_timeline._extract", side_effect=fake_extract):
            return build_review_timeline(self.root)

    def test_schedule_has_six_samples_per_actual_beat(self):
        samples = beat_sample_schedule(self.packet, 23.4)
        self.assertEqual(len(samples), 24)
        self.assertEqual([s["beat"] for s in samples], [1] * 6 + [2] * 6 +
                         [3] * 6 + [4] * 6)
        self.assertEqual([s["frame"] for s in samples], list(range(1, 7)) * 4)
        self.assertTrue(all(
            a["time_seconds"] < b["time_seconds"]
            for a, b in zip(samples, samples[1:])))
        self.assertGreater(samples[0]["time_seconds"], 0)
        self.assertLess(samples[-1]["time_seconds"], 23.4)

    def test_schedule_rejects_missing_alignment_instead_of_guessing(self):
        for variant in (
            {**self.packet, "sample_alignment": "equal_quarters"},
            {**self.packet, "sample_times_seconds": None},
            {**self.packet, "sample_times_seconds": [2, 2, 14, 20]},
            {**self.packet, "sample_times_seconds": [2, 8, 14, 24]},
            {**self.packet, "sample_times_seconds": [2, 8, 14, float("nan")]},
        ):
            with self.subTest(variant=variant["sample_times_seconds"]):
                with self.assertRaisesRegex(
                        ValueError, "unaligned_review_storybeat_timestamps"):
                    beat_sample_schedule(variant, 23.4)

    def test_rejects_excessive_sample_count_or_duration(self):
        with self.assertRaisesRegex(ValueError, "invalid_review_sample_count"):
            beat_sample_schedule(self.packet, 23.4, per_beat=99)
        with self.assertRaisesRegex(ValueError, "invalid_review_video_duration"):
            beat_sample_schedule(self.packet, 350.0)
        with self.assertRaisesRegex(ValueError, "invalid_review_video_duration"):
            beat_sample_schedule(self.packet, float("nan"))

    def test_builds_unsigned_timeline_without_modifying_original_artifacts(self):
        paths = [self.root / name for name in
                 ("candidate.json", "review.story-review.json",
                  "completed-checklist.json", "video.mp4")]
        original = {p: p.read_bytes() for p in paths}
        report = self.run_builder()
        self.assertEqual(report["frames"], 24)
        self.assertEqual(report["status"], "unsigned_timeline_ready")
        self.assertFalse(report["publication_approval"])
        self.assertFalse(report["publication_triggered"])
        self.assertEqual(original, {p: p.read_bytes() for p in paths})
        self.assertTrue((self.root / "timeline-24.jpg").exists())
        with Image.open(self.root / "timeline-24.jpg") as picture:
            self.assertEqual(picture.size, (1500, 1912))
        manifest = json.loads((self.root / "timeline-24.json").read_text())
        self.assertEqual(manifest["sample_count"], 24)
        self.assertEqual(manifest["source_mp4_sha256"], sha(self.video))
        self.assertEqual(manifest["semantic_quality"], "not_verified")
        for key in ("complete_video_reviewed", "publication_approval",
                    "publication_triggered", "reviewer_signature_created"):
            self.assertIs(manifest[key], False)
        self.assertEqual(manifest["frame_times"][0]["beat"], 1)
        self.assertEqual(manifest["frame_times"][-1]["beat"], 4)
        self.assertFalse((self.root / "independent-review.json").exists())

    def test_different_video_bytes_cannot_reuse_timeline(self):
        (self.root / "video.mp4").write_bytes(b"CHANGED")
        with self.assertRaisesRegex(ValueError, "timeline_story_or_video_identity_mismatch"):
            self.run_builder()
        self.assertFalse((self.root / "timeline-24.jpg").exists())

    def test_different_storybeat_cannot_reuse_packet(self):
        self.story["story_beats"][0]["speech"] = "Different first beat."
        (self.root / "candidate.json").write_text(json.dumps(self.story))
        with self.assertRaisesRegex(ValueError, "timeline_storybeat_mismatch"):
            self.run_builder()

    def test_approved_looking_unsigned_packet_is_rejected(self):
        self.packet["semantic_quality"] = "verified"
        (self.root / "review.story-review.json").write_text(json.dumps(self.packet))
        with self.assertRaisesRegex(ValueError, "timeline_story_or_video_identity_mismatch"):
            self.run_builder()

    def test_never_overwrites_existing_timeline_or_checklist(self):
        (self.root / "timeline-24.jpg").write_bytes(b"saved")
        before = (self.root / "completed-checklist.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "timeline_output_already_exists"):
            self.run_builder()
        self.assertEqual((self.root / "timeline-24.jpg").read_bytes(), b"saved")
        self.assertEqual((self.root / "completed-checklist.json").read_bytes(), before)

    def test_failed_frame_decode_leaves_no_partially_approved_files(self):
        count = {"n": 0}
        def broken_extract(video, timestamp, output):
            count["n"] += 1
            if count["n"] == 7:
                raise ValueError("timeline_frame_decode_failed")
            Image.new("RGB", (250, 444)).save(output, "JPEG")
        with patch("astra_v2.review_timeline._duration", return_value=23.4), \
             patch("astra_v2.review_timeline._extract", side_effect=broken_extract):
            with self.assertRaisesRegex(ValueError, "timeline_frame_decode_failed"):
                build_review_timeline(self.root)
        self.assertFalse((self.root / "timeline-24.jpg").exists())
        self.assertFalse((self.root / "timeline-24.json").exists())
        self.assertFalse((self.root / "independent-review.json").exists())


if __name__ == "__main__":
    unittest.main()
