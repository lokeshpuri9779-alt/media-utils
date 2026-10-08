import unittest
from astra_v2.creative import narration_word_count, script_duration_preflight

class ScriptDurationContractTests(unittest.TestCase):
    def story(self, count):
        return {"content_id": "duration-test", "story_beats": [
            {"speech": "word " * count, "headline": "NOT SPOKEN"}]}

    def test_short_script_rejected_before_render(self):
        self.assertFalse(script_duration_preflight(self.story(50)))

    def test_reasonable_script_accepted(self):
        self.assertTrue(script_duration_preflight(self.story(130)))

    def test_excessive_script_rejected(self):
        self.assertFalse(script_duration_preflight(self.story(210)))

    def test_counts_only_narration(self):
        self.assertEqual(narration_word_count(self.story(4)), 4)

if __name__ == "__main__":
    unittest.main()
