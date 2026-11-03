"""Synthetic geometry tests; annotations cannot certify visual identity."""
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from astra_v2.annotated_object_motion import (
    _bbox_gap, _bbox_iou, _box, build_object_motion_evidence,
    create_annotation_template, measure_marked_regions,
)
from astra_v2.review_timeline import beat_sample_schedule


def sha(data):
    return hashlib.sha256(data).hexdigest()


class AnnotatedObjectMotionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = b"FAKE MP4, no complete human inspection"
        self.story = {
            "content_id": "manual-region-demo",
            "title": "A Fox and a Lantern",
            "genre": "fiction", "format": "short",
            "sha256": sha(self.video),
            "story_beats": [
                {"speech": f"The fox examines moment {i}.",
                 "visual_prompt": f"Fox near prop in moment {i}.",
                 "story_beat": role}
                for i, role in enumerate(
                    ("reveal", "build", "mechanism", "payoff"), 1)
            ],
        }
        self.packet = {
            "content_id": self.story["content_id"],
            "title": self.story["title"],
            "source_mp4_sha256": sha(self.video),
            "review_status": "pending_independent_visual_inspection",
            "semantic_quality": "not_verified",
            "publication_approval": False,
            "sample_alignment": "planned_storybeat_midpoints",
            "sample_times_seconds": [3.0, 9.0, 15.0, 21.0],
            "beats": [
                {"beat": i, **beat}
                for i, beat in enumerate(self.story["story_beats"], 1)
            ],
        }
        (self.root / "video.mp4").write_bytes(self.video)
        (self.root / "candidate.json").write_text(json.dumps(self.story))
        (self.root / "review.story-review.json").write_text(json.dumps(self.packet))
        (self.root / "completed-checklist.json").write_text(json.dumps({
            "complete_video_reviewed": False,
            "beat_checks": [
                {"beat": i, "character_visible": False, "narrated_action_visible": False}
                for i in range(1, 5)
            ],
        }))
        sheet = Image.new("RGB", (1500, 1912), (20, 30, 40))
        sheet.save(self.root / "timeline-24.jpg", format="JPEG")
        self.schedule = beat_sample_schedule(self.packet, 24.0)
        self.timeline = {
            "kind": "unsigned_review_timeline",
            "content_id": self.story["content_id"],
            "source_mp4_sha256": sha(self.video),
            "source_review_packet_sha256":
                sha((self.root / "review.story-review.json").read_bytes()),
            "timeline_jpeg_sha256":
                sha((self.root / "timeline-24.jpg").read_bytes()),
            "sample_count": 24,
            "sample_alignment": "estimated_beat_segments_from_planned_midpoints",
            "frame_times": self.schedule,
            "semantic_quality": "not_verified",
            "publication_approval": False,
        }
        (self.root / "timeline-24.json").write_text(json.dumps(self.timeline))

    def call(self, fn, *args):
        with patch("astra_v2.mp4_motion_evidence._duration", return_value=24.0):
            return fn(self.root, *args)

    def fill(self, *, move_subject=True, overlap=False):
        self.call(create_annotation_template)
        path = self.root / "object-region-annotations.json"
        content = json.loads(path.read_text())
        for i, frame in enumerate(content["frames"]):
            x = .3 + (i % 6) * .04 if move_subject else .3
            frame["subject_box"] = [x, .32, x + .16, .57]
            frame["prop_box"] = (
                [x + .08, .4, x + .17, .5] if overlap
                else [.7, .45, .8, .55]
            )
        path.write_text(json.dumps(content))
        return path

    def test_normalized_box_geometry_and_validation(self):
        self.assertEqual(_box([0.1, 0.2, 0.4, 0.8]),
                         (0.1, 0.2, 0.4, 0.8))
        self.assertEqual(_bbox_gap((0, 0, .2, .2), (.4, 0, .6, .2),
                                   250, 444), 50)
        self.assertAlmostEqual(_bbox_iou((0, 0, .2, .2), (.1, 0, .3, .2)), 1 / 3)
        for invalid in ([0, 0, 0, 1], [0, .1, 2, .5],
                        [0, 0, .1, float("nan")], [0, 0, True, .8],
                        ["0", 0, .5, .5], [0, .1, .2], "bad"):
            with self.subTest(box=invalid):
                with self.assertRaisesRegex(ValueError, "invalid_object_region_box"):
                    _box(invalid)

    def test_moving_subject_has_span_without_semantic_verification(self):
        annotations = []
        for i in range(24):
            x = .2 + (i % 6) * .05
            annotations.append({
                "subject_box": (x, .3, x + .1, .6),
                "prop_box": (.7, .4, .8, .5),
            })
        result = measure_marked_regions(annotations, 250, 444)
        self.assertEqual(len(result), 4)
        self.assertTrue(all(b["subject_center_span_px"] > 50 for b in result))
        self.assertTrue(all(b["prop_center_span_px"] == 0 for b in result))
        self.assertTrue(all(b["character_motion_verified"] is False
                            and b["prop_contact_verified"] is False
                            for b in result))

    def test_box_overlap_is_not_verified_contact(self):
        self.fill(overlap=True)
        report = self.call(build_object_motion_evidence)
        self.assertEqual(report["semantic_quality"], "not_verified")
        values = json.loads((self.root / "object-region-evidence.json").read_text())
        self.assertTrue(all(x["annotated_box_overlap_samples"] == 6
                            and x["prop_contact_verified"] is False
                            and x["narrated_action_verified"] is False
                            for x in values["beats"]))

    def test_create_blank_template_does_not_auto_label_or_approve(self):
        result = self.call(create_annotation_template)
        self.assertFalse(result["review_approved"])
        path = self.root / "object-region-annotations.json"
        annotations = json.loads(path.read_text())
        self.assertEqual(len(annotations["frames"]), 24)
        self.assertTrue(all(x["subject_box"] is None and x["prop_box"] is None
                            for x in annotations["frames"]))
        self.assertFalse(annotations["independent_full_video_review"])
        self.assertFalse(annotations["publication_approval"])
        with self.assertRaisesRegex(ValueError, "object_annotations_empty"):
            self.call(build_object_motion_evidence)

    def test_real_provenance_bound_full_report_preserves_inputs(self):
        self.fill()
        original = {p: p.read_bytes() for p in self.root.iterdir()}
        result = self.call(build_object_motion_evidence)
        self.assertEqual(result["measurement_count"], 4)
        self.assertFalse(result["publication_approval"])
        self.assertEqual({p: p.read_bytes() for p in original}, original)
        report = json.loads((self.root / "object-region-evidence.json").read_text())
        self.assertEqual(report["source_mp4_sha256"], sha(self.video))
        self.assertEqual(len(report["beats"]), 4)
        for key in ("complete_video_reviewed", "publication_approval",
                    "publication_triggered", "reviewer_signature_created"):
            self.assertIs(report[key], False)
        self.assertFalse((self.root / "independent-review.json").exists())
        with Image.open(self.root / "object-region-overlay.png") as image:
            self.assertEqual(image.size, (1500, 1776))

    def test_wrong_media_or_timeline_cannot_reuse_annotations(self):
        self.fill()
        (self.root / "video.mp4").write_bytes(b"DIFFERENT MP4")
        with self.assertRaisesRegex(ValueError, "motion_source_provenance_mismatch"):
            self.call(build_object_motion_evidence)
        self.assertFalse((self.root / "object-region-overlay.png").exists())

    def test_replaced_timeline_cannot_reuse_annotations(self):
        self.fill()
        (self.root / "timeline-24.jpg").write_bytes(b"not a frame image")
        with self.assertRaisesRegex(ValueError, "motion_source_provenance_mismatch"):
            self.call(build_object_motion_evidence)

    def test_changed_annotation_video_digest_rejected(self):
        path = self.fill()
        content = json.loads(path.read_text())
        content["source_mp4_sha256"] = "0" * 64
        path.write_text(json.dumps(content))
        with self.assertRaisesRegex(ValueError, "untrusted_object_annotation_provenance"):
            self.call(build_object_motion_evidence)

    def test_moved_or_duplicate_frame_index_rejected(self):
        path = self.fill()
        content = json.loads(path.read_text())
        content["frames"][2]["frame"] = 2
        path.write_text(json.dumps(content))
        with self.assertRaisesRegex(ValueError, "object_annotation_frame_identity_mismatch"):
            self.call(build_object_motion_evidence)

    def test_false_human_review_flag_must_remain_false(self):
        path = self.fill()
        content = json.loads(path.read_text())
        content["independent_full_video_review"] = True
        path.write_text(json.dumps(content))
        with self.assertRaisesRegex(ValueError, "untrusted_object_annotation_provenance"):
            self.call(build_object_motion_evidence)

    def test_no_overwrite_of_previous_evidence(self):
        self.fill()
        prior = self.root / "object-region-evidence.json"
        prior.write_text("already reviewed independently elsewhere")
        with self.assertRaisesRegex(ValueError, "object_evidence_already_exists"):
            self.call(build_object_motion_evidence)
        self.assertEqual(prior.read_text(),
                         "already reviewed independently elsewhere")

    def test_partial_region_annotations_do_not_invent_missing_motion(self):
        path = self.fill(move_subject=False)
        content = json.loads(path.read_text())
        for row in content["frames"]:
            row["prop_box"] = None
        path.write_text(json.dumps(content))
        self.call(build_object_motion_evidence)
        report = json.loads((self.root / "object-region-evidence.json").read_text())
        self.assertTrue(all(row["subject_center_span_px"] == 0
                            and row["prop_center_span_px"] is None
                            and row["min_subject_prop_box_gap_px"] is None
                            and row["review_hint"] == "insufficient_manual_regions"
                            for row in report["beats"]))


if __name__ == "__main__":
    unittest.main()
