import unittest
from astra_v2.object_continuity import ObjectState, plan_object_states, transition, FLOOR_Y

class ObjectContinuityTests(unittest.TestCase):
    def test_pick_carry_release_ground(self):
        shots=[{"story_action":"pick"},{"story_action":"carry"},
               {"story_action":"release"},{"story_action":"idle"}]
        states=plan_object_states(shots,object_id="parcel-1")
        self.assertEqual(states[0]["object_state_after"]["attachment"],"held")
        self.assertEqual(states[1]["object_state_before"]["holder"],"actor_0")
        self.assertEqual(states[2]["object_state_after"]["y"],FLOOR_Y)
        self.assertEqual(states[3]["object_state_after"]["attachment"],"ground")
        self.assertTrue(all(s["object_state_after"]["object_id"]=="parcel-1" for s in states))

    def test_repair_survives_payoff(self):
        shots=plan_object_states([{"story_action":"repair"},{"story_action":"dance"}],object_id="clock")
        self.assertEqual(shots[-1]["object_state_after"]["condition"],"repaired")

    def test_unrelated_prop_does_not_steal_identity(self):
        shots=plan_object_states([{"object_id":"other","story_action":"pick"}],object_id="parcel")
        self.assertEqual(shots[0]["object_state_after"]["attachment"],"ground")

    def test_open_state_persists(self):
        shots=plan_object_states([{"story_action":"open"},{"story_action":"look"}],object_id="box")
        self.assertTrue(shots[-1]["object_state_after"]["opened"])

    def test_throw_releases_holder(self):
        held=transition(ObjectState("ball"),{"story_action":"catch"})
        thrown=transition(held,{"story_action":"throw"})
        self.assertEqual(thrown.attachment,"airborne")
        self.assertIsNone(thrown.holder)

if __name__=="__main__": unittest.main()
