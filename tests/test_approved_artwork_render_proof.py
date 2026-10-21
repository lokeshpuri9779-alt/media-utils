import tempfile
import unittest
from pathlib import Path
from astra.approved_artwork_render_proof import prepare_fixture
from astra.asset_library import load_assets


class ApprovedArtworkProofTests(unittest.TestCase):
    def test_fixture_is_isolated_and_binds_exact_scenes(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest, story = prepare_fixture(temp, "astra/fixtures/artwork_storyboard_review.json")
            approved = load_assets(manifest)
            self.assertEqual(len(approved), 4)
            self.assertEqual(len(story["story_beats"]), 4)
            self.assertTrue(all(x["artwork_manifest_path"] == str(manifest) for x in story["story_beats"]))
            self.assertTrue(all(x["review_scope"] == "isolated_ci_fixture_only" for x in approved))
            self.assertFalse(story["production_ready"])
            self.assertFalse(Path("art/manifest.json").read_text().find('"status": "approved"') >= 0)


if __name__ == "__main__":
    unittest.main()
