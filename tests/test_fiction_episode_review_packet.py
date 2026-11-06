"""Offline proof that decoded video evidence cannot grant semantic approval."""
import hashlib
import json
from pathlib import Path
from io import BytesIO
import tempfile
import unittest

from PIL import Image

from astra_v2.fiction_episode_review_packet import create_episode_packet


def fixture(root):
    actions = ("discover_radio", "trace_cable", "hear_warning", "flee_door")
    story = {"content_id": "episode-1", "title": "The Radio Mystery",
             "genre": "fiction", "kind": "microfiction",
             "story_beats": [
                 {"speech": f"Mara finds clue {i} in the abandoned observatory.",
                  "visual": "signal", "story_beat": "reveal",
                  "story_human_actor": "mara", "story_human_action": actions[i-1],
                  "headline": f"Beat {i}"} for i in range(1, 5)]}
    scenes = [{"start": i * 2., "duration": 2.,
               "visual": "signal", "story_environment": "observatory",
               "story_action": ("idle", "idle", "open", "pick")[i],
               "story_human_actor": "mara",
               "story_human_action": actions[i]} for i in range(4)]
    video = root / "episode.mp4"
    sheet = root / "sheet.jpg"
    video.write_bytes(b"test-encoded-mp4-bytes")
    sheet.write_bytes(b"test-contact-sheet-bytes")
    receipt = {"content_id": "episode-1", "shot_count": 4,
               "shots": [{"status": "composited"} for _ in range(4)],
               "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest()}
    # Tests must use REAL portrait PNGs, not renamed arbitrary byte strings.
    out = BytesIO()
    Image.new("RGB", (1080, 1920), (12, 42, 76)).save(out, format="PNG")
    png = out.getvalue()
    for i in range(1, 5):
        for name in (f"decoded-beat-{i:02d}.png",
                     f"temporal-beat-{i:02d}-early.png",
                     f"temporal-beat-{i:02d}-late.png"):
            (root / name).write_bytes(png)
    return story, {"genre": "fiction", "scenes": scenes}, receipt, video, sheet


class FictionEpisodeReviewPacketTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.story, self.report, self.receipt, self.video, self.sheet = fixture(self.root)
        self.dest = self.root / "visual-review-packet.json"

    def create(self):
        return create_episode_packet(self.story, self.report, self.receipt,
                                     video_path=self.video, sheet_path=self.sheet,
                                     frames_dir=self.root, output_path=self.dest)

    def test_exact_video_and_real_frames_remain_unapproved(self):
        result = self.create()
        packet = json.loads(self.dest.read_text())
        index = json.loads((self.root / "review-frame-index.json").read_text())
        self.assertEqual(result["review_status"], "pending_independent_visual_inspection")
        self.assertEqual(packet["sample_alignment"], "planned_storybeat_midpoints")
        self.assertEqual(packet["source_mp4_sha256"], self.receipt["video_sha256"])
        self.assertEqual(packet["sample_times_seconds"], [1., 3., 5., 7.])
        self.assertEqual(len(index["scenes"]), 4)
        self.assertEqual([r["authored_human_action"] for r in packet["beats"]],
                         ["discover_radio", "trace_cable", "hear_warning", "flee_door"])
        self.assertEqual([r["planned_human_action"] for r in packet["beats"]],
                         ["discover_radio", "trace_cable", "hear_warning", "flee_door"])
        self.assertEqual([r["planned_action"] for r in packet["beats"]],
                         ["idle", "idle", "open", "pick"])
        self.assertTrue(all(r["human_action_metadata_status"] ==
                            "matched_in_metadata" for r in packet["beats"]))
        self.assertTrue(all(r["visual_prompt_provenance"] ==
                            "fallback_visual_label" for r in packet["beats"]))
        self.assertEqual(index["scenes"][1]["authored_human_action"], "trace_cable")
        self.assertEqual(index["scenes"][1]["generic_studio_action"], "idle")
        self.assertEqual(index["scenes"][1]["human_action_metadata_status"],
                         "matched_in_metadata")
        self.assertEqual(index["video_sha256"], self.receipt["video_sha256"])
        self.assertTrue(index["independent_full_video_review_required"])
        self.assertFalse(index["publication_approval"])
        self.assertFalse(index["publication_triggered"])
        self.assertEqual(index["semantic_quality"], "not_verified")
        self.assertTrue(all(row["narrated_action_visible"] == "not_verified"
                            for row in index["scenes"]))
        self.assertTrue(all(row["character_and_prop_fidelity"] == "not_verified"
                            for row in index["scenes"]))
        self.assertFalse(packet["publication_approval"])
        self.assertNotIn("signature", packet)
        self.assertEqual(index["scenes"][0]["actual_decoded_frames"]["midpoint"]["sha256"],
                         hashlib.sha256((self.root / "decoded-beat-01.png").read_bytes()).hexdigest())

    def test_video_tampering_fails_closed(self):
        self.video.write_bytes(b"tampered-encoded-mp4")
        with self.assertRaisesRegex(ValueError, "encoded_video_hash_mismatch"):
            self.create()
        self.assertFalse(self.dest.exists())

    def test_timing_and_identity_mismatch_cannot_be_described_as_aligned(self):
        self.report["scenes"][1]["duration"] = -2
        with self.assertRaises(ValueError):
            self.create()
        self.assertFalse(self.dest.exists())
        self.report["scenes"][1]["duration"] = 2.
        self.receipt["content_id"] = "different"
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            self.create()

    def test_absent_decoded_frame_never_finishes_evidence_index(self):
        (self.root / "temporal-beat-04-late.png").unlink()
        with self.assertRaisesRegex(ValueError, "missing_actual_decoded_frame"):
            self.create()
        self.assertFalse((self.root / "review-frame-index.json").exists())

    def test_corrupt_or_renamed_non_png_frame_is_rejected(self):
        frame = self.root / "temporal-beat-03-late.png"
        frame.write_bytes(b"not a real decoded png")
        with self.assertRaisesRegex(ValueError, "invalid_actual_decoded_png"):
            self.create()
        self.assertFalse(self.dest.exists())

    def test_wrong_dimensions_are_not_accepted_as_video_frames(self):
        frame = self.root / "temporal-beat-01-early.png"
        Image.new("RGB", (320, 480), "green").save(frame)
        with self.assertRaisesRegex(ValueError, "invalid_actual_decoded_png"):
            self.create()
        self.assertFalse(self.dest.exists())

    def test_metadata_disagreement_is_visible_not_auto_resolved(self):
        self.report["scenes"][1]["story_human_action"] = "idle"
        self.create()
        packet = json.loads(self.dest.read_text())
        mismatch = packet["beats"][1]
        self.assertEqual(mismatch["authored_human_action"], "trace_cable")
        self.assertEqual(mismatch["planned_human_action"], "idle")
        self.assertEqual(mismatch["human_action_metadata_status"], "mismatch")
        self.assertEqual(mismatch["narrated_action_visible"], "not_verified")
        self.assertFalse(packet["publication_approval"])

    def test_preexisting_frame_index_cannot_leave_partial_new_packet(self):
        index = self.root / "review-frame-index.json"
        index.write_text("DO NOT REPLACE")
        with self.assertRaisesRegex(ValueError, "frame_index_already_exists"):
            self.create()
        self.assertFalse(self.dest.exists())
        self.assertEqual(index.read_text(), "DO NOT REPLACE")

    def test_preexisting_packet_is_never_overwritten(self):
        self.dest.write_text("DO NOT REPLACE")
        with self.assertRaisesRegex(ValueError, "output_already_exists"):
            self.create()
        self.assertEqual(self.dest.read_text(), "DO NOT REPLACE")

    def test_workflow_uses_only_post_render_encoded_video_evidence(self):
        flow = (Path(__file__).resolve().parents[1] /
                ".github/workflows/astra-fiction-episode-render-audit.yml").read_text()
        decode = flow.index("      - name: Decode actual MP4 and build storyboard review sheet")
        packet = flow.index("      - name: Bind encoded episode to manual visual review packet")
        preserve = flow.index("      - name: Preserve full fiction episode, samples and receipts")
        self.assertLess(decode, packet)
        self.assertLess(packet, preserve)
        block = flow[packet:preserve]
        self.assertIn("python -m astra_v2.fiction_episode_review_packet", block)
        self.assertIn("visual-review-packet.json", block)
        self.assertIn("studio-report.json", block)
        self.assertNotIn("GEMINI_API_KEY", block)
        self.assertNotIn("youtube_upload", block)


if __name__ == "__main__":
    unittest.main()
