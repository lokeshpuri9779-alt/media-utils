"""Offline integrity, single-decode and resource-boundary checks."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np
from tools import experimental_sdxl_decode_review as review


class DecodeReviewTests(unittest.TestCase):
    def test_bad_source_stops_before_model_download(self):
        with TemporaryDirectory() as tmp, mock.patch.object(review, 'SOURCE', Path(tmp)), \
             mock.patch.object(review, 'OUT', Path(tmp) / 'out'), \
             mock.patch.object(review, 'download_one') as download:
            Path(tmp, 'denoised-latents.npy').write_bytes(b'corrupt checkpoint')
            with self.assertRaisesRegex(ValueError, 'Source hash mismatch'):
                review.worker()
            download.assert_not_called()

    def test_invalid_latents_never_reach_decoder(self):
        vae = mock.Mock()
        arrays = [np.zeros((1, 4, 64, 64), np.float32), np.zeros((1, 4, 128, 128), np.float64),
                  np.full((1, 4, 128, 128), np.nan, np.float32)]
        for array in arrays:
            with self.subTest(shape=array.shape, dtype=array.dtype), self.assertRaises(ValueError):
                review.decode_latents(vae, array, mock.Mock())
        vae.decode.assert_not_called()

    def test_decode_scales_once_preserves_source_and_does_not_retry(self):
        array = np.full((1, 4, 128, 128), 0.2605, np.float32)
        original = array.copy()
        torch = SimpleNamespace(inference_mode=contextlib.nullcontext, from_numpy=lambda x: x)
        vae = mock.Mock()
        vae.decode.return_value = ('decoded',)
        self.assertEqual(review.decode_latents(vae, array, torch), 'decoded')
        np.testing.assert_allclose(vae.decode.call_args.args[0], 2.0)
        np.testing.assert_array_equal(array, original)
        self.assertEqual(vae.decode.call_args.kwargs, {'return_dict': False})
        vae.decode.reset_mock(side_effect=True)
        vae.decode.side_effect = RuntimeError('decode failed')
        with self.assertRaisesRegex(RuntimeError, 'decode failed'):
            review.decode_latents(vae, array, torch)
        self.assertEqual(vae.decode.call_count, 1)

    def test_mismatched_reference_is_rejected(self):
        reference = {key: None for key in review.CONFIG_KEYS}
        reference.update(_class_name='AutoencoderKL', scaling_factor=review.SCALE,
                         sample_size=1024, latent_channels=4)
        exported = {**reference, '_name_or_path':
            f'/models--stabilityai--stable-diffusion-xl-base-1.0/snapshots/{review.REFERENCE_REVISION}/vae'}
        review.validate_configs(exported, reference)
        for changed in ({'scaling_factor': 0.18215}, {'latent_channels': 8},
                        {'latents_mean': [0, 0, 0, 0]}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                review.validate_configs(exported, {**reference, **changed})
        with self.assertRaisesRegex(ValueError, 'pinned reference'):
            review.validate_configs({**exported, '_name_or_path': '/different/model'}, reference)

    def test_download_integrity_failure_leaves_no_model(self):
        payload = b'wrong'
        with TemporaryDirectory() as tmp, mock.patch.object(review, 'ROOT', Path(tmp)), \
             mock.patch.object(review.urllib.request, 'urlopen', return_value=io.BytesIO(payload)):
            item = ('model', 'revision', 'vae/weights', 'vae/weights', len(payload), '0' * 64)
            with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
                review.download_one(item)
            self.assertFalse(Path(tmp, 'vae/weights').exists())
            self.assertFalse(list(Path(tmp).rglob('*.tmp')))

    def test_review_metadata_cannot_enable_approval(self):
        with TemporaryDirectory() as tmp, mock.patch.object(review, 'OUT', Path(tmp)):
            review.save('test.json', {'approved': True, 'production_ready': True,
                                     'published': True, 'manual_visual_review_required': False})
            result = json.loads(Path(tmp, 'test.json').read_text())
            for key in ('approved', 'production_ready', 'published'):
                self.assertIs(result[key], False)
            self.assertIs(result['manual_visual_review_required'], True)

    def test_existing_output_is_not_reused(self):
        with TemporaryDirectory() as tmp, mock.patch.object(review, 'OUT', Path(tmp)), \
             mock.patch.dict(sys.modules, {'psutil': mock.Mock()}), \
             mock.patch.object(review.subprocess, 'Popen') as spawn:
            Path(tmp, 'old.png').write_bytes(b'old')
            with self.assertRaisesRegex(RuntimeError, 'prior attempt'):
                review.supervise()
            spawn.assert_not_called()

    def test_supervisor_kills_decode_at_existing_deadline(self):
        process = mock.Mock(pid=123, poll=mock.Mock(side_effect=[None, None]),
                            wait=mock.Mock(return_value=-9))
        root = mock.Mock()
        root.children.return_value = []
        root.is_running.return_value = True
        root.memory_info.return_value = SimpleNamespace(rss=review.GIB)
        psutil = SimpleNamespace(Process=mock.Mock(return_value=root), NoSuchProcess=ProcessLookupError)
        def start(*args, **kwargs):
            review.stage('decode')
            return process
        with TemporaryDirectory() as tmp, mock.patch.object(review, 'OUT', Path(tmp)), \
             mock.patch.dict(sys.modules, {'psutil': psutil}), \
             mock.patch.object(review.subprocess, 'Popen', side_effect=start) as spawn, \
             mock.patch.object(review, 'available_memory', return_value=5 * review.GIB), \
             mock.patch.object(review.time, 'monotonic', side_effect=[0, 10, 910, 911]), \
             mock.patch.object(review.time, 'sleep'), mock.patch.object(review.os, 'killpg') as kill, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.supervise(), 1)
            result = json.loads(Path(tmp, 'report.json').read_text())
            self.assertEqual(result['status'], 'inference_timeout')
            self.assertEqual(result['denoising_steps_executed'], 0)
            self.assertEqual(result['images_generated'], 0)
            self.assertEqual(result['limits']['rss_bytes'], 12 * review.GIB)
            self.assertEqual(spawn.call_args.args[0],
                [sys.executable, '-m', 'tools.experimental_sdxl_decode_review', '--worker'])
            kill.assert_called_once_with(123, review.signal.SIGKILL)


if __name__ == '__main__':
    unittest.main()
