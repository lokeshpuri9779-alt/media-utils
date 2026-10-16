import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.character_storage import initialize_character
from astra_v2.character_snapshot import export_snapshot, read_snapshot


class CharacterSnapshotTests(unittest.TestCase):
    def test_round_trip_multiple_characters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "a.json", root / "b.json"
            initialize_character(a, "a", "Mira")
            initialize_character(b, "b", "Ari")
            snapshot = root / "snapshot.json"
            result = export_snapshot(snapshot, [a, b])
            self.assertEqual(read_snapshot(snapshot), result)
            self.assertEqual(set(result["characters"]), {"a", "b"})

    def test_duplicate_id_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "a.json", root / "b.json"
            initialize_character(a, "a", "Mira")
            initialize_character(b, "a", "Mira")
            with self.assertRaises(ValueError):
                export_snapshot(root / "snapshot.json", [a, b])

    def test_corrupt_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(json.dumps({"version": 1, "characters": {"a": {"character_id": "b", "revision": 0}}}))
            with self.assertRaises(ValueError):
                read_snapshot(path)


if __name__ == "__main__":
    unittest.main()
