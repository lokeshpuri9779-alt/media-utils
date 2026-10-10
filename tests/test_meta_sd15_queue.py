import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.meta_sd15_queue import enqueue, work_one


class SD15QueueTests(unittest.TestCase):
    def test_deduplicates_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = enqueue(root, prompt='a cinematic fox', format_name='short')
            b = enqueue(root, prompt='a cinematic fox', format_name='short')
            self.assertEqual(a, b)
            self.assertEqual(len(list((root / 'pending').glob('*.json'))), 1)

    def test_formats_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = enqueue(root, prompt='fox', format_name='short')
            b = enqueue(root, prompt='fox', format_name='long')
            self.assertNotEqual(a, b)

    def test_disabled_worker_does_not_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enqueue(root, prompt='fox')
            self.assertEqual(work_one(root)['status'], 'disabled')
            self.assertEqual(len(list((root / 'pending').glob('*.json'))), 1)

    def test_success_is_unreviewed_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enqueue(root, prompt='fox')
            def fake_generate(prompt, output, **kwargs):
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b'fake image bytes for test only')
                return {'output': str(output), 'published': False}
            with patch('integrations.meta_sd15_queue.generate', side_effect=fake_generate):
                result = work_one(root, enable_generation=True)
            self.assertEqual(result['status'], 'generated_unreviewed')
            self.assertEqual(len(list((root / 'done').glob('*.json'))), 1)

    def test_generation_failure_keeps_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enqueue(root, prompt='fox')
            with patch('integrations.meta_sd15_queue.generate', side_effect=RuntimeError('OOM')):
                result = work_one(root, enable_generation=True)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(len(list((root / 'failed').glob('*.json'))), 1)


if __name__ == '__main__':
    unittest.main()
