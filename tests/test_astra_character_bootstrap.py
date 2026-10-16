import unittest
from astra_v2.character_bootstrap import register_approved_character


class CharacterBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {"version": 1, "characters": {}}
        self.candidate = {"character_approved": True, "character_id": "mira",
                          "character_name": "Mira", "format": "short"}

    def test_creates_character_without_mutating_source(self):
        result = register_approved_character(self.snapshot, self.candidate)
        self.assertEqual(result["characters"]["mira"]["revision"], 0)
        self.assertEqual(self.snapshot["characters"], {})
        self.assertEqual(register_approved_character(result, self.candidate), result)

    def test_rejects_unapproved_missing_or_conflicting_identity(self):
        for change in ({"character_approved": False}, {"character_id": ""},
                       {"character_name": ""}, {"format": "long"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                register_approved_character(self.snapshot, {**self.candidate, **change})
        existing = register_approved_character(self.snapshot, self.candidate)
        with self.assertRaises(ValueError):
            register_approved_character(existing, {**self.candidate, "character_name": "Someone Else"})


if __name__ == "__main__":
    unittest.main()
