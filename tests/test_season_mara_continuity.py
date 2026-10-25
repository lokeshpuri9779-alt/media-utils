"""Season-one continuation: explicit story acting, continuity and negative checks."""
import unittest

from PIL import Image, ImageChops

from astra_errors import CreativeReject
from astra_v2.human_story_performance import (
    ACTIONS, EPISODE_TWO_ACTIONS, EPISODE_TWO_ID, draw_human_scene
)
from astra_v2.omniroute_local import catalog
from astra_v2.unified_story_engine import draw_story_frame, validate_story_shot


def episode_shots(number):
    story=next(s for s in catalog() if s['episode']==number)
    return [{**shot,'story_visual_seed':story['content_id'],
             'story_title':story['title']} for shot in story['story_beats']]


class SerializedMaraContinuityTests(unittest.TestCase):
    def test_canonical_episode_one_unchanged_and_episode_two_choreographed(self):
        self.assertEqual([s['story_human_action'] for s in episode_shots(1)],list(ACTIONS))
        self.assertEqual([s['story_human_action'] for s in episode_shots(2)],
                         list(EPISODE_TWO_ACTIONS))
        self.assertEqual({s['story_human_actor'] for n in (1,2)
                          for s in episode_shots(n)}, {'mara'})
        self.assertEqual({validate_story_shot(s) for n in (1,2)
                          for s in episode_shots(n)}, {'human'})
        for shot in episode_shots(2):
            self.assertEqual(shot['visual'],'door')

    def test_every_episode_two_acted_scene_changes_over_time(self):
        for index,shot in enumerate(episode_shots(2),1):
            a=Image.new('RGB',(1080,1920),(10,20,33))
            b=a.copy()
            self.assertEqual(draw_story_frame(a,shot,.38),'human')
            self.assertEqual(draw_story_frame(b,shot,1.55),'human')
            region=(100,570,1010,1310)
            self.assertIsNotNone(ImageChops.difference(
                a.crop(region),b.crop(region)).getbbox(),
                f'Episode 2 scene {index} contains no acting/motion')
            self.assertIsNone(ImageChops.difference(
                a.crop((0,0,1080,480)),Image.new('RGB',(1080,480),(10,20,33))).getbbox())
            self.assertIsNone(ImageChops.difference(
                a.crop((0,1400,1080,1920)),Image.new('RGB',(1080,520),(10,20,33))).getbbox())

    def test_episode_two_rejects_wrong_plot_objects_and_cross_episode_actions(self):
        shot=episode_shots(2)[2]
        invalid=(
            {'story_visual_seed':'rayvan-season-01-episode-03'},
            {'story_human_actor':'another-person'},
            {'story_human_action':ACTIONS[0]},
            {'visual':'signal'},
            {'story_cast':['fox']},
            {'speech':'An anonymous item was delivered.'},
        )
        for update in invalid:
            with self.subTest(update=update),self.assertRaises(CreativeReject):
                validate_story_shot({**shot,**update})

    def test_other_episodes_do_not_inherit_unreviewed_acted_human_grammar(self):
        self.assertEqual([s['story_human_actor'] for s in episode_shots(4)],['mara']*4)
        with self.assertRaises(CreativeReject):
            draw_human_scene(Image.new('RGB',(1080,1920)),{
                **episode_shots(2)[0],
                'story_visual_seed':'rayvan-season-01-episode-03'
            },1.0)


if __name__=='__main__':
    unittest.main()
