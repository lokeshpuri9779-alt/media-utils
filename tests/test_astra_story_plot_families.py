import unittest
from astra_v2.story_plot_families import PLOT_FAMILIES, choose_plot_family, plan_plot


class PlotFamilyTests(unittest.TestCase):
    def test_twelve_distinct_beat_structures(self):
        self.assertGreaterEqual(len(PLOT_FAMILIES), 12)
        self.assertEqual(len(set(PLOT_FAMILIES.values())), len(PLOT_FAMILIES))

    def test_deterministic_choice(self):
        self.assertEqual(choose_plot_family("test-01"), choose_plot_family("test-01"))

    def test_recent_family_excluded_when_possible(self):
        self.assertNotEqual(choose_plot_family("test-01", ["mystery"]), "mystery")

    def test_plan_requires_editorial_and_asset_review(self):
        plan = plan_plot("test-01", family="comedy")
        self.assertEqual(plan["beat_roles"][-1], "punchline")
        self.assertFalse(plan["editorial_approved"])
        self.assertIn("asset_validation", plan["requires"])


if __name__ == "__main__":
    unittest.main()
