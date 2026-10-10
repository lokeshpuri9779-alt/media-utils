"""Deterministic tests for CPU feasibility checks (no runner, GPU or network needed)."""
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.meta_cpu_feasibility import assess, available_memory_gib


class CpuFeasibilityTests(unittest.TestCase):
    def test_rejects_insufficient_ram(self):
        with patch('tools.meta_cpu_feasibility.available_memory_gib', return_value=3.0), \
             patch('tools.meta_cpu_feasibility.shutil.disk_usage') as disk:
            disk.return_value.free = 40 * 1024 ** 3
            result = assess(required_ram_gib=12, required_disk_gib=12)
        self.assertFalse(result['resource_check_passed'])
        self.assertFalse(result['generation_verified'])
        self.assertIn('Insufficient RAM', result['blockers'][0])

    def test_rejects_insufficient_disk(self):
        with patch('tools.meta_cpu_feasibility.available_memory_gib', return_value=24), \
             patch('tools.meta_cpu_feasibility.shutil.disk_usage') as disk:
            disk.return_value.free = 2 * 1024 ** 3
            result = assess(required_ram_gib=12, required_disk_gib=12)
        self.assertFalse(result['resource_check_passed'])

    def test_pass_is_not_generation_verification(self):
        with patch('tools.meta_cpu_feasibility.available_memory_gib', return_value=24), \
             patch('tools.meta_cpu_feasibility.shutil.disk_usage') as disk:
            disk.return_value.free = 40 * 1024 ** 3
            result = assess(required_ram_gib=12, required_disk_gib=12)
        self.assertTrue(result['resource_check_passed'])
        self.assertFalse(result['generation_verified'])

    def test_invalid_requirements(self):
        with self.assertRaises(ValueError):
            assess(required_ram_gib=0)


if __name__ == '__main__':
    unittest.main()
