"""Offline proof that decoded video evidence cannot grant semantic approval."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from astra_v2.fiction_episode_review_packet import create_episode_packet


def fixture(root):
    story = {"content_id": "episode-1", "title": "The Radio Mystery",
             "genre": "fiction", "kind": "microfiction",
             "story_beats": [
                 {"speech": f"Mara finds clue {i} in the abandoned observatory.",
                  "visual": "signal", "story_beat": "reveal",
                  "headline": f"Beat {i}"} for i in range(1, 5)]}
    scenes = [{"start": i * 2., "duration": 2.,
               "visual": "signal", "story_environment": "observatory",
               "story_human_action": "discover_radio"} for i in range(4)]
    video = root / "episode.mp4"
    sheet = root / "sheet.jpg"
    video.write_bytes(b"test-encoded-mp4-bytes")
    sheet.write_bytes(b"test-contact-sheet-bytes")
    receipt = {"content_id": "episode-1", "shot_count": 4,
               "shots": [{"status": "composited"} for _ in range(4)],
               "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest()}
    for i in range(1, 5):
        for name in (f"decoded-beat-{i:02d}.png",
                     f"temporal-beat-{i:02d}-early.png",
                     f"temporal-beat-{i:02d}-late.png"):
            (root / name).write_bytes(f"decoded-{name}".encode())
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
