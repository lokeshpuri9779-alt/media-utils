import unittest

from astra_v2.caption_short_pipeline import narration_from_candidate


class CaptionShortPipelineTests(unittest.TestCase):
    def candidate(self):
        roles = ["hook", "stakes", "attempt", "setback", "discovery", "climax", "payoff"]
        return {
            "approved": False,
            "production_ready": False,
            "published": False,
            "question": "Would you have noticed the hidden clue?",
            "performance_scenes": [
                {"role": role, "speech": f"Spoken line for {role}."}
                for role in roles
            ],
        }

    def test_extracts_seven_scene_narration_in_order(self):
        self.assertEqual(
            narration_from_candidate(self.candidate()),
            " ".join(f"Spoken line for {role}." for role in
                     ["hook", "stakes", "attempt", "setback", "discovery", "climax", "payoff"]),
        )

    def test_rejects_missing_engagement_question(self):
        candidate = self.candidate()
        candidate["question"] = ""
        with self.assertRaisesRegex(ValueError, "engagement question"):
            narration_from_candidate(candidate)

    def test_rejects_wrong_scene_count(self):
        candidate = self.candidate()
        candidate["performance_scenes"].pop()
        with self.assertRaisesRegex(ValueError, "exactly seven"):
            narration_from_candidate(candidate)

    def test_rejects_missing_speech(self):
        candidate = self.candidate()
        candidate["performance_scenes"][2]["speech"] = ""
        with self.assertRaisesRegex(ValueError, "no narration"):
            narration_from_candidate(candidate)

    def test_rejects_approved_candidate(self):
        candidate = self.candidate()
        candidate["approved"] = True
        with self.assertRaisesRegex(ValueError, "review-only"):
            narration_from_candidate(candidate)


if __name__ == "__main__":
    unittest.main()
