"""Regression tests for ASTRA's authored and opt-in draft story inventory."""
import unittest

from astra_v2.story_forge import PILLOW_DUO_PLOTS, PLOTS, REWRITTEN_PLOTS, NEW_AUTHORED_PLOTS, EDITORIAL_OCT2026_PLOTS, CROSSGENRE_DIRECTED_24, AUTHORED_REPLENISHMENT_OCT2026, AUTHORED_BATCH_341, AUTHORED_BATCH_364, AUTHORED_BATCH_407, AUTHORED_BATCH_420, AUTHORED_BATCH_421, AUTHORED_BATCH_422, AUTHORED_BATCH_423, AUTHORED_BATCH_424, AUTHORED_BATCH_473, DRAFT_CAUSAL_ARCS, DRAFT_PROBLEMS, catalog, draft_catalog, editorial_screen, plot_fingerprint
from astra_v2.publication_quality import publication_rejection


class StoryInventoryTests(unittest.TestCase):
    def test_authored_inventory_has_distinct_ids(self):
        self.assertEqual(len(PLOTS), 24)
        self.assertEqual(len(REWRITTEN_PLOTS), 55)
        records = catalog(limit=2000)
        self.assertEqual(len(records), len(PILLOW_DUO_PLOTS) + len(PLOTS) + len(REWRITTEN_PLOTS) + len(NEW_AUTHORED_PLOTS) + len(EDITORIAL_OCT2026_PLOTS) + len(CROSSGENRE_DIRECTED_24) + len(AUTHORED_REPLENISHMENT_OCT2026) + len(AUTHORED_BATCH_341) + len(AUTHORED_BATCH_364) + len(AUTHORED_BATCH_407) + len(AUTHORED_BATCH_420) + len(AUTHORED_BATCH_421) + len(AUTHORED_BATCH_422) + len(AUTHORED_BATCH_423) + len(AUTHORED_BATCH_424) + len(AUTHORED_BATCH_473))
        self.assertEqual(len({x["content_id"] for x in records}), len(records))
        self.assertTrue(all(x["production_ready"] for x in records))

    def test_new_replenishment_batch_is_structurally_valid(self):
        self.assertEqual(len(AUTHORED_BATCH_420), 12)
        self.assertEqual(len({row[0] for row in AUTHORED_BATCH_420}), 12)
        self.assertEqual(len({row[1].casefold() for row in AUTHORED_BATCH_420}), 12)
        for key, title, genre, beats in AUTHORED_BATCH_420:
            with self.subTest(story=key):
                self.assertEqual(len(beats), 4)
                self.assertTrue(title.strip() and genre.strip())
                self.assertTrue(all(len(beat) == 4 for beat in beats))
                self.assertTrue(all(len(beat[1].split()) >= 9 for beat in beats))

    def test_batch_421_structure(self):
        self.assertEqual(len(AUTHORED_BATCH_421), 8)
        self.assertEqual(len({x[0] for x in AUTHORED_BATCH_421}), 8)
        for key, title, genre, beats in AUTHORED_BATCH_421:
            self.assertEqual(len(beats), 4)
            self.assertTrue(all(len(beat[1].split()) >= 9 for beat in beats))

    def test_rewritten_story_editorial_structure(self):
        self.assertEqual(len(REWRITTEN_PLOTS), 55)
        keys = [story[0] for story in REWRITTEN_PLOTS]
        titles = [story[1].casefold() for story in REWRITTEN_PLOTS]
        fingerprints = [plot_fingerprint(story[3]) for story in REWRITTEN_PLOTS]
        self.assertEqual(len(set(keys)), 55)
        self.assertEqual(len(set(titles)), 55)
        self.assertEqual(len(set(fingerprints)), 55)
        for key, title, genre, beats in REWRITTEN_PLOTS:
            with self.subTest(story=key):
                self.assertEqual(len(beats), 4)
                self.assertTrue(title.strip() and genre.strip())
                self.assertTrue(all(len(beat) == 4 for beat in beats))
                self.assertTrue(all(all(isinstance(part, str) and part.strip() for part in beat) for beat in beats))
                self.assertTrue(all(len(beat[1].split()) >= 9 for beat in beats))
                self.assertEqual(len({beat[1].casefold() for beat in beats}), 4)

    def test_default_catalog_exposes_full_authored_inventory(self):
        records = catalog()
        self.assertEqual(len(records), len(PILLOW_DUO_PLOTS) + len(PLOTS) + len(REWRITTEN_PLOTS) + len(NEW_AUTHORED_PLOTS) + len(EDITORIAL_OCT2026_PLOTS) + len(CROSSGENRE_DIRECTED_24) + len(AUTHORED_REPLENISHMENT_OCT2026) + len(AUTHORED_BATCH_341) + len(AUTHORED_BATCH_364) + len(AUTHORED_BATCH_407) + len(AUTHORED_BATCH_420) + len(AUTHORED_BATCH_421) + len(AUTHORED_BATCH_422) + len(AUTHORED_BATCH_423) + len(AUTHORED_BATCH_424) + len(AUTHORED_BATCH_473))
        self.assertTrue(all(item["kind"] == "authored_causal_story" for item in records))

    def test_batch_473_structure_and_uniqueness(self):
        self.assertEqual(len(AUTHORED_BATCH_473), 6)
        self.assertEqual(len({row[0] for row in AUTHORED_BATCH_473}), 6)
        self.assertEqual(len({row[1].casefold() for row in AUTHORED_BATCH_473}), 6)
        for key, title, genre, beats in AUTHORED_BATCH_473:
            with self.subTest(story=key):
                self.assertEqual(len(beats), 4)
                self.assertTrue(title.strip() and genre.strip())
                self.assertTrue(all(len(beat) == 4 for beat in beats))
                self.assertTrue(all(len(beat[1].split()) >= 9 for beat in beats))
                self.assertEqual(len({beat[1].casefold() for beat in beats}), 4)

    def test_draft_inventory_count_and_unique_titles(self):
        drafts = draft_catalog()
        self.assertEqual(len(drafts), 996)
        self.assertEqual(len({x[0] for x in drafts}), 996)
        self.assertEqual(len({x[1] for x in drafts}), 996)
        self.assertEqual(len({plot_fingerprint(x[3]) for x in drafts}), 996)

    def test_all_draft_causal_arcs_are_problem_specific(self):
        self.assertEqual(len(DRAFT_CAUSAL_ARCS), 20)
        self.assertEqual({row[0] for row in DRAFT_PROBLEMS}, set(DRAFT_CAUSAL_ARCS))
        self.assertTrue(all(len(arcs) == 5 for arcs in DRAFT_CAUSAL_ARCS.values()))
        self.assertEqual(len({pair for arcs in DRAFT_CAUSAL_ARCS.values()
                              for pair in arcs}), 100)
        for key, title, genre, beats in draft_catalog():
            with self.subTest(key=key):
                self.assertEqual(len(beats), 4)
                self.assertTrue(all(len(beat[1].split()) >= 9 for beat in beats))

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

    def test_publication_gate_blocks_unreviewed_drafts(self):
        drafts = [item for item in catalog(limit=2000, include_drafts=True)
                  if item["kind"] == "unreviewed_causal_draft"]
        self.assertEqual(len(drafts), 996)
        self.assertTrue(all(publication_rejection(item) == "unreviewed_causal_draft"
                            for item in drafts))
        ready = [item for item in catalog(limit=2000) if item["production_ready"]]
        self.assertTrue(all(publication_rejection(item) is None for item in ready))

    def test_history_excludes_draft(self):
        first = catalog(limit=2000, include_drafts=True)[-1]
        later = catalog(limit=2000, include_drafts=True, history=[first])
        self.assertNotIn(first["content_id"], {x["content_id"] for x in later})


if __name__ == "__main__":
    unittest.main()
