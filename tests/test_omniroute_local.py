import unittest
from astra_v2.omniroute_local import catalog


class LocalOmniRouteTests(unittest.TestCase):
    def test_distinct_story_ids_and_rapid_cut_target(self):
        stories = catalog(max_candidates=30)
        self.assertGreaterEqual(len(stories), 20)
        self.assertEqual(len({x["content_id"] for x in stories}), len(stories))
        self.assertEqual(len({x["title"].casefold().strip() for x in stories}), len(stories))
        for s in stories:
            self.assertEqual(len(s["story_beats"]), 4)
            self.assertTrue(all(x["duration"] == 1.0 for x in s["story_beats"]))

    def test_exclusion_rotates_inventory(self):
        first = catalog(max_candidates=1)[0]
        second = catalog(excluded_ids={first["content_id"]}, max_candidates=1)[0]
        self.assertNotEqual(first["content_id"], second["content_id"])


if __name__ == "__main__":
    unittest.main()
