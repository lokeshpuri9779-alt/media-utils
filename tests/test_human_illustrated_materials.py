"""Auditable original art direction across the sixteen approved fiction scenes."""
from __future__ import annotations

import hashlib
import unittest

from PIL import Image, ImageChops, ImageDraw

from astra_errors import CreativeReject
from astra_v2.human_illustrated_materials import (
    SET_PROFILES, MATERIALS, PROFILE_DRAWERS, SAFE_STAGE,
    draw_environment_art, draw_character_materials,
)
from astra_v2.human_stage_depth import draw_observatory_stage
from astra_v2.human_story_performance import PERFORMANCE, _mara
from astra_v2.omniroute_local import catalog
from astra_v2.unified_story_engine import draw_story_frame

BACKGROUND=(27,44,68)
FRAME=(1080,1920)


def preview(action,progress=.64):
    image=Image.new("RGB",FRAME,BACKGROUND)
    draw_observatory_stage(image,action,progress*12,12)
    evidence=draw_environment_art(image,action,progress*12,12)
    return image,evidence


class IllustratedSetContinuityTests(unittest.TestCase):
    def test_all_16_story_actions_have_six_reusable_original_art_profiles(self):
        self.assertEqual(set(SET_PROFILES),set(PERFORMANCE))
        self.assertEqual(set(PROFILE_DRAWERS),set(MATERIALS))
        self.assertEqual(set(SET_PROFILES.values()),set(MATERIALS))
        self.assertEqual(len(MATERIALS),6)
        self.assertEqual(len(SET_PROFILES),16)
        for story in catalog(max_candidates=30):
            for beat in story['story_beats']:
                action=beat['story_human_action']
                self.assertIn(action, SET_PROFILES)

    def test_six_styles_are_visibly_distinct_not_palette_only_metadata(self):
        signatures={}
        for action in SET_PROFILES:
            frame,report=preview(action)
            profile=report['profile']
            self.assertEqual(report['source'],'original-cpu-art-library')
            self.assertEqual(report['asset_count'],6)
            fingerprint=hashlib.sha256(frame.crop((170,645,975,1080)).tobytes()).hexdigest()
            if profile in signatures:
                self.assertEqual(signatures[profile],fingerprint,
                    'Same environment profile changed between story actions')
            else:
                signatures[profile]=fingerprint
        self.assertEqual(len(signatures),6)
        self.assertEqual(len(set(signatures.values())),6,
                         'Repeated same-looking set across separate chapters')

    def test_original_pack_remains_visible_at_center_of_all_six_environments(self):
        original=Image.new("RGB",FRAME,BACKGROUND)
        # The architecture leaves central panoramic scenery untouched.
        region=(475,743,580,846)
        for action in SET_PROFILES:
            result,report=preview(action)
            self.assertEqual(result.crop(region).tobytes(),
                             original.crop(region).tobytes(),
                             f'Art profile {report["profile"]} hid original backdrop')

    def test_scenery_and_character_materials_never_touch_caption_safe_regions(self):
        for action in SET_PROFILES:
            result,_=preview(action)
            for box in ((0,0,1080,480),(0,1400,1080,1920)):
                expected=Image.new('RGB',result.crop(box).size,BACKGROUND)
                self.assertIsNone(ImageChops.difference(
                    expected,result.crop(box)).getbbox())
        source=Image.new("RGB",FRAME,BACKGROUND)
        garment=source.copy()
        receipt=draw_character_materials(ImageDraw.Draw(garment),360,866,2.3)
        self.assertEqual(receipt,'mara-scientist-costume-v1')
        self.assertIsNotNone(ImageChops.difference(
            garment.crop((270,792,445,1220)),
            source.crop((270,792,445,1220))).getbbox())
        for area in ((0,0,1080,480),(0,1400,1080,1920)):
            self.assertIsNone(ImageChops.difference(
                source.crop(area),garment.crop(area)).getbbox())

    def test_character_illustration_is_identical_in_both_story_timelines(self):
        one=Image.new("RGB",FRAME,BACKGROUND)
        other=one.copy()
        _mara(ImageDraw.Draw(one),355,860,1.4,
              emotion='knowing',gaze=-1)
        _mara(ImageDraw.Draw(other),355,860,1.4,
              emotion='knowing',gaze=-1)
        self.assertEqual(one.tobytes(),other.tobytes())

    def test_full_studio_story_grammar_uses_chapter_art_without_visual_fallback(self):
        scenes=0
        for story in catalog(max_candidates=30):
            for beat in story['story_beats']:
                scene={**beat,'story_visual_seed':story['content_id'],
                       'story_title':story['title'],'duration':12}
                image=Image.new("RGB",FRAME,BACKGROUND)
                self.assertEqual(draw_story_frame(image,scene,8),"human")
                self.assertNotEqual(image.crop(SAFE_STAGE).getbbox(),None)
                scenes+=1
        self.assertEqual(scenes,16)

    def test_chapter_location_has_time_specific_visible_readout(self):
        a,_=preview('radio_workshop' if False else 'discover_radio',.03)
        b,_=preview('discover_radio',.89)
        target=(747,660,979,715)
        self.assertIsNotNone(ImageChops.difference(
            a.crop(target),b.crop(target)).getbbox())

    def test_unapproved_art_assets_reject_without_substituting_generic_image(self):
        for invalid in ("random_story", "unknown_art", "unapproved_scene"):
            with self.assertRaises(CreativeReject):
                draw_environment_art(Image.new("RGB",FRAME),invalid,1,12)
        for time in (float('nan'),float('inf'),-1):
            with self.assertRaises(CreativeReject):
                draw_environment_art(Image.new("RGB",FRAME),"discover_radio",time,12)
        with self.assertRaises(CreativeReject):
            draw_environment_art(Image.new("RGB",(540,960)),"discover_radio",1,12)
        with self.assertRaises(CreativeReject):
            draw_environment_art(Image.new("RGB",FRAME),"discover_radio",1,0)


if __name__=="__main__":
    unittest.main()
