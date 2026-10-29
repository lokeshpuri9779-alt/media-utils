#!/usr/bin/env python3
"""Regression tests for advisory-only ASTRA adapter."""
import unittest
from advisory_adapter import analyze

class AdvisoryTests(unittest.TestCase):
    def test_hook_and_package(self):
        result = analyze({"hook": "What happens when the last train disappears?", "title": "The Last Train Vanished", "thumbnail": "NO WAY OUT"})
        self.assertTrue(result["advisory_only"])
        self.assertFalse(result["production_ready"])
        self.assertIn("hook", result)
        self.assertIn("package", result)
        self.assertIsInstance(result["hook"]["score"], int)
        self.assertFalse(result["hook"]["quality_decision_allowed"])
        self.assertEqual(result["hook"]["interpretation"], "unvalidated_heuristic_not_quality_gate")
        self.assertFalse(result["package"]["quality_decision_allowed"])
        self.assertEqual(result["package"]["interpretation"], "unvalidated_heuristic_not_quality_gate")
    def test_empty(self):
        result = analyze({})
        self.assertNotIn("hook", result)
        self.assertNotIn("package", result)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            analyze([])
    def test_non_string(self):
        result = analyze({"hook": 2, "title": False})
        self.assertNotIn("hook", result)
        self.assertNotIn("package", result)

if __name__ == "__main__":
    unittest.main()
