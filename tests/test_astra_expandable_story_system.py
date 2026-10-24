import json
import tempfile
import unittest
from pathlib import Path
from astra_v2.expandable_story_system import (
    NoveltyStore, candidate_briefs, load_families, reserve_unique_candidates,
)


class ExpandableStoryTests(unittest.TestCase):
    def test_custom_family_added_without_code_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "new.json").write_text(json.dumps({
                "name": "courtroom", "beat_roles": ["accusation", "evidence", "verdict"]
            }))
            self.assertIn("courtroom", load_families(directory))

    def test_persistent_exact_novelty(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory, "novelty.sqlite")
            store = NoveltyStore(db)
            concept = dict(family="mystery", setting="railway", protagonist="fox",
                           goal="recover parcel", conflict="storm", twist="false clue")
            self.assertTrue(store.reserve(concept))
            store.close()
            reopened = NoveltyStore(db)
            self.assertFalse(reopened.reserve(concept))
            reopened.close()

    def test_long_form_chapters_and_draft_safeguards(self):
        families = load_families()
        item = next(candidate_briefs("seed", 1, families=families,
                    settings=["railway"], protagonists=["fox"],
                    goals=["recover parcel"], conflicts=["storm"],
                    twists=["false clue"], format="long", chapters=8))
        self.assertEqual(len(item["chapters"]), 8)
        self.assertFalse(item["editorial_approved"])
        self.assertFalse(item["asset_verified"])

    def test_deterministic_and_deduplicated(self):
        families = load_families()
        args = dict(families=families, settings=["railway"], protagonists=["fox"],
                    goals=["recover parcel"], conflicts=["storm"], twists=["false clue"])
        a = list(candidate_briefs("seed", 30, **args))
        self.assertEqual(a, list(candidate_briefs("seed", 30, **args)))
        with tempfile.TemporaryDirectory() as directory:
            store = NoveltyStore(Path(directory, "novelty.sqlite"))
            unique = list(reserve_unique_candidates(store, a))
            self.assertLessEqual(len(unique), len(families))
            self.assertTrue(unique)
            store.close()


if __name__ == "__main__":
    unittest.main()
