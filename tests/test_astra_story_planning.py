import unittest
from astra_v2.story_planning import planning_issues, is_planned_story
from astra_v2.original_stories import catalog


class StoryPlanningTests(unittest.TestCase):
    def test_all_original_story_arcs_have_planned_progression(self):
        for story in catalog():
            with self.subTest(story=story["content_id"]):
                self.assertEqual(planning_issues(story), [])

    def test_reject_missing_payoff_and_repeated_beats(self):
        sample = dict(catalog()[0])
        sample["story_beats"] = [dict(b) for b in sample["story_beats"]]
        sample["story_beats"][-1]["story_beat"] = "build"
        self.assertFalse(is_planned_story(sample))
        sample["story_beats"][-1]["story_beat"] = "payoff"
        sample["story_beats"][-1]["speech"] = sample["story_beats"][0]["speech"]
        self.assertFalse(is_planned_story(sample))


if __name__ == "__main__":
    unittest.main()
