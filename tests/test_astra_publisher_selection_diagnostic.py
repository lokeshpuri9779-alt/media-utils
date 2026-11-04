"""Publisher provenance diagnostics remain read-only and source-bound."""
import json
from pathlib import Path
import tempfile
import unittest

from astra_v2.publisher_selection_diagnostic import classify


class PublisherSelectionDiagnosticTests(unittest.TestCase):
    def test_preloaded_mp4_does_not_require_a_fresh_story_selection_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "astra-story-selection.log"
            path.write_text("ASTRA_PRELOAD_CONSUMED=rayvan-gemini-abc123\n"
                            'ASTRA_V2_RESULT={"outcome":"processing"}\n')
            result = classify(path, publish_step="success",
                              report={"outcome": "processing",
                                      "content_id": "rayvan-gemini-abc123"})
        self.assertEqual(result["collection_status"],
                         "not_applicable_preloaded_candidate")
        self.assertEqual(result["selection_source"], "preload_artifact")
        self.assertEqual(result["counters"], {})
        self.assertNotIn("approved", result)
        self.assertNotIn("published", result)

    def test_stale_or_other_preload_marker_cannot_explain_missing_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "astra-story-selection.log"
            path.write_text("ASTRA_PRELOAD_CONSUMED=rayvan-gemini-old-id\n")
            for report in (
                {"content_id": "rayvan-gemini-new-id"},
                {"content_id": ""},
                {},
            ):
                with self.subTest(report=report):
                    got = classify(path, publish_step="success", report=report)
                    self.assertEqual(got["collection_status"], "missing_diagnostics")
                    self.assertEqual(got["selection_source"], "unknown")

    def test_unsuccessful_step_cannot_claim_consumed_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "astra-story-selection.log"
            path.write_text("ASTRA_PRELOAD_CONSUMED=video-one\n")
            result = classify(path, publish_step="failure",
                              report={"content_id": "video-one"})
        self.assertEqual(result["collection_status"], "missing_diagnostics")
        self.assertEqual(result["selection_source"], "unknown")

    def test_actual_story_supply_counters_still_collected(self):
        expected = {"remaining": 16, "pool": 34}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "astra-story-selection.log"
            path.write_text(
                "ASTRA_STORY_SUPPLY_AFTER_HISTORY=" +
                json.dumps(expected) + "\n"
                "ASTRA_STORY_SELECTION=" +
                json.dumps({"approved": 1, "considered": 2}) + "\n"
            )
            report = classify(path, publish_step="success", report={})
        self.assertEqual(report["collection_status"], "collected")
        self.assertEqual(report["selection_source"], "fresh_candidate_evaluation")
        self.assertEqual(report["counters"]["ASTRA_STORY_SUPPLY_AFTER_HISTORY"],
                         expected)
        self.assertEqual(report["counters"]["ASTRA_STORY_SELECTION"]["approved"], 1)

    def test_skipped_publisher_does_not_invent_render_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = classify(Path(tmp) / "missing.log",
                              publish_step="skipped", report={})
        self.assertEqual(result["collection_status"],
                         "not_applicable_publisher_skipped")
        self.assertEqual(result["selection_source"], "no_render")

    def test_log_injection_or_invalid_json_cannot_fake_preloaded_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "astra-story-selection.log"
            path.write_text(
                "Fake ASTRA_PRELOAD_CONSUMED=match\n"
                "ASTRA_PRELOAD_CONSUMED=bad injected payload\n"
                "ASTRA_STORY_SELECTION={invalid-json}\n"
                'ASTRA_STORY_SELECTION=["not-an-object"]\n'
            )
            result = classify(path, publish_step="success",
                              report={"content_id": "match"})
        self.assertEqual(result["collection_status"], "missing_diagnostics")
        self.assertEqual(result["counters"], {})

    def test_oversized_log_fails_as_diagnostic_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "astra-story-selection.log"
            path.write_bytes(b"x" * 3_000_001)
            result = classify(path, publish_step="success",
                              report={"content_id": "a"})
        self.assertEqual(result["collection_status"], "unavailable_oversized_log")
        self.assertEqual(result["selection_source"], "unknown")


if __name__ == "__main__":
    unittest.main()
