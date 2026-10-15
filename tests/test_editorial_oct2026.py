import unittest
from astra_v2.editorial_batch_oct2026 import PLOTS
from astra_v2.pillow_duo_scene import scene_pair
from astra_v2.story_forge import catalog
from astra_v2.publication_quality import publication_rejection

class EditorialPilotTests(unittest.TestCase):
    def test_twenty_distinct_stories_have_four_authored_scenes(self):
        self.assertEqual(len(PLOTS),20)
        self.assertEqual(len({row[0] for row in PLOTS}),20)
        self.assertEqual(len({row[1] for row in PLOTS}),20)
        self.assertEqual(sum(len(row[3]) for row in PLOTS),80)
        for key,title,genre,scenes in PLOTS:
            with self.subTest(key=key):
                self.assertEqual(len(scene_pair({"speech":title})),2)
                self.assertEqual(len(scenes),4)
                self.assertTrue(all(len(scene)==4 for scene in scenes))
                self.assertTrue(all(scene[2]=="story" for scene in scenes))
                self.assertTrue(all(len(scene[1].split())>=9 for scene in scenes))

    def test_stories_join_production_selection_without_bypassing_qa(self):
        found={x["title"]:x for x in catalog(limit=512)}
        for key,title,genre,scenes in PLOTS:
            with self.subTest(title=title):
                story=found[title]
                self.assertEqual(story["kind"],"authored_causal_story")
                self.assertTrue(story["production_ready"])
                self.assertIsNone(publication_rejection(story))
                self.assertEqual([b["story_beat"] for b in story["story_beats"]],["reveal","build","twist","payoff"])
                self.assertEqual(len(story["story_beats"]),4)

    def test_finite_supply_is_excluded_once_seen(self):
        ids={x["content_id"] for x in catalog(limit=512) if x["title"] not in {p[1] for p in PLOTS}}
        remaining=catalog(excluded_ids=ids,limit=512)
        self.assertEqual({x["title"] for x in remaining},{p[1] for p in PLOTS})
        self.assertEqual(len(remaining),20)

if __name__=="__main__":
    unittest.main()
