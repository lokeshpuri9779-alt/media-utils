import unittest
from PIL import Image
from astra_v2.story_visuals import draw_subject

class CharacterActionRenderTests(unittest.TestCase):
    def test_action_changes_character_frame(self):
        idle=Image.new("RGB",(1080,1920),(10,10,10))
        jump=idle.copy()
        self.assertTrue(draw_subject(idle,"fox",1.1,(255,170,90),"idle"))
        self.assertTrue(draw_subject(jump,"fox",1.1,(255,170,90),"jump"))
        self.assertNotEqual(idle.tobytes(),jump.tobytes())
    def test_backward_compatible_default(self):
        image=Image.new("RGB",(1080,1920),(10,10,10))
        self.assertTrue(draw_subject(image,"owl",1.0,(255,170,90)))
if __name__=="__main__":
    unittest.main()
