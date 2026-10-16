import tempfile
import unittest
from pathlib import Path
from astra_v2.character_storage import initialize_character, load_character, record_episode, save_character


class CharacterStorageTests(unittest.TestCase):
    def test_round_trip_and_stale_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "characters" / "hero.json"
            original = initialize_character(path, "hero", "Mira")
            self.assertEqual(load_character(path), original)
            updated = record_episode(path, {"episode_id": "ep-1", "decision": "asked for help"}, 0)
            self.assertEqual(load_character(path), updated)
            with self.assertRaises(ValueError):
                record_episode(path, {"episode_id": "ep-2"}, 0)
            with self.assertRaises(ValueError):
                save_character(path, original, 0)
            self.assertEqual(load_character(path), updated)

    def test_cannot_initialize_existing_character(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hero.json"
            initialize_character(path, "hero", "Mira")
            with self.assertRaises(ValueError):
                initialize_character(path, "hero", "Different")


if __name__ == "__main__":
    unittest.main()
