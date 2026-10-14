"""Interaction state and timeline regression tests."""
import unittest
from experimental.scene_composer import ScenePlan,SceneObject,compose
from experimental.interaction_engine import Interaction,apply_interactions,state_at

class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.plan=ScenePlan((SceneObject("house","architecture",90,140,90),
                             SceneObject("apple","food",210,200,64)),360,300)
    def test_pickup_before_and_after(self):
        event=(Interaction(0,1,"pickup",1,1),)
        self.assertEqual(apply_interactions(self.plan,event,0).objects[1],self.plan.objects[1])
        final=apply_interactions(self.plan,event,3).objects[1]
        self.assertEqual(final.x,90)
        self.assertEqual(final.y,108.5)
        self.assertEqual(apply_interactions(self.plan,event,5).objects[1],final)
    def test_repair_persists(self):
        timeline=((0,"damage"),(2,"repair"))
        self.assertEqual(state_at("intact",timeline,1),"damaged")
        self.assertEqual(state_at("intact",timeline,3),"repaired")
        self.assertEqual(state_at("intact",timeline,9),"repaired")
    def test_open_close(self):
        self.assertEqual(state_at("closed",((1,"open"),(4,"close")),2),"open")
        self.assertEqual(state_at("closed",((1,"open"),(4,"close")),5),"closed")
    def test_interactions_render(self):
        plan=apply_interactions(self.plan,(Interaction(0,1,"pickup",0,1),),2)
        self.assertEqual(compose(plan,2).size,(360,300))
    def test_invalid(self):
        with self.assertRaises(ValueError):
            apply_interactions(self.plan,(Interaction(0,5,"pickup",0),),1)

if __name__=="__main__":
    unittest.main()
