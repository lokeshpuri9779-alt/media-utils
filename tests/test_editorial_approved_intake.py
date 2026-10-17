import unittest
import json
import tempfile
from pathlib import Path
from astra_v2.editorial_approved_intake import intake_files
from astra_v2.story_forge import catalog
from astra_v2.autonomous_story_proposals import proposal
from astra_v2.editorial_approval_manifest import story_digest
from astra_v2.editorial_approved_intake import approved_intake
from astra_v2.production_story_gate import candidate_issues


def record(story):
    return {"content_id": story["content_id"], "story_sha256": story_digest(story),
            "decision": "approve", "reviewer": "editor", "review_notes": "Read every beat"}


class EditorialIntakeTests(unittest.TestCase):
    def test_unreviewed_draft_never_enters_intake(self):
        draft = proposal(0)
        result = approved_intake([draft], [record(draft)])
        self.assertEqual(result["intake_count"], 0)
        self.assertFalse(result["publication_triggered"])

    def test_authored_candidate_with_valid_review_only(self):
        candidates = catalog(limit=128)
        passing = next((story for story in candidates if not candidate_issues(story)), None)
        if passing is None:
            self.skipTest("No authored candidate passes existing gates")
        result = approved_intake([passing], [record(passing)])
        self.assertEqual(result["intake_count"], 1)
        self.assertEqual(result["stories"], [passing])
        self.assertFalse(result["publication_triggered"])

    def test_stale_approval_never_enters_intake(self):
        story = catalog(limit=1)[0]
        approved = record(story)
        altered = dict(story, title=story["title"] + " changed")
        self.assertEqual(approved_intake([altered], [approved])["intake_count"], 0)

    def test_published_plot_fingerprint_blocks_intake(self):
        candidates = catalog(limit=128)
        passing = next((story for story in candidates if not candidate_issues(story)), None)
        if passing is None:
            self.skipTest("No authored candidate passes existing gates")
        history = [{"content_id": "already-published",
                    "plot_fingerprint": passing["plot_fingerprint"]}]
        result = approved_intake([passing], [record(passing)], history)
        self.assertEqual(result["intake_count"], 0)
        self.assertIn("narrative_duplicate", result["audit"]["results"][0]["issues"])

    def test_missing_persistent_history_blocks_export(self):
        story = catalog(limit=1)[0]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "stories.json").write_text(json.dumps({"stories": [story]}))
            (root / "reviews.json").write_text(json.dumps({"reviews": [record(story)]}))
            with self.assertRaises(FileNotFoundError):
                intake_files(root / "stories.json", root / "reviews.json",
                             root / "approved.json", root / "missing-state.json",
                             root / "missing-history.json")
            self.assertFalse((root / "approved.json").exists())

    def test_missing_review_fails_closed(self):
        story = catalog(limit=1)[0]
        self.assertEqual(approved_intake([story], [])["intake_count"], 0)


if __name__ == "__main__":
    unittest.main()
