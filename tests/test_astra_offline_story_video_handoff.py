"""Negative controls for source-bound offline story-to-actual-video evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.astra_offline_story_video_handoff import (
    FRAMES, SIZE, SOURCE_SHA, STAGES, STORIES, WITNESSES,
    audit_decoded_frames, validate_metadata, verify,
)


def source_fixture():
    packets, video_previews = [], []
    for case, (digest, actor) in STORIES.items():
        shots = []
        for index, stage in enumerate(STAGES):
            shots.append({
                "stage": stage, "character_id": actor,
                "source_beat": "The character performs a concrete action, with a result.",
                "focus_state": f"state_{index+1}",
                "before_state": [f"state_{index}"],
                "after_state": [f"state_{index+1}"],
                "asset_verification": "not_verified",
                "frame_generation_executed": False,
                "manual_visual_review_required": True,
            })
        packets.append({
            "case_id": case, "story_digest": digest, "character_id": actor,
            "shot_count": 4, "event_state_contract_valid": True,
            "story_visual_semantics": "not_verified",
            "source_status": "assistant_drafted_reference_not_independently_reviewed",
            "shots": shots, "approved": False,
            "published": False, "production_ready": False,
        })
        video_previews.append({
            "case_id": case, "file": case + ".mp4", "sha256": "a"*64,
            "bytes": 2048, "frame_count": 48, "decoded_frame_count_verified": 48,
            "fps": 12, "dimensions": [320, 180], "codec": "h264",
            "pixel_changes_verified": True, "visible_story_outcome_cues_verified": True,
            "shot_pixel_evidence": [{"stage": stage} for stage in STAGES],
            "decoded_mp4_visual_cues": {"case_id": case, "passed": True},
            "decoded_character_presence_cues": {
                "case_id": case, "character_id": actor, "passed": True,
                "character_identity_semantics": "not_verified",
            },
            "story_semantic_accuracy": "not_verified",
            "review_only": True, "approved": False,
            "published": False, "production_ready": False,
        })
    return ({
        "experiment": "astra-offline-storyboards-v1",
        "reference_count": 3, "total_shots": 12, "packets": packets,
        "real_model_inference_executed": False, "frames_rendered": False,
        "semantic_fidelity": "not_verified",
        "manual_editorial_and_visual_review_required": True,
        "approved": False, "published": False, "production_ready": False,
    }, {
        "experiment": "astra-cpu-procedural-motion-proofs-v1",
        "video_count": 3, "video_previews": video_previews,
        "model_inference_executed": False,
        "human_visual_review_required": True, "production_quality": "not_verified",
        "approved": False, "published": False, "production_ready": False,
    })


def decoded_fixture(cid):
    frames = [Image.new("RGB", SIZE, (5, 12, 20)) for _ in range(FRAMES)]
    for index in range(4):
        ImageDraw.Draw(frames[(index+1)*12-1]).rectangle(
            (43, 30, 284, 153), fill=(110, 120, 130))
    final = ImageDraw.Draw(frames[-1])
    for index, (_, (region, color, _, _, _)) in enumerate(WITNESSES[cid].items()):
        x0, y0, x1, y1 = region
        if cid == "moon-mirror-garden":
            x0, x1 = (130, 168) if index == 0 else (82, 120)
        final.rectangle((x0, y0, x1-1, y1-1), fill=color)
    return frames


class OfflineStoryVideoHandoffTests(unittest.TestCase):
    def test_valid_reference_handoff_is_still_unapproved(self):
        board, preview = source_fixture()
        a, b = validate_metadata(board, preview)
        self.assertEqual(set(a), set(STORIES))
        self.assertEqual(set(b), set(STORIES))

    def test_story_digests_cannot_be_silently_replaced(self):
        board, preview = source_fixture()
        board["packets"][0]["story_digest"] = "f"*64
        with self.assertRaisesRegex(ValueError, "identity"):
            validate_metadata(board, preview)

    def test_video_and_story_case_ids_must_match(self):
        board, preview = source_fixture()
        preview["video_previews"][0]["file"] = "footbridge-ducklings.mp4"
        with self.assertRaisesRegex(ValueError, "mismatched"):
            validate_metadata(board, preview)

    def test_missing_case_or_repeated_case_fails(self):
        board, preview = source_fixture()
        preview["video_previews"][0]["case_id"] = preview["video_previews"][1]["case_id"]
        with self.assertRaisesRegex(ValueError, "duplicated"):
            validate_metadata(board, preview)

    def test_unapproved_flags_cannot_be_promoted(self):
        for field in ("approved", "published", "production_ready"):
            with self.subTest(field=field):
                board, preview = source_fixture()
                preview["video_previews"][0][field] = True
                with self.assertRaises(ValueError):
                    validate_metadata(board, preview)

    def test_missing_payoff_state_and_bad_order_fail(self):
        board, preview = source_fixture()
        board["packets"][0]["shots"][3]["focus_state"] = "never_observed"
        with self.assertRaisesRegex(ValueError, "visible-action"):
            validate_metadata(board, preview)
        board, preview = source_fixture()
        board["packets"][0]["shots"][2]["before_state"] = ["unrelated"]
        with self.assertRaisesRegex(ValueError, "discontinuity"):
            validate_metadata(board, preview)

    def test_four_decoded_stages_and_both_outcome_cues(self):
        for cid in STORIES:
            with self.subTest(cid=cid):
                report = audit_decoded_frames(cid, decoded_fixture(cid))
                self.assertEqual(len(report["four_beat_scene_motion"]), 4)
                self.assertEqual(len(report["fixed_profile_payoff_pixels"]), 2)
                self.assertFalse(report["approved"])
                self.assertEqual(report["narrative_semantics"], "not_verified")

    def test_frozen_or_caption_only_frames_fail(self):
        for cid in STORIES:
            with self.subTest(cid=cid):
                frames = decoded_fixture(cid)
                for i in range(11, FRAMES, 12):
                    frames[i] = frames[i-11].copy()
                with self.assertRaisesRegex(ValueError, "visual-action"):
                    audit_decoded_frames(cid, frames)

    def test_omitted_second_payoff_cue_fails(self):
        for cid in STORIES:
            with self.subTest(cid=cid):
                frames = decoded_fixture(cid)
                # Remove all marker-color pixels from final payoff.
                frames[-1] = Image.new("RGB", SIZE, (110, 120, 130))
                with self.assertRaisesRegex(ValueError, "payoff"):
                    audit_decoded_frames(cid, frames)

    def test_cross_case_and_incomplete_video_fail_closed(self):
        with self.assertRaises(ValueError):
            audit_decoded_frames("unsupported-case", decoded_fixture(next(iter(STORIES))))
        with self.assertRaises(ValueError):
            audit_decoded_frames(next(iter(STORIES)), [Image.new("RGB", SIZE)]*47)

    def test_stale_source_sha_rejected_before_any_decode(self):
        board, preview = source_fixture()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"preview").mkdir()
            (root/"storyboard.json").write_text(json.dumps(board), encoding="utf-8")
            (root/"preview"/"review-report.json").write_text(json.dumps(preview), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Source SHA"):
                verify(root/"storyboard.json", root/"preview", "0"*40)
            self.assertEqual(len(SOURCE_SHA), 40)


if __name__ == "__main__":
    unittest.main()
