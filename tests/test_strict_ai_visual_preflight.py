import unittest
from astra_v2.strict_ai_visual_preflight import require_reviewed_story_art


class StrictVisualPreflightTests(unittest.TestCase):
    def test_default_is_unchanged(self):
        self.assertFalse(require_reviewed_story_art({"genre":"fiction"},environ={}))

    def test_strict_fiction_requires_reviewed_manifest(self):
        with self.assertRaisesRegex(ValueError,"reviewed_ai_visual_manifest_required"):
            require_reviewed_story_art({"genre":"fiction","content_id":"abc"},
                environ={"ASTRA_REQUIRE_REVIEWED_AI_VISUALS":"1"})

    def test_strict_fiction_accepts_manifest_for_downstream_validation(self):
        self.assertTrue(require_reviewed_story_art({
            "genre":"fiction","content_id":"abc","reviewed_art_manifest":"assets/reviewed.json"},
            environ={"ASTRA_REQUIRE_REVIEWED_AI_VISUALS":"1"}))

    def test_other_genres_not_affected(self):
        self.assertFalse(require_reviewed_story_art({"genre":"news"},
            environ={"ASTRA_REQUIRE_REVIEWED_AI_VISUALS":"1"}))


if __name__=="__main__":
    unittest.main()
