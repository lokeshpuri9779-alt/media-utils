import unittest
from quality_lab import director_input_from_render
from creative_director import evaluate

class MediaQAFailClosedTests(unittest.TestCase):
    def test_explicit_media_failure_without_reasons_blocks(self):
        story = {"genre": "suspense", "hook": "What was behind the door?"}
        render = {"duration": 57, "scenes": [
            {"duration": 19, "speech": "One", "start": 0},
            {"duration": 19, "speech": "Two", "start": 19},
            {"duration": 19, "speech": "Three", "start": 38}],
            "creative_quality": {"score": 95}, "audio": {"peak_dbfs": -3}}
        qa = {"available": True, "pass": False, "audio_score": 95,
              "caption_score": 95, "hard_failures": []}
        director_input = director_input_from_render(story, render, media_qa=qa)
        self.assertIn("post_render_media_validation_failed", director_input["hard_failures"])
        self.assertFalse(evaluate(director_input)["publish_allowed"])

if __name__ == "__main__":
    unittest.main()
