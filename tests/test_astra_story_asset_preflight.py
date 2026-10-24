import unittest
from unittest.mock import patch
from astra_v2.story_asset_preflight import inspect_story_assets, prepare_story_candidates


class StoryAssetPreflightTests(unittest.TestCase):
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
        report = inspect_story_assets(story, "/unused")
        self.assertEqual(report["matched_shots"], 1)
        self.assertFalse(report["all_shots_matched"])
        self.assertFalse(report["approved_for_publication"])

    @patch("astra_v2.story_asset_preflight.select_assets", return_value=[])
    def test_no_asset_never_claims_ready(self, select):
        report = inspect_story_assets({"story_beats": [{"story_environment": "railway"}]}, "/unused")
        self.assertEqual(report["matched_shots"], 0)
        self.assertFalse(report["all_shots_matched"])


if __name__ == "__main__":
    unittest.main()
