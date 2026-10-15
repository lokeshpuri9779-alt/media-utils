"""Prevent published animals from silently turning into other species."""
import unittest
from PIL import Image, ImageChops
from astra_v2.story_visuals import select_subject, draw_subject
from astra_v2.distinct_animal_art import SPECIES

class ExactAnimalArtTests(unittest.TestCase):
    def test_story_title_selects_its_actual_species(self):
        cases=(
            ("The Heron and the Missing Moon","heron"),
            ("The Penguin and the Silent Trumpet","penguin"),
            ("The Beaver and the Floating Garden","beaver"),
            ("The Mole and the Lantern Path","mole"),
        )
        for title,expected in cases:
            with self.subTest(title=title):
                self.assertEqual(select_subject({"title":title},{"speech":"","visual":"story"}),expected)
                self.assertEqual(select_subject({"title":title},
                    {"speech":"A tree rustled beside the river.","visual":"forest"}),expected)
        self.assertEqual(select_subject({"title":"The Beaver Arrived"},
                        {"speech":"A beaver repaired the dam."}),"beaver")
        self.assertEqual(select_subject({"title":"The Mole Arrived"},
                        {"speech":"A mole searched underground."}),"mole")

    def test_distinct_silhouettes_not_other_species(self):
        backgrounds = (17,22,38)
        images={}
        for name in SPECIES+("otter","mouse"):
            image=Image.new("RGB",(1080,1920),backgrounds)
            self.assertTrue(draw_subject(image,name,.7,(133,174,212),"walk"))
            self.assertIsNotNone(ImageChops.difference(
                image,Image.new("RGB",image.size,backgrounds)).getbbox())
            images[name]=image.crop((160,500,920,1260)).tobytes()
            self.assertEqual(image.crop((0,1400,1080,1920)).tobytes(),
                             Image.new("RGB",(1080,520),backgrounds).tobytes())
        self.assertEqual(len(set(images.values())),len(images))

    def test_actual_limbs_change_frames(self):
        for name in SPECIES:
            with self.subTest(species=name):
                a=Image.new("RGB",(1080,1920),(17,22,38))
                b=a.copy()
                self.assertTrue(draw_subject(a,name,0.0,(133,174,212),"run"))
                self.assertTrue(draw_subject(b,name,.8,(133,174,212),"run"))
                self.assertIsNotNone(ImageChops.difference(a,b).getbbox())

    def test_unknown_species_stays_unrendered(self):
        im=Image.new("RGB",(1080,1920),(17,22,38))
        self.assertFalse(draw_subject(im,"imaginary-new-animal",1,(140,170,200)))

if __name__=="__main__":
    unittest.main()
