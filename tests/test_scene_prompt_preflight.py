import unittest

from astra_v2.scene_prompt_preflight import audit


class PromptPreflightTests(unittest.TestCase):
    def test_preflight_never_grants_approval_or_calls_provider(self):
        story = {"content_id": "scene-test", "title": "Test",
                 "visual_bible": {"characters": {"otter": "blue scarf"}},
                 "story_beats": [
                     {"speech": "Otter lifts a brass bell.",
                      "visual_prompt": "Otter visibly lifts the brass bell."},
                     {"speech": "Otter rings the brass bell."}]}
        result = audit({"rewrites": [
            {"status": "awaiting_independent_editorial_approval", "story": story}]})
        self.assertEqual(result["provider_calls"], 0)
        self.assertFalse(result["approval_granted"])
        self.assertFalse(result["production_ready"])
        self.assertEqual(result["stories"][0]["status"], "prompt_preflight_pass")
        self.assertEqual(result["stories"][0]["scene_count"], 2)
        self.assertTrue(all(x <= 2048 for x in result["stories"][0]["prompt_lengths"]))

    def test_oversized_prompts_fail_closed(self):
        story = {"content_id": "too-long",
                 "story_beats": [{"speech": "An action",
                                  "visual_prompt": "very long action " * 250}]}
        result = audit({"rewrites": [
            {"status": "awaiting_independent_editorial_approval", "story": story}]})
        self.assertEqual(result["stories"][0]["status"], "prompt_preflight_failed")
        self.assertFalse(result["stories"][0]["production_ready"])


if __name__ == "__main__":
    unittest.main()
