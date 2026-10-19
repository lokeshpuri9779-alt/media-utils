"""Inventory and production-safety gate for ASTRA's 4,200-candidate story expansion."""
import unittest
from PIL import Image, ImageDraw, ImageChops
from astra_v2.procedural_visual_library import (
    SPECIES, MOTIFS, CHARACTER_VARIANTS, ICON_VARIANTS,
    character_recipe, icon_recipe, icon_for_story, visual_identity, draw_icon)
from astra_v2.story_expansion_2000 import candidate_records, candidate_count
from astra_v2.publication_quality import publication_rejection

class ExpandedInventoryTests(unittest.TestCase):
    def test_exact_asset_recipe_counts_and_id_uniqueness(self):
        self.assertEqual(CHARACTER_VARIANTS, len(SPECIES)*250)
        self.assertEqual(ICON_VARIANTS, 2000)
        chars=[character_recipe(i) for i in range(CHARACTER_VARIANTS)]
        icons=[icon_recipe(i) for i in range(ICON_VARIANTS)]
        self.assertEqual(len({x["id"] for x in chars}),CHARACTER_VARIANTS)
        self.assertEqual(len({(x["species"],x["palette"],x["costume"],x["accessory"]) for x in chars}),CHARACTER_VARIANTS)
        self.assertEqual(len({(x["motif"],x["palette"],x["decoration"]) for x in icons}),2000)
        self.assertEqual(set(x["species"] for x in chars),set(SPECIES))
        self.assertEqual(set(x["motif"] for x in icons),set(MOTIFS))
        with self.assertRaises(ValueError):
            character_recipe(CHARACTER_VARIANTS)
        with self.assertRaises(ValueError):
            icon_recipe(-1)
    def test_reproducible_different_illustrations(self):
        index=icon_for_story("book","my story")
        self.assertEqual(index,icon_for_story("book","my story"))
        self.assertEqual(visual_identity("story-id","fox",0),visual_identity("story-id","fox",0))
        images=[]
        for variant in (0,25,99):
            im=Image.new("RGB",(220,220),(21,34,54))
            draw_icon(ImageDraw.Draw(im),variant,110,110,120)
            images.append(im)
        for a,b in ((0,1),(0,2),(1,2)):
            self.assertIsNotNone(ImageChops.difference(images[a],images[b]).getbbox())
    def test_each_icon_motif_is_visually_distinct_not_a_renamed_clone(self):
        import hashlib
        digests=[]
        for j,motif in enumerate(MOTIFS):
            im=Image.new("RGB",(240,240),(29,42,61))
            draw_icon(ImageDraw.Draw(im),j*100,120,120,150)
            digests.append(hashlib.sha256(im.tobytes()).hexdigest())
        self.assertEqual(len(set(digests)),len(MOTIFS))

    def test_exact_4200_causal_draft_records(self):
        plots=candidate_records()
        self.assertEqual(candidate_count(),4200)
        self.assertEqual(len(plots),4200)
        self.assertEqual(len({p[0] for p in plots}),4200)
        self.assertEqual(len({p[1] for p in plots}),4200)
        from astra_v2.story_forge import plot_fingerprint
        self.assertEqual(len({plot_fingerprint(p[3]) for p in plots}),4200)
        for key,title,genre,beats in plots:
            self.assertEqual(len(beats),4)
            self.assertTrue(all(len(x[1].split())>=9 for x in beats))
            self.assertEqual(len({x[1] for x in beats}),4)
    def test_stories_are_available_for_review_but_blocked_from_publication(self):
        from astra_v2.story_forge import catalog
        default=catalog()
        self.assertTrue(all(s["production_ready"] for s in default))
        all_review=catalog(limit=5000,include_expansion=True)
        expansion=[s for s in all_review if s["kind"]=="unreviewed_causal_draft"]
        self.assertEqual(len(expansion),4200)
        self.assertTrue(all(not s["production_ready"] for s in expansion))
        self.assertTrue(all(publication_rejection(s)=="unreviewed_causal_draft" for s in expansion))
        self.assertEqual(len({s["content_id"] for s in all_review}),len(all_review))
        excluded=catalog(limit=5000,include_expansion=True,
                         excluded_ids={expansion[0]["content_id"]})
        self.assertNotIn(expansion[0]["content_id"],{s["content_id"] for s in excluded})
    def test_real_pillow_frames_have_story_specific_costumes(self):
        from astra_v2.pillow_duo_scene import draw_duo, scene_prop
        self.assertEqual(scene_prop({"speech":"The fox and rabbit repaired the bell."}),"bell")
        shot={"speech":"The fox and rabbit carry a gift box.",
              "story_cast":("fox","rabbit"),"story_action":"carry",
              "story_visual_seed":"episode-one"}
        base=Image.new("RGB",(1080,1920),(23,35,51))
        changed=base.copy()
        self.assertTrue(draw_duo(base,shot,1.1))
        shot["story_visual_seed"]="episode-two"
        self.assertTrue(draw_duo(changed,shot,1.1))
        self.assertIsNotNone(ImageChops.difference(base,changed).getbbox())
        self.assertEqual(base.getpixel((40,1600)),(23,35,51))

if __name__=="__main__":
    unittest.main()
