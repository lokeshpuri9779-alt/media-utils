"""Finale: continuity, two actors, key destruction, and next-season setup."""
import unittest
from PIL import Image, ImageChops
from astra_errors import CreativeReject
from astra_v2.omniroute_local import catalog
from astra_v2.human_story_performance import (
    EPISODE_FOUR_ACTIONS, EPISODE_THREE_ACTIONS
)
from astra_v2.unified_story_engine import draw_story_frame, validate_story_shot


def beats(episode):
    record=next(x for x in catalog() if x['episode']==episode)
    return [{**s,'story_visual_seed':record['content_id'],
             'story_title':record['title']} for s in record['story_beats']]


def frame(shot,t):
    output=Image.new('RGB',(1080,1920),(10,20,33))
    assert draw_story_frame(output,shot,t)=='human'
    return output


class SeasonFinalePerformanceTests(unittest.TestCase):
    def test_finale_is_fully_authored_and_prior_character_identity_kept(self):
        self.assertEqual([s['story_human_action'] for s in beats(4)],
                         list(EPISODE_FOUR_ACTIONS))
        for episode in (1,2,3,4):
            self.assertEqual({s['story_human_actor'] for s in beats(episode)}, {'mara'})
        for s in beats(4):
            self.assertEqual(s['visual'],'door')
            self.assertEqual(validate_story_shot(s),'human')

    def test_every_finale_action_animates_without_text_safe_region_intrusion(self):
        for index,shot in enumerate(beats(4),1):
            early=frame(shot,.26)
            late=frame(shot,1.85)
            self.assertIsNotNone(ImageChops.difference(
                early.crop((90,570,1010,1320)),
                late.crop((90,570,1010,1320))).getbbox(),
                f'Finale scene {index} is static')
            source=Image.new('RGB',(1080,1920),(10,20,33))
            for zone in ((0,0,1080,480),(0,1400,1080,1920)):
                self.assertIsNone(ImageChops.difference(
                    early.crop(zone),source.crop(zone)).getbbox())

    def test_first_scene_has_two_separate_performers(self):
        shot=beats(4)[0]
        result=frame(shot,.74)
        blank=Image.new('RGB',(1080,1920),(10,20,33))
        for bounds in ((195,605,435,1200),(655,605,920,1200)):
            self.assertIsNotNone(ImageChops.difference(
                result.crop(bounds),blank.crop(bounds)).getbbox())

    def test_key_separates_as_a_visible_breaking_action(self):
        shot=beats(4)[2]
        a=frame(shot,.30).crop((420,874,740,1098))
        b=frame(shot,1.95).crop((420,874,740,1098))
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())

    def test_book_and_sea_door_are_present_only_in_the_final_reveal(self):
        final=frame(beats(4)[3],1.9)
        before=frame(beats(4)[0],1.9)
        page=(602,1030,968,1264)
        self.assertIsNotNone(ImageChops.difference(
            final.crop(page),before.crop(page)).getbbox())

    def test_wrong_episode_wrong_action_or_missing_plot_contract_rejected(self):
        sample=beats(4)[2]
        invalid=(
            {'story_visual_seed':'rayvan-season-01-episode-03'},
            {'story_human_actor':'brother'},
            {'story_human_action':EPISODE_THREE_ACTIONS[0]},
            {'visual':'signal'},
            {'story_cast':['owl']},
            {'speech':'A quiet glow appeared.'},
        )
        for update in invalid:
            with self.subTest(update=update),self.assertRaises(CreativeReject):
                validate_story_shot({**sample,**update})


if __name__=='__main__':
    unittest.main()
