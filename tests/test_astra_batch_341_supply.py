"""Regression: newly authored Shorts reach the real approval-filtered forge pool."""
import unittest

from astra_v2.authored_batch_341 import PLOTS as NEW_PLOTS
from astra_v2.story_forge import catalog
from astra_v2.production_story_gate import approved_authored_candidates, candidate_issues


class NewAuthoredSupplyTests(unittest.TestCase):
    def test_new_authored_stories_reach_reviewed_candidate_pool(self):
        all_stories = catalog(limit=100000)
        by_title = {story["title"]: story for story in all_stories}
        expected_titles = {row[1] for row in NEW_PLOTS}
        self.assertEqual(len(expected_titles), 4)
        self.assertTrue(expected_titles.issubset(by_title))
        new_stories = [by_title[title] for title in sorted(expected_titles)]
        for story in new_stories:
            with self.subTest(title=story["title"]):
                self.assertEqual(story["kind"], "authored_causal_story")
                self.assertIs(story["production_ready"], True)
                self.assertEqual(candidate_issues(story, ()), [])
        approved = approved_authored_candidates(new_stories)
        self.assertEqual(len(approved), len(new_stories))

    def test_used_story_is_not_reapproved(self):
        story = next(s for s in catalog(limit=100000) if s["title"] == NEW_PLOTS[0][1])
        self.assertTrue(candidate_issues(story, [story]))


if __name__ == "__main__":
    unittest.main()
