"""Review-only regression for Episode 1's missing physical floorboard reveal.

These tests validate actual pixels and permitted action routing, NOT whether
the complete encoded MP4 satisfies semantic/narrative visual review.
"""
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw
from astra_errors import CreativeReject
from astra_v2.human_floorboard_reveal import (
    OPENING, LIFTED_BOARD, WOOD, VOID, EXPOSED_CABLE, CONCEALED_CABLE,
    draw_floorboard_hatch, draw_floor_cable_trace, _cable_progress_point,
    draw_radio_inside_hatch, HIDDEN_RADIO_CAPTURE,
    floorboard_panel, floorboard_reveal_fraction,
)
from astra_v2.human_story_performance import draw_human_scene
from astra_v2.omniroute_local import catalog


def trace_shot():
    story = next(s for s in catalog(max_candidates=30)
                 if s["content_id"] == "rayvan-season-01-episode-01")
    beat = next(b for b in story["story_beats"]
                if b["story_human_action"] == "trace_cable")
    return {**beat, "story_visual_seed": story["content_id"],
            "story_title": story["title"], "duration": 12.0}


class FloorboardRevealTests(unittest.TestCase):
    def test_physical_hatch_covers_room_first_then_exposes_darker_space(self):
        start = Image.new("RGB", (1080, 1920), (23, 35, 50))
        end = start.copy()
        a = draw_floorboard_hatch(ImageDraw.Draw(start), 0.0)
        b = draw_floorboard_hatch(ImageDraw.Draw(end), 1.0)
        self.assertEqual(a["hatch_open_fraction"], 0.0)
        self.assertEqual(b["hatch_open_fraction"], 1.0)
        self.assertFalse(a["verified_semantics"])
        self.assertFalse(b["verified_semantics"])
        self.assertEqual(start.getpixel((370, 1100)), WOOD)
        self.assertEqual(end.getpixel((370, 1100)), VOID)
        # The upright flap must remain above the hole, not slide out of frame.
        self.assertEqual(end.getpixel((370, 940)), WOOD)
        self.assertNotEqual(start.getpixel((370, 940)), WOOD)
        self.assertEqual(floorboard_panel(0), OPENING)
        self.assertEqual(floorboard_panel(1), LIFTED_BOARD)
        changed = ImageChops.difference(
            start.crop((150, 925, 510, 1230)),
            end.crop((150, 925, 510, 1230)))
        self.assertIsNotNone(changed.getbbox())
        # The artwork remains entirely in the subject stage; no changes to
        # text/header and caption-safe regions.
        for region in ((0, 0, 1080, 480), (0, 1400, 1080, 1920)):
            self.assertIsNone(ImageChops.difference(
                start.crop(region), end.crop(region)).getbbox())

    def test_upright_hatch_is_inside_actual_story_camera_crop(self):
        from astra_v2.human_story_composition import stage_crop_box
        from astra_v2.human_action_choreography import action_state
        for p in (.65, .88, .97):
            with self.subTest(progress=p):
                # The flap is visible even after actual stage camera reframing,
                # not just on an uncropped internal drawing canvas.
                box = stage_crop_box("trace_cable", p * 12, 12)
                self.assertLess(box[0], 370)
                self.assertGreater(box[2], 370)
                self.assertLess(box[1], 940)
                self.assertGreater(box[3], 940)
                frac = floorboard_reveal_fraction(
                    action_state("trace_cable", p * 12, 12).event)
                self.assertGreater(frac, .1)
        self.assertEqual(LIFTED_BOARD[0], OPENING[0])
        self.assertEqual(LIFTED_BOARD[1], OPENING[1])

    def test_opening_is_finite_gradual_and_deterministic(self):
        fractions = [floorboard_reveal_fraction(x / 100) for x in range(101)]
        self.assertTrue(all(a <= b for a, b in zip(fractions, fractions[1:])))
        self.assertEqual(fractions[0], 0)
        self.assertEqual(fractions[-1], 1)
        for event in (0, .1, .4, .55, .75, 1):
            with self.subTest(event=event):
                self.assertEqual(floorboard_panel(event), floorboard_panel(event))
                self.assertTrue(all(80 <= x <= 1000 and 555 <= y <= 1260
                                    for x, y in floorboard_panel(event)))
        for bad in (-.1, 1.01, float("nan"), float("inf"), "bad", None, True):
            with self.subTest(bad=bad), self.assertRaises(CreativeReject):
                floorboard_reveal_fraction(bad)

    def test_actual_pilot_actor_path_draws_hatch_and_delays_second_radio(self):
        from astra_v2.human_action_choreography import action_state
        from astra_v2.human_story_performance import _radio
        shot = trace_shot()
        rendered = []
        for p in (.12, .49, .62, .88):
            canvas = Image.new("RGB", (1080, 1920), (23, 35, 50))
            with patch("astra_v2.human_floorboard_reveal.draw_floorboard_hatch",
                       wraps=draw_floorboard_hatch) as hatch, \
                 patch("astra_v2.human_story_performance._radio",
                       wraps=_radio) as radios:
                self.assertTrue(draw_human_scene(canvas, shot, p * 12))
            hatch.assert_called_once()
            self.assertAlmostEqual(hatch.call_args.args[1],
                                   action_state("trace_cable", p * 12, 12).event)
            coords = [(x.args[1], x.args[2]) for x in radios.call_args_list]
            rendered.append((canvas, coords))
        self.assertEqual([len(radio) for _, radio in rendered], [1, 1, 2, 2])
        self.assertIn((342, 1109), rendered[-1][1])
        self.assertIsNotNone(ImageChops.difference(
            rendered[0][0].crop((220, 1030, 520, 1200)),
            rendered[-1][0].crop((220, 1030, 520, 1200))).getbbox())

    def test_cable_is_continuous_socket_to_hatch_before_hidden_receiver_reveal(self):
        # Source radio port and hatch entry are in the existing verified scene.
        self.assertEqual(EXPOSED_CABLE[0], (750, 1038))
        self.assertEqual(EXPOSED_CABLE[-1], CONCEALED_CABLE[0])
        self.assertEqual(_cable_progress_point(EXPOSED_CABLE, 0), EXPOSED_CABLE[0])
        self.assertEqual(_cable_progress_point(EXPOSED_CABLE, 1), EXPOSED_CABLE[-1])
        self.assertNotEqual(_cable_progress_point(EXPOSED_CABLE, .15),
                            _cable_progress_point(EXPOSED_CABLE, .85))

        image_early = Image.new("RGB", (1080, 1920), (23, 35, 50))
        image_late = image_early.copy()
        first = draw_floor_cable_trace(ImageDraw.Draw(image_early), .1, 0)
        last = draw_floor_cable_trace(ImageDraw.Draw(image_late), 1, 1)
        self.assertFalse(first["underfloor_connection_visible"])
        self.assertTrue(last["underfloor_connection_visible"])
        self.assertFalse(first["visual_semantics_verified"])
        self.assertFalse(last["visual_semantics_verified"])
        # The late new underfloor extension is not exposed before reveal.
        self.assertEqual(image_early.getpixel((441, 1148)), (23, 35, 50))
        self.assertNotEqual(image_late.getpixel((441, 1148)), (23, 35, 50))
        self.assertNotEqual(image_early.getpixel(first["marker"]),
                            image_late.getpixel(first["marker"]))
        for region in ((0, 0, 1080, 480), (0, 1400, 1080, 1920)):
            self.assertIsNone(ImageChops.difference(
                image_early.crop(region), image_late.crop(region)).getbbox())

    def test_actual_human_scene_renders_moving_trace_and_late_connection(self):
        from astra_v2.human_action_choreography import action_state
        from astra_v2.human_cinematic_camera import apply_human_camera
        from astra_v2.human_story_composition import stage_crop_box
        shot = trace_shot()
        observations = []
        for p in (.10, .38, .65, .91):
            t = p * 12.
            image = Image.new("RGB", (1080, 1920), (23, 35, 50))
            with patch("astra_v2.human_floorboard_reveal.draw_floor_cable_trace",
                       wraps=draw_floor_cable_trace) as tracer:
                self.assertTrue(draw_human_scene(image, shot, t))
            tracer.assert_called_once()
            self.assertAlmostEqual(
                tracer.call_args.args[1], action_state("trace_cable", t, 12).attention)
            self.assertAlmostEqual(
                tracer.call_args.args[2], action_state("trace_cable", t, 12).event)
            marker = _cable_progress_point(
                EXPOSED_CABLE, action_state("trace_cable", t, 12).attention)
            crop = stage_crop_box("trace_cable", t, 12)
            self.assertTrue(crop[0] <= marker[0] <= crop[2])
            self.assertTrue(crop[1] <= marker[1] <= crop[3])
            # Exercise the same real camera crop used before MP4 encoding.
            composed = apply_human_camera(image, shot, t)
            self.assertEqual(composed.size, image.size)
            observations.append((marker, composed))
        self.assertNotEqual(observations[0][0], observations[-1][0])
        self.assertIsNotNone(ImageChops.difference(
            observations[0][1].crop((160, 520, 920, 1330)),
            observations[-1][1].crop((160, 520, 920, 1330))).getbbox())

    def test_trace_progress_rejects_invalid_or_unreviewed_inputs(self):
        img = ImageDraw.Draw(Image.new("RGB", (1080, 1920)))
        for invalid in (-.01, 1.01, float("nan"), float("inf"), True, None, "0.3"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(CreativeReject):
                    _cable_progress_point(EXPOSED_CABLE, invalid)
                with self.assertRaises(CreativeReject):
                    draw_floor_cable_trace(img, invalid, 0)
                with self.assertRaises(CreativeReject):
                    draw_floor_cable_trace(img, 0, invalid)
        with self.assertRaises(CreativeReject):
            draw_floor_cable_trace(None, .5, .5)

    def test_hidden_radio_is_clipped_behind_hatch_not_on_top_of_panel(self):
        from astra_v2.human_story_performance import _radio
        self.assertEqual(HIDDEN_RADIO_CAPTURE, (210,960,515,1210))
        for event in (.25, .50, 1.0):
            with self.subTest(event=event):
                before=Image.new("RGB",(1080,1920),(23,35,50))
                draw=ImageDraw.Draw(before)
                draw_floorboard_hatch(draw,event)
                after=before.copy()
                with patch("astra_v2.human_story_performance._radio",
                           wraps=_radio) as actual_radio:
                    info=draw_radio_inside_hatch(
                        after,ImageDraw.Draw(after),event,actual_radio,7.8)
                actual_radio.assert_called_once()
                self.assertEqual(actual_radio.call_args.args[1:3],(342,1109))
                self.assertTrue(info["masked_behind_moving_panel"])
                self.assertEqual(info["semantic_quality"],"not_verified")
                self.assertFalse(info["publication_approval"])
                diff=ImageChops.difference(after,before)
                # No antenna, receiver case, or decorative pixel leaks from
                # the lower room onto the upright panel or main stage.
                for forbidden in ((0,0,1080,1077),
                                  (0,1211,1080,1920),
                                  (0,1078,210,1210),
                                  (515,1078,1080,1210)):
                    self.assertIsNone(diff.crop(forbidden).getbbox(),
                                      (event,forbidden))
                self.assertIsNotNone(diff.crop((240,1080,480,1190)).getbbox())
                if event == .25:
                    # The not-yet-lifted panel still occludes the receiver.
                    self.assertEqual(after.getpixel((342,1100)),
                                     before.getpixel((342,1100)))
                if event == 1.0:
                    self.assertNotEqual(after.getpixel((342,1100)),
                                        before.getpixel((342,1100)))

    def test_actual_post_camera_hatch_reveal_changes_when_radio_is_inside(self):
        from astra_v2.human_cinematic_camera import apply_human_camera
        shot=trace_shot()
        t=12*.88
        base=Image.new("RGB",(1080,1920),(23,35,50))
        clipped=base.copy()
        with patch("astra_v2.human_floorboard_reveal.draw_radio_inside_hatch",
                   wraps=draw_radio_inside_hatch) as hidden:
            draw_human_scene(clipped,shot,t)
        hidden.assert_called_once()
        with patch("astra_v2.human_floorboard_reveal.draw_radio_inside_hatch",
                   return_value=None):
            draw_human_scene(base,shot,t)
        a=apply_human_camera(clipped,shot,t)
        b=apply_human_camera(base,shot,t)
        self.assertIsNotNone(ImageChops.difference(
            a.crop((0,480,1080,1370)),b.crop((0,480,1080,1370))).getbbox())
        for box in ((0,0,1080,480),(0,1400,1080,1920)):
            self.assertIsNone(ImageChops.difference(
                a.crop(box),b.crop(box)).getbbox())

    def test_hidden_radio_rejects_invalid_surface_and_story_time(self):
        from astra_v2.human_story_performance import _radio
        frame=Image.new("RGB",(1080,1920),(23,35,50))
        draw=ImageDraw.Draw(frame)
        for bad in (-.1,1.1,float("nan"),float("inf"),None,True):
            with self.subTest(bad=bad),self.assertRaises(CreativeReject):
                draw_radio_inside_hatch(frame,draw,bad,_radio,1.)
        with self.assertRaises(CreativeReject):
            draw_radio_inside_hatch(None,draw,.5,_radio,1.)
        with self.assertRaises(CreativeReject):
            draw_radio_inside_hatch(frame,draw,.5,_radio,float("nan"))
        with self.assertRaises(CreativeReject):
            draw_radio_inside_hatch(frame,draw,.5,None,1.)

    def test_invalid_image_surface_rejected_without_silent_fallback(self):
        with self.assertRaises(CreativeReject):
            draw_floorboard_hatch(None, .5)


if __name__ == "__main__":
    unittest.main()
