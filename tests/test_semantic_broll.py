import unittest

from semantic_broll import infer_visual_intent, plan_broll


class SemanticBrollTests(unittest.TestCase):
    def test_first_beat_prefers_fast_motion(self):
        item = infer_visual_intent({"speech": "Tokyo built a massive underground flood system"}, 0)
        self.assertEqual(item["motion"], "fast_push")
        self.assertIn("tokyo", item["keywords"])

    def test_comparison_maps_to_comparison_visual(self):
        item = infer_visual_intent({"speech": "This engine is bigger than the older machine"}, 1)
        self.assertEqual(item["visual_type"], "compare")

    def test_plan_is_renderer_neutral(self):
        plan = plan_broll({
            "content_id": "x",
            "story_beats": [
                {"speech": "A satellite circles Earth every ninety minutes"},
                {"speech": "The system sends a signal back to the ground"},
                {"speech": "That changes how operators react"},
            ],
        })
        self.assertEqual(len(plan["items"]), 3)
        self.assertIn("fallback", plan["items"][0])


if __name__ == "__main__":
    unittest.main()
