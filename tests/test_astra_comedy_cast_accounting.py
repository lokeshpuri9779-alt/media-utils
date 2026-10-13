"""Guard against reporting a two-actor pilot as one unique character."""
import unittest
from astra_v2.coordinated_development import build_comedy_demo, verify_story_cast


class ComedyCastAccountingTests(unittest.TestCase):
    def test_two_distinct_actors_in_every_scene(self):
        plan = build_comedy_demo()
        self.assertTrue(verify_story_cast(plan))
        self.assertEqual(len(plan["scenes"]), 5)
        identities = set()
        for scene in plan["scenes"]:
            self.assertEqual({a["subject"] for a in scene["actors"]}, {"fox", "rabbit"})
            self.assertEqual(len({a["character_id"] for a in scene["actors"]}), 2)
            identities.update(a["character_id"] for a in scene["actors"])
        self.assertEqual(len(identities), 2)


if __name__ == "__main__":
    unittest.main()
