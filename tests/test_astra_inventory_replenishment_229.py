import unittest

from astra_v2.authored_replenishment_oct2026 import PLOTS
from astra_v2.story_forge import catalog
from astra_v2.story_planning import planning_issues


class InventoryReplenishmentTests(unittest.TestCase):
    def test_new_authored_plots_are_visible_under_default_catalog_limit(self):
        expected = {row[1] for row in PLOTS}
        available = {row["title"]: row for row in catalog()}
        self.assertTrue(expected.issubset(available), expected - set(available))
        for title in expected:
            story = available[title]
            self.assertTrue(story["production_ready"])
            self.assertEqual(story["kind"], "authored_causal_story")
            self.assertEqual(planning_issues(story), [])

    def test_new_stories_have_unique_titles_and_keys(self):
        self.assertEqual(len({row[0] for row in PLOTS}), len(PLOTS))
        self.assertEqual(len({row[1] for row in PLOTS}), len(PLOTS))


if __name__ == "__main__":
    unittest.main()
