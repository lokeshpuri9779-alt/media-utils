import tempfile
import unittest
from pathlib import Path

from astra_v2.character_storage import initialize_character, load_character
from astra_v2.character_story_context import continuity_proposal, accept_character_episode
from astra_v2.publication_quality import publication_rejection


class CharacterStoryContextTests(unittest.TestCase):
    def test_continuity_is_read_only_until_explicit_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hero.json"
            initialize_character(path, "hero", "Mira")
            first = continuity_proposal(1, path)
            self.assertEqual(load_character(path)["revision"], 0)
            self.assertTrue(publication_rejection(first))
            accept_character_episode(path, first, {
                "episode_id": first["content_id"],
                "relationships": {"Ari": "trusted friend"},
                "new_conflicts": ["lost map"],
                "decision": "asked Ari for help",
            })
            second = continuity_proposal(2, path)
            self.assertEqual(second["character_revision"], 1)
            self.assertIn("Established relationships: Ari is trusted friend", second["continuity_context"])
            self.assertIn("Still unresolved: lost map", second["continuity_context"])
            self.assertIn("Previous choice: asked Ari for help", second["continuity_context"])
            self.assertTrue(publication_rejection(second))
            with self.assertRaises(ValueError):
                accept_character_episode(path, first, {"episode_id": first["content_id"]})
            self.assertEqual(load_character(path)["revision"], 1)


if __name__ == "__main__":
    unittest.main()
