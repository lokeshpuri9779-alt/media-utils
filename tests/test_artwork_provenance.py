import unittest
from astra.artwork_provenance import audit


class ArtworkProvenanceTests(unittest.TestCase):
    def test_procedural_fallback_is_not_mislabeled_as_requested_artwork(self):
        data = audit("astra/fixtures/artwork_storyboard_review.json", {
            "scenes": [{"resolved_asset": {"provider": "astra-studio", "status": "ready"}}
                       for _ in range(4)]})
        self.assertFalse(data["requested_backgrounds_verified"])
        self.assertEqual(len(data["scenes"]), 4)
        self.assertTrue(data["review_only"])

    def test_only_exact_approved_ids_count(self):
        from json import loads
        from pathlib import Path
        requested = loads(Path("astra/fixtures/artwork_storyboard_review.json").read_text())["scenes"]
        data = audit("astra/fixtures/artwork_storyboard_review.json", {
            "scenes": [{"resolved_asset": {"id": x["background"], "status": "approved"}}
                       for x in requested]})
        self.assertTrue(data["requested_backgrounds_verified"])


if __name__ == "__main__":
    unittest.main()
