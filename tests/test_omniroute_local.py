import unittest
from astra_v2.omniroute_local import catalog


class LocalOmniRouteTests(unittest.TestCase):
    def test_series_starts_with_first_episode_only(self):
        stories = catalog(max_candidates=30)
        self.assertEqual(len(stories), 1)
        first = stories[0]
        self.assertEqual(first["episode"], 1)
        self.assertEqual(first["season"], 1)
        self.assertEqual(first["previous_episode_id"], None)
        self.assertEqual(len(first["story_beats"]), 4)
        self.assertTrue(all(beat["duration"] == 1.0 for beat in first["story_beats"]))

    def test_series_advances_in_order(self):
        previous = catalog(max_candidates=1)[0]
        for expected_episode in range(2, 5):
            ids = {f"rayvan-season-01-episode-{i:02d}"
                   for i in range(1, expected_episode)}
            stories = catalog(excluded_ids=ids, max_candidates=30)
            self.assertEqual(len(stories), 1)
            current = stories[0]
            self.assertEqual(current["episode"], expected_episode)
            self.assertEqual(current["previous_episode_id"], previous["content_id"])
            self.assertNotEqual(current["content_id"], previous["content_id"])
            self.assertNotEqual(
                current["story_beats"][0]["speech"],
                previous["story_beats"][0]["speech"])
            previous = current

    def test_cannot_skip_an_episode(self):
        stories = catalog(excluded_ids={"rayvan-season-01-episode-02"},
                          max_candidates=30)
        self.assertEqual([story["episode"] for story in stories], [1])

    def test_no_replay_after_season_is_exhausted(self):
        all_ids = {f"rayvan-season-01-episode-{i:02d}" for i in range(1, 5)}
        self.assertEqual(catalog(excluded_ids=all_ids), [])


if __name__ == "__main__":
    unittest.main()
