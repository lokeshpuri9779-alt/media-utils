"""Gate fresh 2-actor stories before they enter the autonomous preload."""
import unittest
from astra_v2.pillow_duo_stories import PLOTS as DUO_PLOTS
from astra_v2.story_forge import catalog
from astra_v2.pillow_duo_scene import scene_pair, scene_prop
from astra_v2.story_action_motion import choose_action
from astra_v2.publication_quality import publication_rejection

class StorySupplyTests(unittest.TestCase):
    def test_unique_curated_not_generic_templates(self):
        self.assertEqual(len(DUO_PLOTS), 12)
        keys=[s[0] for s in DUO_PLOTS]
        titles=[s[1].casefold() for s in DUO_PLOTS]
        self.assertEqual(len(set(keys)), len(keys))
        self.assertEqual(len(set(titles)), len(titles))
        self.assertTrue(all(len(s[3]) == 4 for s in DUO_PLOTS))
        for key,title,genre,beats in DUO_PLOTS:
            self.assertEqual(len(scene_pair({"speech":title})), 2, title)
            self.assertGreaterEqual(len(set(b[1] for b in beats)), 4)
            self.assertTrue(all(len(b[1].split()) >= 9 for b in beats), title)
            self.assertTrue(all(b[2] == "story" for b in beats), title)
            self.assertTrue(all(len(b) == 4 for b in beats))
            actions=[choose_action({"speech":b[1]}) for b in beats]
            self.assertGreaterEqual(sum(x!="idle" for x in actions),2,title)
            self.assertTrue(any(scene_prop({"speech":b[1]}) for b in beats),title)

    def test_every_story_is_available_and_publication_eligible(self):
        found=catalog(limit=256)
        wanted={s[1] for s in DUO_PLOTS}
        selected=[s for s in found if s["title"] in wanted]
        self.assertEqual({s["title"] for s in selected}, wanted)
        self.assertEqual(len({s["content_id"] for s in selected}),12)
        self.assertEqual(len({s["plot_fingerprint"] for s in selected}),12)
        for story in selected:
            self.assertEqual(story["kind"], "authored_causal_story")
            self.assertTrue(story["production_ready"])
            self.assertIsNone(publication_rejection(story))
            self.assertEqual([beat["story_beat"] for beat in story["story_beats"]],
                             ["reveal","build","twist","payoff"])
            self.assertTrue(all(beat["visual"] == "story" for beat in story["story_beats"]))

    def test_title_cast_is_retained_in_real_studio_plan(self):
        from studio_renderer import make_plan
        story=next(s for s in catalog(limit=256)
                   if s["title"] == "The Fox and Rabbit's Last Lantern")
        cast=scene_pair({"speech":story["title"]})
        plan=make_plan(story)
        self.assertEqual(len(plan),4)
        self.assertEqual([s.get("story_cast") for s in plan],[cast]*4)
        self.assertTrue(all(s.get("story_subject") in cast for s in plan))

    def test_used_story_cannot_be_reissued(self):
        story=catalog(limit=256)[0]
        expected_title="The Fox and Rabbit's Last Lantern"
        self.assertEqual(story["title"], expected_title)
        excluded=catalog(excluded_ids={story["content_id"]},limit=256)
        self.assertNotIn(story["content_id"],{s["content_id"] for s in excluded})
        excluded=catalog(excluded_plot_hashes={story["plot_fingerprint"]},limit=256)
        self.assertNotIn(story["content_id"],{s["content_id"] for s in excluded})
if __name__ == "__main__":
    unittest.main()
