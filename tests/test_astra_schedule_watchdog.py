"""Unit tests for monitor-only ASTRA schedule watchdog."""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "astra_schedule_watchdog.py"
spec = importlib.util.spec_from_file_location("astra_schedule_watchdog", SCRIPT)
module = importlib.util.module_from_spec(spec)
with patch.dict(os.environ, {"GITHUB_REPOSITORY": "example/repo"}):
    spec.loader.exec_module(module)

class WatchdogTests(TestCase):
    def test_recent_schedule_is_ok(self):
        now = dt.datetime(2026, 10, 22, 12, tzinfo=dt.timezone.utc)
        runs = [{"event": "schedule", "created_at": "2026-10-22T11:55:00Z", "html_url": "https://github.com/example/run/1", "conclusion": "success"}]
        with patch.object(module, "NOW", now), patch.object(module, "get_json", return_value={"workflow_runs": runs}), patch.dict(os.environ, {"ASTRA_WATCHDOG_MAX_GAP_MINUTES": "45", "GITHUB_STEP_SUMMARY": ""}):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(module.main(), 0)
            self.assertFalse(json.loads(out.getvalue())["alert"])

    def test_old_schedule_warns_but_does_not_fail(self):
        now = dt.datetime(2026, 10, 22, 12, tzinfo=dt.timezone.utc)
        runs = [{"event": "schedule", "created_at": "2026-10-22T10:00:00Z", "conclusion": "success"}]
        with patch.object(module, "NOW", now), patch.object(module, "get_json", return_value={"workflow_runs": runs}), patch.dict(os.environ, {"ASTRA_WATCHDOG_MAX_GAP_MINUTES": "45", "GITHUB_STEP_SUMMARY": ""}):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(module.main(), 0)
            self.assertIn('"alert": true', out.getvalue())

    def test_non_scheduled_runs_are_ignored(self):
        now = dt.datetime(2026, 10, 22, 12, tzinfo=dt.timezone.utc)
        runs = [{"event": "workflow_dispatch", "created_at": "2026-10-22T11:59:00Z"}]
        with patch.object(module, "NOW", now), patch.object(module, "get_json", return_value={"workflow_runs": runs}), patch.dict(os.environ, {"ASTRA_WATCHDOG_MAX_GAP_MINUTES": "45", "GITHUB_STEP_SUMMARY": ""}):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(module.main(), 0)
            self.assertIn('"alert": true', out.getvalue())
