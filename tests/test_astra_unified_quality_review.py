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

    def test_sparse_longform_storyboard_is_flagged_diagnostically(self):
        story={"story_beats":[
            {"story_action":"pick","story_environment":"forest","duration":12},
            {"story_action":"carry","story_environment":"village","duration":13},
            {"story_action":"repair","story_environment":"harbor","duration":13},
            {"story_action":"open","story_environment":"cave","duration":13},
        ]}
        report=review_storyboard(story)
        self.assertIn("sparse_longform_visual_beats",report["findings"])
        self.assertEqual(report["visual_beats"],4)
        self.assertEqual(report["duration_seconds"],51)
        self.assertEqual(report["publication_decision"],"unchanged")
        self.assertEqual(report["enforcement"],"diagnostic_only")

    def test_twenty_authored_beats_clear_longform_density_diagnostic(self):
        story={"story_beats":[
            {"story_action":"walk","story_environment":f"scene-{i}","duration":3}
            for i in range(20)
        ]}
        report=review_storyboard(story)
        self.assertNotIn("sparse_longform_visual_beats",report["findings"])

    def test_short_video_is_not_subject_to_longform_beat_target(self):
        story={"story_beats":[
            {"story_action":"walk","story_environment":"forest","duration":10},
            {"story_action":"run","story_environment":"forest","duration":10},
        ]}
        self.assertNotIn("sparse_longform_visual_beats",
                         review_storyboard(story)["findings"])

    def test_malformed_storyboard(self):
        with self.assertRaises(ValueError):
            review_storyboard({"story_beats":"invalid"})

if __name__=="__main__": unittest.main()
