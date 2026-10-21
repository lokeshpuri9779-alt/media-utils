import unittest
from astra_v2.automated_editorial_evidence import assess


class AutomatedEditorialEvidenceTests(unittest.TestCase):
    def test_unreviewed_candidate_never_becomes_approved(self):
        story = {"content_id": "draft-test", "title": "A Flooded Crossing",
                 "kind": "unreviewed_causal_draft", "production_ready": False,
                 "story_beats": [
                     {"story_beat": role, "speech": "The otter followed the strange signal and learned how to repair the crossing safely.", "visual": visual}
                     for role, visual in zip(("reveal", "build", "twist", "payoff"),
                                             ("bridge", "bell", "cable", "lantern"))]}
        result = assess(story)
        self.assertEqual(result["decision"], "not_approved")
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["publication_triggered"])
        self.assertEqual(len(result["story_sha256"]), 64)

    def test_invalid_story_fails_closed(self):
        with self.assertRaises(ValueError):
            assess(None)


if __name__ == "__main__":
    unittest.main()
