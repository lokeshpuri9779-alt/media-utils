"""Review-queue artifacts are diagnostic, never approved visual evidence."""
import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.artwork_gap_queue import build_repair_queue, save_repair_queue


class ArtworkGapQueueTests(unittest.TestCase):
    def test_bounded_story_priority_and_unapproved_provenance(self):
        items = [
            {"content_id": "story-b", "shot_count": 4, "missing_shots": [
                {"shot": 1, "reason": "scene_unresolved",
                 "authored_context": {"source_beat_found": True, "authored_fields": {
                     "visual_prompt": "An unfamiliar grassland with a wooden sign." * 20,
                     "speech": "The marker fell.", "untrusted": "ignored"}}}]},
            {"content_id": "story-a", "shot_count": 4, "missing_shots": [
                {"shot": 2, "reason": "no_matching_background", "scene": "railway",
                 "authored_context": {"source_beat_found": True, "authored_fields": {
                     "story_environment": "railway", "speech": "The train arrives."}}},
                {"shot": 3, "reason": "scene_unresolved",
                 "authored_context": {"source_beat_found": False}}]},
        ]
        result = build_repair_queue({"background_review_gaps": items}, lane=2)
        self.assertEqual(result["story_count"], 2)
        self.assertEqual(result["missing_shot_count"], 3)
        self.assertEqual(result["scene_unresolved_count"], 2)
        self.assertEqual(result["no_matching_background_count"], 1)
        self.assertEqual([i["content_id"] for i in result["items"]], ["story-a", "story-b"])
        self.assertEqual(result["items"][0]["missing_shots"][0]["scene"], "railway")
        excerpts = result["items"][1]["missing_shots"][0]["authored_context"]["authored_fields"]
        self.assertEqual(len(excerpts["visual_prompt"]), 160)
        self.assertNotIn("untrusted", excerpts)
        self.assertFalse(result["publication_approval"])
        self.assertEqual(result["semantic_quality"], "not_verified")
        self.assertFalse(result["automatic_scene_substitution"])
        self.assertFalse(result["automatic_image_generation"])

    def test_preserves_bounded_story_art_direction_for_later_review(self):
        story_context = {
            "content_id": "story-a", "title": "The Bell Tower",
            "visual_bible": {"fox": "russet fur, white chest", "owl": ["amber eyes"]},
            "story_cast": [{"name": "Fox", "appearance": "russet fur"}],
            "story_beats": [{"speech": "The fox enters the tower."}],
        }
        result = build_repair_queue({"background_review_gaps": [{
            "content_id": "story-a", "shot_count": 1, "story_context": story_context,
            "missing_shots": [{"shot": 1, "reason": "scene_unresolved"}],
        }]}, lane=0)
        self.assertEqual(result["items"][0]["story_context"], story_context)
        self.assertFalse(result["publication_approval"])
        self.assertEqual(result["semantic_quality"], "not_verified")

    def test_no_gaps_create_no_artifact(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(save_repair_queue({"background_review_gaps": []},
                                                 lane=1, directory=root))
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_writes_lane_report_atomically_and_without_publication(self):
        selection = {"background_review_gaps": [
            {"content_id": "candidate-7", "shot_count": 1,
             "missing_shots": [{"shot": 1, "reason": "scene_unresolved",
                               "authored_context": {"source_beat_found": True,
                                                   "authored_fields": {"visual": "grassland"}}}]},
        ]}
        with tempfile.TemporaryDirectory() as root:
            result = save_repair_queue(selection, lane=3, directory=root)
            output = Path(result["path"])
            self.assertEqual(output.name, "lane-3.json")
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["items"][0]["missing_shots"][0]["authored_context"]
                             ["authored_fields"]["visual"], "grassland")
            self.assertEqual(result["story_count"], 1)
            self.assertFalse(report["publication_approval"])
            self.assertFalse((Path(root) / ".lane-3.json.tmp").exists())

    def test_invalid_shot_numbers_and_lane_never_approve(self):
        with self.assertRaises(ValueError):
            build_repair_queue({"background_review_gaps": [{"content_id": "a"}]}, lane=True)
        invalid = {"background_review_gaps": [
            {"content_id": "s", "missing_shots": [
                {"shot": False, "reason": "scene_unresolved"}]}]}
        self.assertIsNone(build_repair_queue(invalid, lane=0))
        self.assertIsNone(build_repair_queue({}, lane=0))


    def test_preserves_renderer_issue_scene_identity_and_issue_count(self):
        selection = {"background_review_gaps": [{
            "content_id": "renderer-rejected-story",
            "shot_count": 3,
            "story_context": {"title": "The Signal Bell"},
            "missing_shots": [{
                "shot": 2,
                "scene_id": "signal-bell-scene-2",
                "reason": "scene_unresolved",
                "renderer_issue": "signal_graphic_does_not_depict_narrated_event",
                "authored_context": {
                    "source_beat_found": True,
                    "authored_fields": {"speech": "The bell rings twice."},
                },
            }],
        }]}
        result = build_repair_queue(selection, lane=1)
        self.assertEqual(result["renderer_issue_count"], 1)
        row = result["items"][0]["missing_shots"][0]
        self.assertEqual(row["scene_id"], "signal-bell-scene-2")
        self.assertEqual(row["renderer_issue"],
                         "signal_graphic_does_not_depict_narrated_event")
        self.assertFalse(result["publication_approval"])
        self.assertEqual(result["semantic_quality"], "not_verified")

    def test_archive_hook_and_upload_stay_optional_and_separate(self):
        root = Path(__file__).resolve().parents[1]
        creative = (root / "astra_v2/creative.py").read_text(encoding="utf-8")
        preload = (root / ".github/workflows/astra-v2-preload.yml").read_text(encoding="utf-8")
        self.assertIn('ASTRA_ARTWORK_GAP_REPORT", "0") != "1"', creative)
        self.assertEqual(creative.count("archive_background_review_gaps(selection)"), 3)
        self.assertIn("ASTRA_ARTWORK_GAP_REPORT: '1'", preload)
        self.assertIn("astra-artwork-gaps-", preload)
        self.assertIn("if-no-files-found: ignore", preload)
        self.assertIn("if: steps.render.outputs.content_id != ''", preload)
        self.assertIn("fiction_compositor_coverage_rejection(story, rendered)", creative)


if __name__ == "__main__":
    unittest.main()
