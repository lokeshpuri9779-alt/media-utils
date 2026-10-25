import unittest
from astra_v2.omniroute_local import catalog


class LocalOmniRouteTests(unittest.TestCase):
    def test_all_four_episodes_available_for_parallel_preload(self):
        stories = catalog(max_candidates=30)
        self.assertEqual([s["episode"] for s in stories], [1, 2, 3, 4])
        self.assertEqual(len({s["content_id"] for s in stories}), 4)
        self.assertTrue(all(len(s["story_beats"]) == 4 for s in stories))

    def test_season_one_pilot_visuals_match_narrated_objects(self):
        from astra_v2.directed_scene_contract import directed_scene_issue
        pilot = next(story for story in catalog() if story["episode"] == 1)
        self.assertEqual([beat["visual"] for beat in pilot["story_beats"]],
                         ["signal", "signal", "door", "door"])
        for number, beat in enumerate(pilot["story_beats"], 1):
            self.assertIsNone(directed_scene_issue({
                **beat, "story_title": pilot["title"],
            }), f"Episode 1 beat {number} has a mismatched visual")

    def test_exclusions_do_not_block_future_rendering(self):
        first_id = "rayvan-season-01-episode-01"
        stories = catalog(excluded_ids={first_id}, max_candidates=30)
        self.assertEqual([s["episode"] for s in stories], [2, 3, 4])
        self.assertEqual(stories[0]["previous_episode_id"], first_id)

    def test_can_render_later_episode_before_previous_publishes(self):
        stories = catalog(excluded_ids={"rayvan-season-01-episode-02"}, max_candidates=30)
        self.assertEqual([s["episode"] for s in stories], [1, 3, 4])

    def test_exhausted_season(self):
        ids = {f"rayvan-season-01-episode-{i:02d}" for i in range(1, 5)}
        self.assertEqual(catalog(excluded_ids=ids), [])


if __name__ == "__main__":
    unittest.main()
