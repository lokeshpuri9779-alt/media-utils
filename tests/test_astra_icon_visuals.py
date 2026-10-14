"""Verify cached SVG drawing produces a visible, time-varying asset."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageChops
from astra_v2 import icon_visuals

SVG=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><line x1="4" y1="4" x2="20" y2="20"/></svg>'

class IconVisualTests(unittest.TestCase):
    def test_match_story_subject(self):
        self.assertIsNone(icon_visuals.pick_icon({"speech":"A fox ran away."}))
        self.assertEqual(icon_visuals.pick_icon({"speech":"A dog ran away."}),"dog")
        self.assertIsNone(icon_visuals.pick_icon({"speech":"An owl flew away."}))
        self.assertIsNone(icon_visuals.pick_icon({"speech":"An otter found a box."}))
        self.assertEqual(icon_visuals.pick_icon({"speech":"The train arrived."}),"tram-front")
    def test_draw_cached_icon_and_animate(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,"dog.svg").write_bytes(SVG)
            with patch.object(icon_visuals,"ROOT",Path(folder)):
                a=Image.new("RGB",(1080,1920),(0,0,0))
                b=Image.new("RGB",(1080,1920),(0,0,0))
                self.assertTrue(icon_visuals.overlay_icon(a,{"speech":"dog"},0,(255,200,100)))
                self.assertTrue(icon_visuals.overlay_icon(b,{"speech":"dog"},1,(255,200,100)))
                self.assertIsNotNone(ImageChops.difference(a,b).getbbox())
    def test_missing_icon_is_safe(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(icon_visuals,"ROOT",Path(folder)):
                self.assertFalse(icon_visuals.overlay_icon(Image.new("RGB",(1080,1920)),
                                                          {"speech":"dog"},0,(255,255,255)))
    def test_reject_entity_svg(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,"dog.svg").write_bytes(b'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg>&x;</svg>')
            with patch.object(icon_visuals,"ROOT",Path(folder)):
                self.assertFalse(icon_visuals.overlay_icon(Image.new("RGB",(1080,1920)),
                                                          {"speech":"dog"},0,(255,255,255)))

if __name__=="__main__":
    unittest.main()
