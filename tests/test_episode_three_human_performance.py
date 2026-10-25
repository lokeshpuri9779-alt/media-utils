"""The Tomorrow Signal Episode 3: explicit human acting and serialized continuity."""
import unittest
from PIL import Image, ImageChops
from astra_errors import CreativeReject
from astra_v2.omniroute_local import catalog
from astra_v2.human_story_performance import (
    EPISODE_THREE_ACTIONS, EPISODE_THREE_ID, EPISODE_TWO_ACTIONS
)
from astra_v2.unified_story_engine import draw_story_frame, validate_story_shot


def beats(number):
    story=next(s for s in catalog() if s['episode']==number)
    return [{**beat, 'story_visual_seed':story['content_id'],
             'story_title':story['title']} for beat in story['story_beats']]


class EpisodeThreeHumanPerformanceTests(unittest.TestCase):
    def test_four_exact_actions_have_approved_human_grammar(self):
        shots=beats(3)
        self.assertEqual([s['story_human_action'] for s in shots],
                         list(EPISODE_THREE_ACTIONS))
        self.assertEqual({s['story_human_actor'] for s in shots},{'mara'})
        self.assertTrue(all(s['visual']=='door' for s in shots))
        self.assertTrue(all(validate_story_shot(s)=='human' for s in shots))
        self.assertEqual({s['story_human_actor'] for n in (1,2,3)
                          for s in beats(n)},{'mara'})

    def test_acted_shots_have_real_frame_changes_inside_safe_stage(self):
        for i,shot in enumerate(beats(3),1):
            frame=Image.new('RGB',(1080,1920),(10,20,33))
            a=frame.copy()
            b=frame.copy()
            self.assertEqual(draw_story_frame(a,shot,.31),'human')
            self.assertEqual(draw_story_frame(b,shot,1.64),'human')
            region=(90,570,1010,1335)
            self.assertIsNotNone(
                ImageChops.difference(a.crop(region),b.crop(region)).getbbox(),
                f'Episode 3 scene {i} is frozen')
            for box in ((0,0,1080,480),(0,1400,1080,1920)):
                self.assertIsNone(ImageChops.difference(
                    a.crop(box),frame.crop(box)).getbbox(),
                    f'Episode 3 scene {i} violates safe typography region')

    def test_reverse_clock_has_changing_time_hand(self):
        shot=beats(3)[1]
        one=Image.new('RGB',(1080,1920),(10,20,33))
        two=one.copy()
        draw_story_frame(one,shot,.2)
        draw_story_frame(two,shot,2.4)
        clock=(620,720,885,1010)
        self.assertIsNotNone(ImageChops.difference(
            one.crop(clock),two.crop(clock)).getbbox())

    def test_double_is_drawn_on_opposite_side_of_door(self):
        shot=beats(3)[3]
        original=Image.new('RGB',(1080,1920),(10,20,33))
        frame=original.copy()
        draw_story_frame(frame,shot,.85)
        for box in ((185,675,440,1200),(630,675,990,1200)):
            self.assertIsNotNone(ImageChops.difference(
                frame.crop(box),original.crop(box)).getbbox(),
                'Both Mara performers must be visible')

    def test_unapproved_actor_story_action_and_plot_fails_closed(self):
        third=beats(3)[3]
        cases=(
            {'story_visual_seed':'rayvan-season-01-episode-04'},
            {'story_human_actor':'stranger'},
            {'story_human_action':EPISODE_TWO_ACTIONS[0]},
            {'visual':'signal'},
            {'story_cast':['fox']},
            {'speech':'Mara stood next to a tree with no key or radios.'},
        )
        for change in cases:
            with self.subTest(change=change),self.assertRaises(CreativeReject):
                validate_story_shot({**third,**change})
        self.assertEqual({beat['story_human_actor'] for beat in beats(4)}, {'mara'})


if __name__=='__main__':
    unittest.main()
