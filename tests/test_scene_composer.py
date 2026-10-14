"""Scene composer batch regression tests."""
import unittest
from experimental.scene_composer import ScenePlan,SceneObject,compose,sample_plan

class SceneComposerTests(unittest.TestCase):
    def test_deterministic(self):
        p=sample_plan()
        self.assertEqual(compose(p,1).tobytes(),compose(p,1).tobytes())
    def test_motion_changes_frames(self):
        p=sample_plan()
        self.assertNotEqual(compose(p,0).tobytes(),compose(p,1).tobytes())
    def test_every_action(self):
        for action in ("idle","float","bounce","sway","spin","pulse","slide"):
            p=ScenePlan((SceneObject("sun","nature",100,120,64,action),),192,256)
            self.assertEqual(compose(p,.4).size,(192,256))
    def test_generic_category_fallback(self):
        p=ScenePlan((SceneObject("dog","animals",90,90,64),),192,256)
        self.assertEqual(compose(p,0).size,(192,256))
    def test_invalid_action(self):
        with self.assertRaises(ValueError):
            compose(ScenePlan((SceneObject("apple","food",90,90,64,"teleport"),)),0)

if __name__=="__main__":
    unittest.main()
