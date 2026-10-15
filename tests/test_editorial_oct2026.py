import unittest
from astra_v2.editorial_batch_oct2026 import PLOTS
from astra_v2.pillow_duo_scene import scene_pair

class EditorialPilotTests(unittest.TestCase):
    def test_twenty_distinct_stories_have_four_authored_scenes(self):
        self.assertEqual(len(PLOTS),20)
        self.assertEqual(len({row[0] for row in PLOTS}),20)
        self.assertEqual(len({row[1] for row in PLOTS}),20)
        self.assertEqual(sum(len(row[3]) for row in PLOTS),80)
        for key,title,genre,scenes in PLOTS:
            with self.subTest(key=key):
                self.assertEqual(len(scene_pair({"speech":title})),2)
                self.assertEqual(len(scenes),4)
                self.assertTrue(all(len(scene)==4 for scene in scenes))
                self.assertTrue(all(scene[2]=="story" for scene in scenes))
                self.assertTrue(all(len(scene[1].split())>=9 for scene in scenes))

if __name__=="__main__":
    unittest.main()
