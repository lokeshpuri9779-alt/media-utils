"""Data-only semantic inspection evidence: NEVER a publication-approval test."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from astra_v2.story_visual_review_packet import snapshot, build_packet, write_packet


def original_story():
    return {
        "content_id": "test-short-1", "genre": "fiction",
        "kind": "authored_causal_story", "production_ready": True,
        "title": "The Fox and the Clock",
        "story_beats": [
            {"speech": "The fox notices the clock has stopped.",
             "visual_prompt": "A red fox inspects an unmoving clock.",
             "visual": "clock", "story_beat": "reveal"},
            {"speech": "The fox reaches for the broken key.",
             "visual_prompt": "The fox picks up a tiny brass key.",
             "visual": "door", "story_beat": "build"},
        ],
    }


def evidence(story, digest="a" * 64):
    shots = [
        {"shot": 1, "status": "composited", "pixel_changed": True},
        {"shot": 2, "status": "composited", "pixel_changed": True},
    ]
    receipt = {"content_id": story["content_id"], "shot_count": 2,
               "shots": shots, "video_sha256": digest, "composited_shots": 2,
               "asset_coverage_status": "full"}
    manifest = {"source_mp4_sha256": digest, "contact_sheet_sha256": "b" * 64,
                "sample_count": 4,
                "sample_times_seconds": [0.2, 0.6, 1.0, 1.4],
                "semantic_quality": "not_verified", "publication_approval": False}
    return receipt, manifest


class StoryVisualReviewPacketTests(unittest.TestCase):
    def test_storyboard_is_immutable_and_links_mp4_not_false_approval(self):
        story = original_story()
        plan = [
            {"story_subject": "fox", "story_action": "look", "story_environment": "forest"},
            {"story_subject": "fox", "story_action": "pick", "story_environment": "forest"},
        ]
        source = snapshot(story, plan)
        story["story_beats"][0]["speech"] = "Changed AFTER render began."
        receipt, manifest = evidence(source)
        packet = build_packet(source, receipt, manifest)
        self.assertEqual(packet["story_beat_count"], 2)
        self.assertEqual(packet["rendered_shot_count"], 2)
        self.assertEqual(packet["beats"][1]["planned_action"], "pick")
        self.assertEqual(packet["beats"][0]["asset_shot_status"], "composited")
        self.assertIn("notices the clock", packet["beats"][0]["speech"])
        self.assertNotIn("Changed AFTER", str(packet))
        self.assertEqual(packet["sample_alignment"], "not_established")
        self.assertEqual(packet["semantic_quality"], "not_verified")
        self.assertFalse(packet["publication_approval"])
        self.assertFalse(packet["publication_triggered"])
        for beat in packet["beats"]:
            self.assertEqual(beat["narrated_action_visible"], "not_verified")
            self.assertEqual(beat["character_visible"], "not_verified")

    def test_human_action_context_is_not_confused_with_generic_studio_motion(self):
        story = original_story()
        story["story_beats"][0]["story_human_actor"] = "mara"
        story["story_beats"][0]["story_human_action"] = "trace_cable"
        plan = [
            {"story_action": "idle", "story_human_actor": "mara",
             "story_human_action": "trace_cable"},
            {"story_action": "pick", "story_human_action": "pick_key"},
        ]
        source = snapshot(story, plan)
        rows = source["beats"]
        self.assertEqual(rows[0]["planned_action"], "idle")
        self.assertEqual(rows[0]["authored_human_action"], "trace_cable")
        self.assertEqual(rows[0]["planned_human_action"], "trace_cable")
        self.assertEqual(rows[0]["human_action_metadata_status"], "matched_in_metadata")
        self.assertEqual(rows[0]["visual_prompt_provenance"], "authored_visual_prompt")
        self.assertEqual(rows[1]["human_action_metadata_status"], "not_declared")
        plan[0]["story_human_action"] = "idle"
        mismatch = snapshot(story, plan)
        self.assertEqual(mismatch["beats"][0]["human_action_metadata_status"], "mismatch")
        del plan[0]["story_human_action"]
        missing = snapshot(story, plan)
        self.assertEqual(missing["beats"][0]["human_action_metadata_status"], "missing_in_plan")
        receipt, manifest = evidence(missing)
        packet = build_packet(missing, receipt, manifest)
        self.assertEqual(packet["beats"][0]["human_action_metadata_status"], "missing_in_plan")
        self.assertEqual(packet["semantic_quality"], "not_verified")
        self.assertFalse(packet["publication_approval"])
        self.assertFalse(packet["publication_triggered"])

    def test_four_beats_align_to_actual_narration_timestamps_without_semantic_approval(self):
        story = original_story()
        story["story_beats"] += [
            {"speech": "The fox fits the key into the clock.",
             "visual_prompt": "A fox turns a brass key.", "visual": "clock",
             "story_beat": "mechanism"},
            {"speech": "The clock starts moving again.",
             "visual_prompt": "A fox smiles beside the working clock.",
             "visual": "clock", "story_beat": "payoff"},
        ]
        plan = [
            {"start": 0.0, "duration": 2.0, "story_subject": "fox"},
            {"start": 2.0, "duration": 3.0, "story_subject": "fox"},
            {"start": 5.0, "duration": 4.0, "story_subject": "fox"},
            {"start": 9.0, "duration": 1.0, "story_subject": "fox"},
        ]
        source = snapshot(story, plan)
        self.assertEqual(source["beat_midpoint_times_seconds"], [1.0, 3.5, 7.0, 9.5])
        receipt, manifest = evidence(source)
        receipt["shot_count"] = 4
        receipt["composited_shots"] = 4
        receipt["shots"] += [
            {"shot": 3, "status": "composited"},
            {"shot": 4, "status": "composited"},
        ]
        manifest["sample_strategy"] = "planned_beat_midpoints"
        manifest["sample_times_seconds"] = [1.0, 3.5, 7.0, 9.5]
        packet = build_packet(source, receipt, manifest)
        self.assertEqual(packet["sample_alignment"], "planned_storybeat_midpoints")
        self.assertEqual([beat["contact_sheet_frame_index"] for beat in packet["beats"]],
                         [1, 2, 3, 4])
        self.assertEqual(packet["semantic_quality"], "not_verified")
        self.assertFalse(packet["publication_approval"])
        self.assertTrue(all(b["narrated_action_visible"] == "not_verified"
                            for b in packet["beats"]))
        for bad in ([1.0, 3.5, 8.0, 9.5], [1.0, 3.5, 7.0, 9.51]):
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    ValueError, "storybeat_frame_timestamps_mismatch"):
                build_packet(source, receipt, {**manifest, "sample_times_seconds": bad})

    def test_missing_or_ambiguous_plan_does_not_invent_midpoint_alignment(self):
        story = original_story()
        story["story_beats"] += [
            {"speech": "And the key turns."},
            {"speech": "The clock chimes."},
        ]
        plans = [
            [],
            [{"start": 0, "duration": 1}] * 4,
            [{"start": 0, "duration": 1}, {"start": 1, "duration": 1},
             {"start": 2, "duration": float("nan")},
             {"start": 3, "duration": 1}],
        ]
        for plan in plans:
            with self.subTest(plan=plan):
                source = snapshot(story, plan)
                self.assertIsNone(source["beat_midpoint_times_seconds"])
                receipt, manifest = evidence(source)
                receipt["shot_count"] = 4
                receipt["shots"] *= 2
                self.assertEqual(build_packet(source, receipt, manifest)["sample_alignment"],
                                 "not_established")
                with self.assertRaisesRegex(ValueError, "storybeat_frame_timestamps_mismatch"):
                    build_packet(source, receipt, {
                        **manifest,
                        "sample_strategy": "planned_beat_midpoints"})

    def test_hash_and_identity_mismatches_fail_closed(self):
        source = snapshot(original_story())
        receipt, manifest = evidence(source)
        for change in ("video_hash", "sheet_hash", "story_id", "no_shots", "missing_samples"):
            with self.subTest(change=change):
                r, m = dict(receipt), dict(manifest)
                if change == "video_hash":
                    m["source_mp4_sha256"] = "b" * 64
                elif change == "sheet_hash":
                    m["contact_sheet_sha256"] = "wrong"
                elif change == "story_id":
                    r["content_id"] = "wrong-story"
                elif change == "no_shots":
                    r["shots"] = []
                else:
                    m["sample_times_seconds"] = []
                with self.assertRaises(ValueError):
                    build_packet(source, r, m)

    def test_garbled_sample_times_do_not_verify(self):
        source = snapshot(original_story())
        receipt, manifest = evidence(source)
        for invalid in ([0.3, 0.2, 1, 2], [0.1, 0.1, 1, 2],
                        [0, float("nan"), 1, 2], [True, 0.2, 1, 2]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                build_packet(source, receipt, {**manifest, "sample_times_seconds": invalid})

    def test_missing_or_foreign_storyboard_does_not_claim_approval(self):
        self.assertIsNone(snapshot({"genre": "current"}))
        self.assertEqual(snapshot({"genre": "fiction", "story_beats": []})["status"],
                         "invalid_storyboard")
        source = snapshot(original_story())
        self.assertEqual(source["status"], "captured")
        with self.assertRaises(ValueError):
            build_packet({"status": "invalid_storyboard"}, *evidence(source))

    def test_mismatched_plan_does_not_invent_asset_to_storybeat_alignment(self):
        source = snapshot(original_story(), plan=[{"story_action": "pick"}])
        receipt, manifest = evidence(source)
        receipt["shot_count"] = 1
        receipt["shots"] = receipt["shots"][:1]
        packet = build_packet(source, receipt, manifest)
        self.assertTrue(all(x["asset_shot_status"] == "not_aligned"
                            for x in packet["beats"]))
        self.assertFalse(packet["publication_approval"])

    def test_writer_serializes_bounded_evidence_only(self):
        source = snapshot(original_story())
        receipt, manifest = evidence(source)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "review.story-review.json"
            jpeg = Path(folder) / "review.jpg"
            jpeg.write_bytes(b"sampled frames fixture")
            manifest["contact_sheet_sha256"] = hashlib.sha256(jpeg.read_bytes()).hexdigest()
            result = write_packet(source, receipt, manifest, output,
                                  contact_sheet_path=jpeg)
            packet = json.loads(output.read_text())
            self.assertEqual(result["source_mp4_sha256"], receipt["video_sha256"])
            self.assertFalse(result["publication_approval"])
            self.assertFalse(packet["publication_approval"])
            self.assertLess(output.stat().st_size, 30_000)

    def test_compositor_finish_emits_bound_packet_without_approving(self):
        from astra_v2.asset_usage_audit import begin, observe, finish
        story = original_story()
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            video = directory / "actual.mp4"
            video.write_bytes(b"test synthetic video hash only, no encoded frames")
            digest = hashlib.sha256(video.read_bytes()).hexdigest()
            review_dir = directory / "review"
            sheet = review_dir / "sample.jpg"
            manifest_path = sheet.with_suffix(".json")

            def sampled(*args, **kwargs):
                review_dir.mkdir(exist_ok=True)
                sheet.write_bytes(b"mock sheet; separately decoded frame tests exist")
                contact_hash = hashlib.sha256(sheet.read_bytes()).hexdigest()
                manifest_path.write_text(json.dumps({
                    "source_mp4_sha256": digest,
                    "contact_sheet_sha256": contact_hash,
                    "sample_count": 4,
                    "sample_times_seconds": [0.2, 0.6, 1.0, 1.4],
                    "semantic_quality": "not_verified", "publication_approval": False,
                }))
                return {"path": str(sheet), "manifest": str(manifest_path),
                        "source_mp4_sha256": digest, "sample_count": 4}
            env = {"ASTRA_ASSET_PACK_ENABLED": "1", "ASTRA_ASSET_PACK_AUDIT": "1",
                   "ASTRA_ASSET_AUDIT_DIR": str(directory / "asset-audit"),
                   "ASTRA_VISUAL_REVIEW_SHEET": "1",
                   "ASTRA_VISUAL_REVIEW_DIR": str(review_dir)}
            with patch.dict(os.environ, env), patch(
                "astra_v2.render_contact_sheet.create_contact_sheet", side_effect=sampled):
                self.assertTrue(begin(story, 2, plan=[
                    {"story_subject": "fox", "story_action": "look"},
                    {"story_subject": "fox", "story_action": "pick"},
                ]))
                for i in (1, 2):
                    observe(i, {"scene": None, "source_field": None,
                                "matched_term": None}, "scene_unresolved", story["content_id"])
                receipt = finish(video, renderer="studio-test", expected_shots=2)
            review = list(review_dir.glob("*.story-review.json"))
            self.assertEqual(len(review), 1)
            packet = json.loads(review[0].read_text())
            self.assertEqual(packet["source_mp4_sha256"], receipt["video_sha256"])
            self.assertEqual(packet["story_sha256"], snapshot(story)["story_sha256"])
            self.assertFalse(packet["publication_approval"])
            self.assertEqual(packet["semantic_quality"], "not_verified")

    def test_actual_asset_audit_forwards_narration_midpoints_to_decoder(self):
        from astra_v2.asset_usage_audit import begin, observe, finish
        story = original_story()
        story["story_beats"] += [
            {"speech": "A fox places the key.", "visual": "clock"},
            {"speech": "The clock works.", "visual": "clock"},
        ]
        plan = [
            {"start": 0, "duration": 2, "story_action": "look"},
            {"start": 2, "duration": 2, "story_action": "pick"},
            {"start": 4, "duration": 2, "story_action": "hold"},
            {"start": 6, "duration": 2, "story_action": "look"},
        ]
        expected = [1.0, 3.0, 5.0, 7.0]
        captured = []
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            video = folder / "actual.mp4"
            video.write_bytes(b"synthetic SHA256 receipt fixture")
            digest = hashlib.sha256(video.read_bytes()).hexdigest()
            review_dir = folder / "review"
            def sampled(_, output, **kwargs):
                captured.append(kwargs.get("sample_times_seconds"))
                img = Path(output)
                img.parent.mkdir(parents=True, exist_ok=True)
                img.write_bytes(b"fake decoded sheet; unit integration only")
                sample_manifest = {
                    "source_mp4_sha256": digest,
                    "contact_sheet_sha256": hashlib.sha256(img.read_bytes()).hexdigest(),
                    "sample_count": 4,
                    "sample_times_seconds": expected,
                    "sample_strategy": "planned_beat_midpoints",
                }
                manifest = img.with_suffix(".json")
                manifest.write_text(json.dumps(sample_manifest))
                return {"path": str(img), "manifest": str(manifest),
                        "source_mp4_sha256": digest, "sample_count": 4}
            with patch.dict(os.environ, {
                "ASTRA_ASSET_PACK_ENABLED": "1", "ASTRA_ASSET_PACK_AUDIT": "1",
                "ASTRA_ASSET_AUDIT_DIR": str(folder / "receipts"),
                "ASTRA_VISUAL_REVIEW_SHEET": "1",
                "ASTRA_VISUAL_REVIEW_DIR": str(review_dir),
            }), patch("astra_v2.render_contact_sheet.create_contact_sheet",
                      side_effect=sampled):
                self.assertTrue(begin(story, 4, plan=plan))
                for i in range(1, 5):
                    observe(i, {"scene": None, "source_field": None,
                                "matched_term": None}, "scene_unresolved",
                            story["content_id"])
                receipt = finish(video, renderer="studio-test", expected_shots=4)
            self.assertEqual(captured, [expected])
            packets = list(review_dir.glob("*.story-review.json"))
            self.assertEqual(len(packets), 1)
            packet = json.loads(packets[0].read_text())
            self.assertEqual(packet["sample_alignment"], "planned_storybeat_midpoints")
            self.assertEqual(packet["source_mp4_sha256"], receipt["video_sha256"])
            self.assertFalse(packet["publication_approval"])
            self.assertEqual(packet["semantic_quality"], "not_verified")

    def test_swapped_contact_jpeg_cannot_generate_review_packet(self):
        source = snapshot(original_story())
        receipt, manifest = evidence(source)
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "sheet.jpg"
            output = Path(folder) / "review.story-review.json"
            image.write_bytes(b"original frame samples")
            manifest["contact_sheet_sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
            image.write_bytes(b"tampered frame samples")
            with self.assertRaisesRegex(ValueError, "contact_sheet_hash_mismatch"):
                write_packet(source, receipt, manifest, output,
                             contact_sheet_path=image)
            self.assertFalse(output.exists())

    def test_preload_and_publisher_archive_visual_evidence(self):
        root = Path(__file__).resolve().parents[1]
        pre = (root / ".github/workflows/astra-v2-preload.yml").read_text()
        publisher = (root / ".github/workflows/astra-v2-publish.yml").read_text()
        self.assertIn("ASTRA_VISUAL_REVIEW_SHEET: '1'", pre)
        self.assertIn("astra-preload-story-review-", pre)
        self.assertIn("ASTRA_VISUAL_REVIEW_SHEET: '1'", publisher)
        self.assertIn("Archive sampled MP4 frames for manual visual review", publisher)
        renderer = (root / "studio_renderer.py").read_text()
        self.assertIn("begin_asset_audit(ch, len(plan), plan=plan)", renderer)


if __name__ == "__main__":
    unittest.main()
