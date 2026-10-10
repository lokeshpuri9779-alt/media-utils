"""Offline SD1.5 queue safety smoke test; requires only Python standard library.
Run: python -m unittest tests.test_meta_sd15_queue_smoke
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.meta_sd15_queue import enqueue, work_one


class Smoke(unittest.TestCase):
    def test_worker_lock_blocks_second_worker(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            enqueue(root, prompt='a robot')
            (root / '.worker_lock').mkdir()
            self.assertEqual(work_one(root, enable_generation=True)['status'], 'busy')
            self.assertEqual(len(list((root / 'pending').glob('*.json'))), 1)

    def test_failed_request_not_requeued(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            first = enqueue(root, prompt='a robot')
            with patch('integrations.meta_sd15_queue.generate', side_effect=RuntimeError('OOM')):
                self.assertEqual(work_one(root, enable_generation=True)['status'], 'failed')
            second = enqueue(root, prompt='a robot')
            self.assertEqual(first, second)
            self.assertEqual(len(list((root / 'pending').glob('*.json'))), 0)

    def test_disabled_does_not_claim(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            enqueue(root, prompt='a robot')
            self.assertEqual(work_one(root)['status'], 'disabled')


if __name__ == '__main__':
    unittest.main()
