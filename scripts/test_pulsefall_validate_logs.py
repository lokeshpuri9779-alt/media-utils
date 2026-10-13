"""Regression tests for the validation gate itself, including false greens."""

from pathlib import Path
import contextlib
import io
import tempfile
import unittest

from pulsefall_validate_logs import SUITES, main, validate_logs


class ValidationGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pulsefall-gate-test-")
        self.addCleanup(self.temp.cleanup)
        self.logs = Path(self.temp.name)
        (self.logs / "import.log").write_text("Godot import finished\n", encoding="utf-8")
        for name, (label, checks, cycles) in SUITES.items():
            if name == "extraction-test.log":
                text = "".join(f"PASS: extraction check {i}\n" for i in range(checks))
                text += "EXTRACTION TEST FAILURES: 0\n"
            else:
                cycle_text = f" CYCLES: {cycles}" if cycles is not None else ""
                text = f"{label}: {checks}{cycle_text} FAILURES: 0\n"
            (self.logs / name).write_text(text, encoding="utf-8")

    def append(self, name, text):
        with (self.logs / name).open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")

    def test_complete_clean_evidence_passes(self):
        self.assertEqual(validate_logs(self.logs), [])
        self.assertEqual(sum(s[1] for s in SUITES.values()), 394)

    def test_every_missing_log_fails(self):
        for name in ("import.log", *SUITES):
            with self.subTest(name=name):
                path = self.logs / name
                content = path.read_text()
                path.unlink()
                self.assertTrue(validate_logs(self.logs))
                path.write_text(content)

    def test_empty_log_fails(self):
        (self.logs / "meta-progression-test.log").write_text(" \n")
        self.assertTrue(validate_logs(self.logs))

    def test_unreadable_encoding_fails(self):
        (self.logs / "meta-progression-test.log").write_bytes(b"\xff")
        self.assertTrue(validate_logs(self.logs))

    def test_generic_error_overrides_zero_failure_summary(self):
        self.append("meta-progression-test.log", "ERROR: misleading assertion message")
        self.assertTrue(validate_logs(self.logs))

    def test_script_error_overrides_zero_failure_summary(self):
        self.append("controls-test.log", "SCRIPT ERROR: Invalid call")
        self.assertTrue(validate_logs(self.logs))

    def test_leaks_fail_in_every_suite_including_import(self):
        for name in ("import.log", *SUITES):
            with self.subTest(name=name):
                path = self.logs / name
                content = path.read_text()
                self.append(name, "WARNING: 3 ObjectDB instances were leaked at exit")
                self.assertTrue(validate_logs(self.logs))
                path.write_text(content)

    def test_singular_and_resource_rid_leaks_fail(self):
        for message in (
            "WARNING: 1 ObjectDB instance was leaked at exit",
            "WARNING: 1 resource still in use at exit",
            "WARNING: RID allocations of type CanvasItem were leaked at exit",
        ):
            with self.subTest(message=message):
                path = self.logs / "meta-progression-test.log"
                content = path.read_text()
                self.append(path.name, message)
                self.assertTrue(validate_logs(self.logs))
                path.write_text(content)

    def test_corrupt_save_engine_error_is_not_blanket_allowlisted(self):
        self.append("run-checkpoint-test.log", "ERROR: Parse JSON failed. Error at line 0: Expected key")
        self.assertTrue(validate_logs(self.logs))

    def test_nonzero_failures_cannot_be_hidden_by_later_success(self):
        self.append("meta-progression-test.log", "META PROGRESSION CHECKS: 34 FAILURES: 1")
        self.assertTrue(validate_logs(self.logs))

    def test_incomplete_or_duplicate_summary_fails(self):
        path = self.logs / "controls-test.log"
        for content in ("CONTROLS CHECKS: 34 FAILURES: 0\n", "CONTROLS CHECKS: 35 FAILURES: 0\n" * 2):
            with self.subTest(content=content):
                path.write_text(content)
                self.assertTrue(validate_logs(self.logs))

    def test_shell_echo_is_not_completion_evidence(self):
        (self.logs / "controls-test.log").write_text("echo 'CONTROLS CHECKS: 35 FAILURES: 0'\n")
        self.assertTrue(validate_logs(self.logs))

    def test_incomplete_extraction_pass_records_fail(self):
        path = self.logs / "extraction-test.log"
        path.write_text(path.read_text().replace("PASS: extraction check 0\n", ""))
        self.assertTrue(validate_logs(self.logs))

    def test_soak_cycle_count_is_enforced(self):
        (self.logs / "runtime.log").write_text("RUNTIME SOAK CHECKS: 10 CYCLES: 4 FAILURES: 0\n")
        self.assertTrue(validate_logs(self.logs))

    def test_unsupported_rendering_fails(self):
        self.append("runtime.log", "WARNING: Volumetric fog is only available in Forward+")
        self.assertTrue(validate_logs(self.logs))

    def test_ansi_and_crlf_are_supported(self):
        (self.logs / "controls-test.log").write_bytes(b"\x1b[32mCONTROLS CHECKS: 35 FAILURES: 0\x1b[0m\r\n")
        self.assertEqual(validate_logs(self.logs), [])

    def test_cli_success_failure_and_usage_exit_codes(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["gate", str(self.logs)]), 0)
            self.append("controls-test.log", "ERROR: injected regression")
            self.assertEqual(main(["gate", str(self.logs)]), 1)
            self.assertEqual(main(["gate"]), 2)


if __name__ == "__main__":
    unittest.main()
