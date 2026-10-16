import unittest
from astra_v2.character_registry import initial_character
from astra_v2.character_manifest_bridge import build_character_manifests


class CharacterManifestBridgeTests(unittest.TestCase):
    def setUp(self):
        self.state = initial_character("mira", "Mira")
        self.candidate = {"content_id": "short-1", "character_id": "mira",
                          "character_approved": True, "format": "short",
                          "character_episode": {"episode_id": "short-1", "decision": "helped a friend"}}

    def test_approved_explicit_character(self):
        proposal, episode = build_character_manifests(self.candidate, self.state)
        self.assertEqual(proposal["character_revision"], 0)
        self.assertEqual(episode["episode_id"], "short-1")

    def test_fail_closed_on_missing_approval_or_identity(self):
        for change in ({"character_approved": False}, {"character_id": "other"},
                       {"character_episode": {"episode_id": "other"}},
                       {"format": "long"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                build_character_manifests({**self.candidate, **change}, self.state)

    def test_rejects_unknown_fields(self):
        candidate = {**self.candidate, "character_episode": {"episode_id": "short-1", "invented": True}}
        with self.assertRaises(ValueError):
            build_character_manifests(candidate, self.state)


if __name__ == "__main__":
    unittest.main()
