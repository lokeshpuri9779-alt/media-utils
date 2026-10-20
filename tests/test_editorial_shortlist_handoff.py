"""Review exports preserve drafts and reuse the existing intake contract."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from astra_v2.autonomous_story_proposals import proposal
from astra_v2.editorial_approval_manifest import story_digest
from astra_v2.editorial_approved_intake import intake_files
from astra_v2.editorial_review_packet import export_packet, shortlist_stories
from astra_v2.story_review_shortlist import shortlist


class ShortlistHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stories = [proposal(0), proposal(1)]
        # Adjacent generated proposals can share a title; exercise two selected IDs.
        for index, story in enumerate(self.stories):
            story["title"] = f"Editorial handoff CI fixture {index}"
        self.stories[0]["editorial_context"] = {"preserve_full_payload": True}
        self.write("ledger.json", {"proposals": self.stories})
        self.write("audit.json", {"proposals": [
            {"content_id": story["content_id"],
             "editorial_issues": ["human_or_model_editorial_review_required"],
             "publication_rejection": "unreviewed_causal_draft"}
            for story in self.stories
        ]})
        self.report = shortlist(self.root / "ledger.json", self.root / "audit.json",
                                self.root / "shortlist.json")
        self.write("state.json", {"published": {}, "pending": {}, "reserved": {}, "rejected": {}})
        self.write("history.json", {"stories": []})

    def write(self, name, document):
        (self.root / name).write_text(json.dumps(document), encoding="utf-8")

    def test_cli_exports_full_unchanged_drafts_with_pending_decisions(self):
        before = copy.deepcopy(self.stories)
        subprocess.run([
            sys.executable, "-m", "astra_v2.editorial_review_packet",
            "--stories", str(self.root / "ledger.json"),
            "--shortlist", str(self.root / "shortlist.json"),
            "--output", str(self.root / "packet.json"),
            "--stories-output", str(self.root / "stories.json"),
            "--reviews-output", str(self.root / "reviews.json"),
        ], check=True, capture_output=True, text=True)
        exported = json.loads((self.root / "stories.json").read_text())["stories"]
        reviews = json.loads((self.root / "reviews.json").read_text())["reviews"]
        self.assertEqual(exported, list(reversed(before)))
        self.assertEqual(self.stories, before)
        self.assertEqual(len(reviews), len(exported))
        for story, record in zip(exported, reviews):
            self.assertEqual(record["story_sha256"], story_digest(story))
            self.assertEqual(record["decision"], "pending")
            self.assertEqual(record["reviewer"], "")
            self.assertEqual(record["review_notes"], "")
            self.assertIs(story["production_ready"], False)
        result = self.intake()
        self.assertEqual(result["intake_count"], 0)
        self.assertFalse(result["publication_triggered"])
        # A rubber-stamped generated draft still fails the authored-story gate.
        for record in reviews:
            record.update(decision="approve", reviewer="ci-fixture",
                          review_notes="Synthetic negative test; no production approval")
        self.write("reviews.json", {"reviews": reviews})
        self.assertEqual(self.intake()["intake_count"], 0)

    def intake(self):
        return intake_files(self.root / "stories.json", self.root / "reviews.json",
                            self.root / "approved.json", self.root / "state.json",
                            self.root / "history.json")

    def test_stale_source_or_missing_digest_is_rejected(self):
        changed = copy.deepcopy(self.stories)
        changed[0]["editorial_context"]["preserve_full_payload"] = False
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            shortlist_stories(changed, self.report)
        report = copy.deepcopy(self.report)
        del report["review_candidates"][0]["story_sha256"]
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            shortlist_stories(self.stories, report)

    def test_unknown_duplicate_or_approved_candidates_are_rejected(self):
        variants = []
        unknown = copy.deepcopy(self.report)
        unknown["review_candidates"][0]["content_id"] = "absent"
        variants.append(unknown)
        duplicate = copy.deepcopy(self.report)
        duplicate["review_candidates"][1] = duplicate["review_candidates"][0]
        variants.append(duplicate)
        enabled = copy.deepcopy(self.report)
        enabled["publication_enabled"] = True
        variants.append(enabled)
        promoted = copy.deepcopy(self.report)
        promoted["review_candidates"][0]["production_ready"] = True
        variants.append(promoted)
        for report in variants:
            with self.subTest(report=report), self.assertRaises(ValueError):
                shortlist_stories(self.stories, report)
        duplicate_source = [self.stories[0], self.stories[0]]
        with self.assertRaisesRegex(ValueError, "duplicate source"):
            shortlist_stories(duplicate_source, self.report)

    def test_export_requires_distinct_paired_outputs(self):
        with self.assertRaises(ValueError):
            export_packet([], self.root / "packet.json", self.root / "stories.json")
        with self.assertRaises(ValueError):
            export_packet([], self.root / "packet.json", self.root / "same.json",
                          self.root / "same.json")

    def test_empty_shortlist_exports_zero_approvals(self):
        report = dict(self.report, review_candidates=[], candidate_count=0)
        stories = shortlist_stories(self.stories, report)
        packet = export_packet(stories, self.root / "packet.json",
                               self.root / "stories.json", self.root / "reviews.json")
        self.assertEqual(packet["approved_count"], 0)
        self.assertEqual(self.intake()["intake_count"], 0)


if __name__ == "__main__":
    unittest.main()
