"""Regression tests for ASTRA's authored and opt-in draft story inventory."""
import unittest

from astra_v2.story_forge import PLOTS, REWRITTEN_PLOTS, catalog, draft_catalog, editorial_screen, plot_fingerprint


class StoryInventoryTests(unittest.TestCase):
    def test_authored_inventory_has_distinct_ids(self):
        self.assertEqual(len(PLOTS), 24)
        self.assertEqual(len(REWRITTEN_PLOTS), 10)
        self.assertEqual(len(records), 34)
        records = catalog(limit=2000)
        self.assertEqual(len({x["content_id"] for x in records}), len(records))
        self.assertTrue(all(x["production_ready"] for x in records))

    def test_draft_inventory_count_and_unique_titles(self):
        drafts = draft_catalog()
        self.assertEqual(len(drafts), 996)
        self.assertEqual(len({x[0] for x in drafts}), 996)
        self.assertEqual(len({x[1] for x in drafts}), 996)
        self.assertEqual(len({plot_fingerprint(x[3]) for x in drafts}), 996)

    def test_drafts_are_not_publication_ready(self):
        records = catalog(limit=2000, include_drafts=True)
        drafts = [x for x in records if x["kind"] == "unreviewed_causal_draft"]
        self.assertEqual(len(drafts), 996)
        self.assertTrue(all(not x["production_ready"] for x in drafts))
        self.assertEqual(len({x["content_id"] for x in records}), len(records))

    def test_editorial_screen_requires_rewrite(self):
        screened = editorial_screen()
        queue = screened["rewrite_queue"]
        rejected = screened["rejected"]
        self.assertEqual(len(queue), 55)
        self.assertEqual(len(rejected), 941)
        self.assertEqual(len({row[0] for row in queue}), len(queue))
        self.assertTrue(all(row[0].startswith("badger-") for row in queue))
        self.assertTrue(all(reason in ("causal_mismatch", "character_swap_duplicate") for _, reason in rejected))

    def test_history_excludes_draft(self):
        first = catalog(limit=2000, include_drafts=True)[-1]
        later = catalog(limit=2000, include_drafts=True, history=[first])
        self.assertNotIn(first["content_id"], {x["content_id"] for x in later})


if __name__ == "__main__":
    unittest.main()
