import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from astra_v2.story_asset_preflight import inspect_story_assets, prepare_story_candidates


class StoryAssetPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "art").mkdir()
        (self.root / "art" / "manifest.json").write_text('{"assets": []}', encoding="utf-8")

    def test_candidate_to_story_with_explicit_scene(self):
        stories = list(prepare_story_candidates("seed", 2,
            settings=["railway"], protagonists=["fox"], goals=["find parcel"],
            conflicts=["storm"], twists=["secret message"]))
        self.assertEqual(len(stories), 2)
        for story in stories:
            self.assertTrue(all(b["story_environment"] == "railway"
                                for b in story["story_beats"]))
            self.assertFalse(story["editorial_approved"])

    @patch("astra_v2.story_asset_preflight.select_assets")
    def test_asset_preflight_records_missing_shots(self, select):
        select.side_effect = [[{"id": "art-01"}], []]
        story = {"content_id": "test", "story_beats": [
            {"story_environment": "railway"}, {"story_environment": "forest"}]}
        report = inspect_story_assets(story, self.root)
        self.assertEqual(report["matched_shots"], 1)
        self.assertFalse(report["all_shots_matched"])
        self.assertEqual(report["shots"][1]["reason"], "no_matching_background")
        self.assertEqual(select.call_args_list[0].kwargs["tags"], ("railway",))
        self.assertFalse(report["approved_for_publication"])

    @patch("astra_v2.story_asset_preflight.select_assets", return_value=[])
    def test_no_asset_never_claims_ready(self, select):
        report = inspect_story_assets({"story_beats": [
            {"story_environment": "railway"}]}, self.root)
        self.assertEqual(report["matched_shots"], 0)
        self.assertEqual(report["shots"][0]["reason"], "no_matching_background")
        self.assertFalse(report["all_shots_matched"])

    @patch("astra_v2.story_asset_preflight.select_assets", return_value=[{"id": "forest-001"}])
    def test_source_visual_scene_recognized_with_real_compositor_taxonomy(self, select):
        original = {"story_beats": [
            {"visual": "Fox crosses through the dense forest."}]}
        report = inspect_story_assets(original, self.root)
        self.assertEqual(report["matched_shots"], 1)
        self.assertEqual(report["shots"][0]["scene"], "forest")
        self.assertEqual(report["shots"][0]["scene_source"], "visual")
        self.assertEqual(select.call_args.kwargs["tags"], ("forest",))
        self.assertNotIn("story_environment", original["story_beats"][0])
        self.assertEqual(report["semantic_quality"], "not_verified")
        self.assertFalse(report["approved_for_publication"])

    @patch("astra_v2.story_asset_preflight.select_assets", return_value=[{"id": "railway-001"}])
    def test_story_level_environment_is_explicit_fallback(self, select):
        story = {"story_environment": "railway",
                 "story_beats": [{"speech": "The fox looked outside."}]}
        report = inspect_story_assets(story, self.root)
        self.assertEqual(report["shots"][0]["scene"], "railway")
        self.assertEqual(report["shots"][0]["scene_source"], "story_environment")
        self.assertNotIn("story_environment", story["story_beats"][0])

    @patch("astra_v2.story_asset_preflight.select_assets", return_value=[{"id": "forest-001"}])
    def test_unknown_scene_does_not_select_unrelated_background(self, select):
        report = inspect_story_assets({"story_beats": [
            {"visual_intent": "shimmering dreamworld and a flying teacup"}]}, self.root)
        self.assertEqual(report["matched_shots"], 0)
        self.assertEqual(report["shots"][0]["reason"], "scene_unresolved")
        select.assert_not_called()

    @patch("astra_v2.story_asset_preflight.select_assets")
    def test_missing_pack_fails_closed_without_selector(self, select):
        (self.root / "art" / "manifest.json").unlink()
        report = inspect_story_assets({"story_beats": [
            {"story_environment": "forest"}]}, self.root)
        self.assertEqual(report["shots"][0]["reason"], "verified_asset_pack_missing")
        self.assertFalse(report["all_shots_matched"])
        select.assert_not_called()

    @patch("astra_v2.story_asset_preflight.select_assets", return_value=[{"id": "art-01"}])
    def test_repeated_scene_is_cached_and_respects_orientation(self, select):
        report = inspect_story_assets({"story_beats": [
            {"story_environment": "forest"}, {"visual": "forest trail"}]},
            self.root, video_format="long")
        self.assertEqual(report["matched_shots"], 2)
        self.assertEqual(report["shots"][0]["candidate_asset_ids"],
                         report["shots"][1]["candidate_asset_ids"])
        select.assert_called_once()
        self.assertEqual(select.call_args.kwargs["video_format"], "long")
        self.assertFalse(report["approved_for_publication"])

    def test_malformed_story_and_empty_beats_cannot_claim_coverage(self):
        self.assertFalse(inspect_story_assets({"story_beats": []}, self.root)["all_shots_matched"])
        with self.assertRaises(ValueError):
            inspect_story_assets({"story_beats": "not a list"}, self.root)
        with self.assertRaises(ValueError):
            inspect_story_assets({"story_beats": [None]}, self.root)


if __name__ == "__main__":
    unittest.main()
