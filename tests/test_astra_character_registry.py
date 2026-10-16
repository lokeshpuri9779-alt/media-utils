import unittest
from astra_v2.character_registry import initial_character, apply_episode


class CharacterRegistryTests(unittest.TestCase):
    def test_episodes_carry_relationships_and_conflicts(self):
        original = initial_character("hero-1", "Mira")
        first = apply_episode(original, {
            "episode_id": "ep-1", "relationships": {"Ari": "new friend"},
            "new_conflicts": ["afraid to lead"], "decision": "asked Ari for help",
        }, 0)
        second = apply_episode(first, {
            "episode_id": "ep-2", "relationships": {"Ari": "trusted teammate"},
            "resolve_conflicts": ["afraid to lead"], "decision": "led the rescue",
        }, 1)
        self.assertEqual(original["revision"], 0)
        self.assertEqual(second["revision"], 2)
        self.assertEqual(second["episode_ids"], ["ep-1", "ep-2"])
        self.assertEqual(second["relationships"]["Ari"], "trusted teammate")
        self.assertEqual(second["unresolved_conflicts"], [])
        self.assertEqual(len(second["decisions"]), 2)

    def test_rejects_stale_and_duplicate_episode(self):
        state = initial_character("hero-1", "Mira")
        updated = apply_episode(state, {"episode_id": "ep-1"}, 0)
        with self.assertRaises(ValueError):
            apply_episode(updated, {"episode_id": "ep-2"}, 0)
        with self.assertRaises(ValueError):
            apply_episode(updated, {"episode_id": "ep-1"}, 1)

    def test_rejects_unknown_conflict_without_mutation(self):
        state = initial_character("hero-1", "Mira")
        with self.assertRaises(ValueError):
            apply_episode(state, {"episode_id": "ep-1", "resolve_conflicts": ["never opened"]}, 0)
        self.assertEqual(state["revision"], 0)


if __name__ == "__main__":
    unittest.main()
