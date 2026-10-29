"""Offline guardrails for the read-only ASTRA CPU runtime probe."""
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class CpuRuntimeProbeTests(unittest.TestCase):
    def setUp(self):
        self.probe = importlib.import_module("tools.experimental_cpu_runtime_probe")

    def test_collect_is_read_only_and_unapproved(self):
        with patch.object(self.probe, "read", return_value=None), \
             patch.object(self.probe.os, "cpu_count", return_value=2), \
             patch.object(self.probe, "cpu_model", return_value="test cpu"):
            report = self.probe.collect()
        self.assertFalse(report["approved"])
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["published"])
        self.assertEqual(report["images_generated"], 0)
        self.assertTrue(report["diagnostic_only"])
        self.assertEqual(report["logical_cpu_count"], 2)

    def test_missing_procfs_is_safe(self):
        with patch.object(self.probe, "read", return_value=None), \
             patch.object(self.probe.platform, "processor", return_value="fallback"):
            self.assertEqual(self.probe.cpu_model(), "fallback")

    def test_report_written_without_model_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(self.probe, "Path", wraps=Path), \
                 patch.object(self.probe, "collect", return_value={
                     "approved": False, "production_ready": False,
                     "published": False, "images_generated": 0}):
                # Main writes only the fixed local artifact; run in an isolated cwd.
                import os
                cwd = os.getcwd()
                try:
                    os.chdir(d)
                    self.probe.main()
                    report = json.loads(Path("artifacts/experimental-openvino/cpu-runtime-probe.json").read_text())
                finally:
                    os.chdir(cwd)
                self.assertEqual(report["images_generated"], 0)


if __name__ == "__main__":
    unittest.main()
