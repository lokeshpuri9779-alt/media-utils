"""Offline checks for the manual CPU image benchmark; no model download."""
import tempfile
import unittest
from pathlib import Path

from tools.experimental_openvino_benchmark import run


class CPUImageBenchmarkTests(unittest.TestCase):
    def test_unknown_profile_rejected_before_model_import(self):
        with self.assertRaisesRegex(ValueError, "Unapproved model"):
            run(profile="some-paid-api")

    def test_step_budget_rejected_before_model_import(self):
        with self.assertRaisesRegex(ValueError, "steps"):
            run(steps=1000)

    def test_default_profile_is_bounded(self):
        from tools.experimental_openvino_benchmark import APPROVED_MODELS
        self.assertEqual(set(APPROVED_MODELS), {"preconverted", "export"})


if __name__ == "__main__":
    unittest.main()
