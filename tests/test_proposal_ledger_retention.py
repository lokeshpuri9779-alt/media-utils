import json
import tempfile
import unittest
from pathlib import Path

from astra_v2.proposal_ledger_retention import (
    DEFAULT_KEEP, MAX_KEEP, MIN_KEEP, protected_ids, trim_file, trim_ledger)


def ledger(count, **extra):
    data = {"next_index": count + 7, "supply_health": {"ok": True},
            "proposals": [{"content_id": f"p{i}", "title": f"T{i}",
                           "production_ready": False} for i in range(count)]}
    data.update(extra)
    return data


class LedgerRetentionTests(unittest.TestCase):
    def test_keeps_newest_and_preserves_order_and_other_fields(self):
        original = ledger(MIN_KEEP + 300)
        trimmed, report = trim_ledger(original, keep=MIN_KEEP)
        ids = [s["content_id"] for s in trimmed["proposals"]]
        self.assertEqual(ids, [f"p{i}" for i in range(300, MIN_KEEP + 300)])
        self.assertEqual(report, {"before": MIN_KEEP + 300, "after": MIN_KEEP,
                                  "dropped": 300, "protected_kept": 0, "keep": MIN_KEEP})
        self.assertEqual(trimmed["next_index"], original["next_index"])
        self.assertEqual(trimmed["supply_health"], {"ok": True})
        self.assertEqual(len(original["proposals"]), MIN_KEEP + 300)  # input untouched

    def test_surviving_proposals_are_unchanged_objects(self):
        original = ledger(MIN_KEEP + 5)
        trimmed, _ = trim_ledger(original, keep=MIN_KEEP)
        for story in trimmed["proposals"]:
            self.assertIs(story, original["proposals"][int(story["content_id"][1:])])

    def test_never_drops_reviewed_or_production_ready_proposals(self):
        original = ledger(MIN_KEEP + 100)
        original["proposals"][3]["production_ready"] = True
        trimmed, report = trim_ledger(original, keep=MIN_KEEP, protected={"p10"})
        ids = [s["content_id"] for s in trimmed["proposals"]]
        self.assertIn("p3", ids)
        self.assertIn("p10", ids)
        self.assertEqual(report["protected_kept"], 2)
        self.assertEqual(report["dropped"], 98)
        self.assertEqual(ids, sorted(ids, key=lambda x: int(x[1:])))  # order preserved

    def test_small_ledger_is_unchanged(self):
        trimmed, report = trim_ledger(ledger(10), keep=MIN_KEEP)
        self.assertEqual(len(trimmed["proposals"]), 10)
        self.assertEqual(report["dropped"], 0)

    def test_rejects_unsafe_keep_values_and_bad_ledgers(self):
        for bad in (0, MIN_KEEP - 1, MAX_KEEP + 1, "2000", None, 2.5):
            with self.assertRaises(ValueError):
                trim_ledger(ledger(5), keep=bad)
        for bad in ({}, {"proposals": "x"}, [], None):
            with self.assertRaises(ValueError):
                trim_ledger(bad)
        with self.assertRaises(ValueError):
            trim_ledger({"proposals": [{"content_id": "a"}, "oops"]})

    def test_protected_ids_reads_only_string_ids(self):
        self.assertEqual(protected_ids({"reviews": [
            {"content_id": "a"}, {"content_id": 5}, "x", {"decision": "pending"}]}), {"a"})
        self.assertEqual(protected_ids({}), set())
        self.assertEqual(protected_ids(None), set())

    def test_file_roundtrip_trims_in_place_and_protects_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "story_proposals.json"
            decisions = Path(tmp) / "decisions.json"
            path.write_text(json.dumps(ledger(MIN_KEEP + 50)))
            decisions.write_text(json.dumps({"reviews": [{"content_id": "p1"}]}))
            report = trim_file(path, decisions, keep=MIN_KEEP)
            written = json.loads(path.read_text())
            self.assertEqual(report["dropped"], 49)
            self.assertEqual(len(written["proposals"]), MIN_KEEP + 1)
            self.assertEqual(written["proposals"][0]["content_id"], "p1")
            self.assertEqual(written["next_index"], MIN_KEEP + 57)
            self.assertFalse(list(Path(tmp).glob("*.tmp")))

    def test_missing_decisions_file_is_allowed_and_no_rewrite_when_nothing_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "story_proposals.json"
            path.write_text(json.dumps(ledger(20)))
            before = path.read_text()
            report = trim_file(path, Path(tmp) / "absent.json")
            self.assertEqual(report["dropped"], 0)
            self.assertEqual(path.read_text(), before)

    def test_default_keep_is_within_bounds(self):
        self.assertTrue(MIN_KEEP <= DEFAULT_KEEP <= MAX_KEEP)


if __name__ == "__main__":
    unittest.main()
