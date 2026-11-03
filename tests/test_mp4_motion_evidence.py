"""Read-only pixel-change evidence tests; synthetic pixels are NOT video review."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from astra_v2.mp4_motion_evidence import (
    compare_review_frames, build_motion_evidence,
)
from astra_v2.review_timeline import beat_sample_schedule


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sample_image(index, *, center_motion=False, side_motion=False):
    frame = Image.new("L", (250, 444), 30)
    d = ImageDraw.Draw(frame)
    if center_motion:
        x = 80 + (index % 6) * 13
        d.rectangle((x, 160, x + 40, 270), fill=215)
    else:
        d.rectangle((92, 160, 132, 270), fill=215)
    if side_motion:
        d.rectangle((0, 160, 34, 255),
                    fill=235 if index % 2 else 30)
        d.rectangle((215, 160, 249, 255),
                    fill=235 if index % 2 else 30)
    return frame


class MP4MotionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        video = b"synthetic fake MP4, not real video review"
        self.video_bytes = video
        self.candidate = {
            "content_id": "scene-motion-test",
            "title": "The Fox and the Clock",
            "genre": "fiction", "format": "short", "sha256": sha(video),
            "story_beats": [
                {"speech": f"The fox notices event {n}.",
                 "visual_prompt": f"The fox moves in beat {n}.",
                 "story_beat": role}
                for n, role in enumerate(
                    ("reveal", "build", "mechanism", "payoff"), 1)
            ],
        }
        self.packet = {
            "content_id": self.candidate["content_id"],
            "title": self.candidate["title"],
            "source_mp4_sha256": sha(video),
            "review_status": "pending_independent_visual_inspection",
            "semantic_quality": "not_verified",
            "publication_approval": False,
            "sample_alignment": "planned_storybeat_midpoints",
            "sample_times_seconds": [3.0, 9.0, 15.0, 21.0],
            "beats": [
                {"beat": n, **beat}
                for n, beat in enumerate(self.candidate["story_beats"], 1)
            ],
        }
        (self.root / "video.mp4").write_bytes(video)
        (self.root / "candidate.json").write_text(json.dumps(self.candidate))
        (self.root / "review.story-review.json").write_text(json.dumps(self.packet))
        (self.root / "completed-checklist.json").write_text(json.dumps({
            "complete_video_reviewed": False,
            "beat_checks": [{"beat": n, "character_visible": False}
                            for n in range(1, 5)],
        }))
        self.make_sheet()

    def make_sheet(self, *, center_motion=True, side_motion=False):
        sheet = Image.new("RGB", (1500, 1912), (5, 5, 5))
        for i in range(24):
            frame = sample_image(i, center_motion=center_motion,
                                 side_motion=side_motion).convert("RGB")
            sheet.paste(frame, ((i % 6) * 250, (i // 6) * 478 + 34))
        sheet.save(self.root / "timeline-24.jpg", "JPEG", quality=94)
        manifest = {
            "kind": "unsigned_review_timeline",
            "content_id": self.candidate["content_id"],
            "source_mp4_sha256": sha(self.video_bytes),
            "source_review_packet_sha256": sha(
                (self.root / "review.story-review.json").read_bytes()),
            "timeline_jpeg_sha256": sha(
                (self.root / "timeline-24.jpg").read_bytes()),
            "sample_count": 24,
            "sample_alignment": "estimated_beat_segments_from_planned_midpoints",
            "frame_times": beat_sample_schedule(self.packet, 24.0),
            "semantic_quality": "not_verified",
            "publication_approval": False,
        }
        (self.root / "timeline-24.json").write_text(json.dumps(manifest))

    def build(self):
        with patch("astra_v2.mp4_motion_evidence._duration",
                   return_value=24.0):
            return build_motion_evidence(self.root)

    def test_static_center_has_low_observable_change(self):
        rows, maps = compare_review_frames([
            sample_image(i).convert("L") for i in range(24)])
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(maps), 4)
        self.assertTrue(all(row["review_hint"] ==
                            "limited_center_stage_pixel_change"
                            for row in rows))
        self.assertFalse(any(row["character_motion_verified"] for row in rows))

    def test_center_motion_not_automatically_semantically_approved(self):
        rows, _ = compare_review_frames([
            sample_image(i, center_motion=True) for i in range(24)])
        self.assertTrue(all(
            row["center_stage_changed_fraction_median"] > .01 for row in rows))
        self.assertTrue(all(row["review_hint"] ==
                            "pixel_change_observed_action_unverified" for row in rows))
        for row in rows:
            self.assertFalse(row["character_motion_verified"])
            self.assertFalse(row["prop_contact_verified"])
            self.assertFalse(row["narrated_action_verified"])

    def test_background_motion_does_not_prove_character_motion(self):
        rows, _ = compare_review_frames([
            sample_image(i, side_motion=True) for i in range(24)])
        self.assertTrue(all(row["review_hint"] ==
                            "background_motion_confounded" for row in rows))
        self.assertFalse(any(row["narrated_action_verified"] for row in rows))

    def test_rejects_missing_or_inconsistent_images(self):
        with self.assertRaisesRegex(ValueError, "motion_review_requires_24_frames"):
            compare_review_frames([sample_image(0)])
        frames = [sample_image(i) for i in range(24)]
        frames[-1] = Image.new("L", (180, 300))
        with self.assertRaisesRegex(ValueError, "motion_frame_geometry_invalid"):
            compare_review_frames(frames)

    def test_generates_only_unsigned_evidence_and_preserves_original_files(self):
        originals = {p: p.read_bytes() for p in self.root.iterdir()}
        result = self.build()
        self.assertEqual(result["status"], "unsigned_motion_evidence_ready")
        self.assertTrue(result["review_required"])
        self.assertFalse(result["publication_approval"])
        self.assertEqual({p: p.read_bytes() for p in originals}, originals)
        report = json.loads((self.root / "motion-evidence.json").read_text())
        self.assertEqual(report["source_mp4_sha256"], sha(self.video_bytes))
        self.assertEqual(len(report["metrics"]), 4)
        self.assertEqual(report["semantic_quality"], "not_verified")
        for field in ("complete_video_reviewed", "publication_approval",
                      "publication_triggered", "reviewer_signature_created"):
            self.assertIs(report[field], False)
        self.assertFalse((self.root / "independent-review.json").exists())
        with Image.open(self.root / "motion-heatmap.png") as heatmap:
            self.assertEqual(heatmap.size, (1000, 444))

    def test_changed_video_fails_before_outputs(self):
        (self.root / "video.mp4").write_bytes(b"another MP4")
        with self.assertRaisesRegex(ValueError, "motion_source_provenance_mismatch"):
            self.build()
        self.assertFalse((self.root / "motion-evidence.json").exists())

    def test_tampered_timeline_image_fails(self):
        (self.root / "timeline-24.jpg").write_bytes(b"spoofed screenshot")
        with self.assertRaisesRegex(ValueError, "motion_source_provenance_mismatch"):
            self.build()

    def test_changed_storybeat_text_fails(self):
        self.candidate["story_beats"][0]["speech"] = "Altered after rendering."
        (self.root / "candidate.json").write_text(json.dumps(self.candidate))
        with self.assertRaisesRegex(ValueError, "motion_story_beat_mismatch"):
            self.build()

    def test_fake_sample_times_fail(self):
        timeline = json.loads((self.root / "timeline-24.json").read_text())
        timeline["frame_times"][0]["time_seconds"] = 0.123
        (self.root / "timeline-24.json").write_text(json.dumps(timeline))
        with self.assertRaisesRegex(ValueError, "motion_sample_times_mismatch"):
            self.build()

    def test_reviewer_flag_spoofing_fails(self):
        timeline = json.loads((self.root / "timeline-24.json").read_text())
        timeline["semantic_quality"] = "verified"
        (self.root / "timeline-24.json").write_text(json.dumps(timeline))
        with self.assertRaisesRegex(ValueError, "motion_source_provenance_mismatch"):
            self.build()

    def test_never_overwrites_previous_review_evidence(self):
        prior = self.root / "motion-evidence.json"
        prior.write_text("independent reviewer record must not change")
        with self.assertRaisesRegex(ValueError, "motion_evidence_output_already_exists"):
            self.build()
        self.assertEqual(prior.read_text(),
                         "independent reviewer record must not change")

    def test_decoder_not_used_when_video_hash_mismatch(self):
        (self.root / "video.mp4").write_bytes(b"wrong")
        with patch("astra_v2.mp4_motion_evidence._duration",
                   side_effect=AssertionError("should not decode")):
            with self.assertRaisesRegex(ValueError, "motion_source_provenance_mismatch"):
                build_motion_evidence(self.root)


if __name__ == "__main__":
    unittest.main()
