import unittest
from astra_v2.story_pacing import review_pacing


class StoryPacingTests(unittest.TestCase):
    def test_thin_four_beat_story_gets_specific_development_notes(self):
        story = {"story_beats": [
            {"speech": "A fox wanted to find a key."},
            {"speech": "The door was locked."},
            {"speech": "A clue appeared."},
            {"speech": "The fox found the key."},
        ]}
        result = review_pacing(story)
        self.assertEqual(result["status"], "needs_story_development")
        self.assertIn("expand_into_more_visual_story_turns", result["issues"])
        self.assertIn("add_story_content_not_filler", result["issues"])
        self.assertFalse(result["approval"])

    def test_suspenseful_longer_story_reports_signals_without_approval(self):
        beats = [
            "Why was the lighthouse flashing when nobody was inside? The final ferry was due in sixty seconds.",
            "Mira ran up the stairs, but the locked door was warm and something moved behind it.",
            "A wet footprint appeared on the dry floor. She heard three knocks from above.",
            "The radio crackled: the missing keeper had warned them never to trust the light.",
            "But the signal was coming from the sea, not the tower. The map showed a second lamp.",
            "Mira cut the power just before the countdown ended. The real lighthouse answered from the cliff above the dark water.",
        ]
        story = {"story_beats": [{"speech": s} for s in beats]}
        result = review_pacing(story)
        self.assertEqual(result["beat_count"], 6)
        self.assertGreater(result["word_count"], 95)
        self.assertGreater(result["tension_signals"]["uncertainty"], 0)
        self.assertGreater(result["tension_signals"]["reversal"], 0)
        self.assertFalse(result["approval"])

    def test_invalid_format_rejected(self):
        with self.assertRaises(ValueError):
            review_pacing({}, "reel")


if __name__ == "__main__":
    unittest.main()
