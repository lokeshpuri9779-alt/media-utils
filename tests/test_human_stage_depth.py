"""Foreground observatory must reveal real scenery and ground animated actors."""
import unittest

from PIL import Image, ImageChops

from astra_errors import CreativeReject
from astra_v2.human_stage_depth import (
    ACTION_SEQUENCE, STAGE_BOUNDS, draw_observatory_stage, draw_actor_shadow
)
from astra_v2.omniroute_local import catalog
from astra_v2.unified_story_engine import draw_story_frame


def patterned_background():
    canvas=Image.new("RGB",(1080,1920),(23,41,71))
    pixels=canvas.load()
    # Vary both axes: an opaque replacement would erase this local source.
    for y in range(610,1160):
        for x in range(175,905):
            pixels[x,y]=(25+x%91,34+y%81,66+(x//17+y//9)%121)
    return canvas


def story_shots():
    for story in catalog(max_candidates=30):
        for scene in story["story_beats"]:
            yield {**scene, "story_visual_seed":story["content_id"],
                   "story_title":story["title"],"duration":12.0}


class LayeredObservatoryStageTests(unittest.TestCase):
    def test_preserves_original_art_within_glazed_center(self):
        before=patterned_background()
        after=before.copy()
        receipt=draw_observatory_stage(after,"discover_radio",4.0,12.0)
        self.assertTrue(receipt["background_visible"])
        self.assertEqual(receipt["depth_layers"],4)
        self.assertEqual(receipt["frame"],STAGE_BOUNDS)
        self.assertEqual(after.getpixel((525,795)),before.getpixel((525,795)))
        # More than half the broad window stays visibly the supplied imagery;
        # unlike the old filled rectangle this is not merely one tiny hole.
        bounds=(215,710,870,980)
        original=before.crop(bounds).tobytes()
        result=after.crop(bounds).tobytes()
        same=sum(a==b for a,b in zip(original,result))
        self.assertGreater(same/len(original),.65,
                           "Stage masks the supplied background almost entirely")

    def test_architecture_has_real_depth_not_invisible_overlay(self):
        original=patterned_background()
        scene=original.copy()
        draw_observatory_stage(scene,"discover_radio",7.0,12.0)
        for point in ((400,580),(102,820),(968,820),(540,1230)):
            self.assertNotEqual(scene.getpixel(point),original.getpixel(point))
        # Architecture also contains a physically different near floor plane.
        self.assertNotEqual(scene.getpixel((540,1200)),scene.getpixel((540,600)))

    def test_stage_lights_react_to_authored_warning(self):
        a=patterned_background()
        b=a.copy()
        early=draw_observatory_stage(a,"hear_warning",1.0,12)
        late=draw_observatory_stage(b,"hear_warning",9.5,12)
        self.assertFalse(early["warning_lamps"])
        self.assertTrue(late["warning_lamps"])
        lamp=(210,575,855,603)
        self.assertIsNotNone(ImageChops.difference(
            a.crop(lamp),b.crop(lamp)).getbbox())

    def test_actor_contact_shadow_changes_before_body_is_drawn(self):
        base=Image.new("RGB",(1080,1920),(47,58,72))
        person=base.copy()
        from PIL import ImageDraw
        draw_actor_shadow(ImageDraw.Draw(person),370,875,progress=.8)
        self.assertNotEqual(base.getpixel((370,1215)),person.getpixel((370,1215)))
        running=base.copy()
        draw_actor_shadow(ImageDraw.Draw(running),370,875,
                          running=True,progress=.8)
        self.assertIsNotNone(ImageChops.difference(
            person.crop((210,1195,550,1248)),
            running.crop((210,1195,550,1248))).getbbox())

    def test_every_approved_acting_shot_draws_stage_without_hiding_text(self):
        shots=list(story_shots())
        self.assertEqual(len(shots),len(ACTION_SEQUENCE))
        for shot in shots:
            with self.subTest(action=shot["story_human_action"]):
                image=Image.new("RGB",(1080,1920),(25,34,52))
                original=image.copy()
                self.assertEqual(draw_story_frame(image,shot,3.4),"human")
                self.assertIsNotNone(ImageChops.difference(
                    image.crop((80,555,1000,1260)),
                    original.crop((80,555,1000,1260))).getbbox())
                for zone in ((0,0,1080,480),(0,1400,1080,1920)):
                    self.assertIsNone(ImageChops.difference(
                        image.crop(zone),original.crop(zone)).getbbox())

    def test_unsafe_stage_geometry_and_unknown_actions_are_rejected(self):
        with self.assertRaises(CreativeReject):
            draw_observatory_stage(Image.new("RGB",(540,960)),
                                  "discover_radio",0,12)
        with self.assertRaises(CreativeReject):
            draw_observatory_stage(Image.new("RGB",(1080,1920)),
                                  "unreviewed_action",0,12)
        with self.assertRaises((ValueError,CreativeReject)):
            draw_observatory_stage(Image.new("RGB",(1080,1920)),
                                  "discover_radio",float("nan"),12)


if __name__=="__main__":
    unittest.main()
