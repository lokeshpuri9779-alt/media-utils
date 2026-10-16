import unittest
from astra_v2.unified_quality_review import review_storyboard

class UnifiedQualityTests(unittest.TestCase):
    def test_detects_static_repetitive_storyboard(self):
        story={"story_beats":[{"story_action":"idle","story_environment":"forest"} for _ in range(4)]}
        report=review_storyboard(story)
        self.assertIn("limited_scene_variety",report["findings"])
        self.assertIn("limited_action_variety",report["findings"])
        self.assertEqual(report["publication_decision"],"unchanged")

    def test_varied_actions_and_scenes(self):
        story={"story_beats":[{"story_action":"pick","story_environment":"village"},
                              {"story_action":"carry","story_environment":"harbor"},
                              {"story_action":"repair","story_environment":"library"}]}
        self.assertEqual(review_storyboard(story)["findings"],[])

    def test_malformed_storyboard(self):
        with self.assertRaises(ValueError):
            review_storyboard({"story_beats":"invalid"})

if __name__=="__main__": unittest.main()
