"""No-model checks for the denoising/decode memory handoff."""
import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np
from tools import experimental_sdxl_load as sdxl


class DecodeMemoryTests(unittest.TestCase):
    def setUp(self):
        process = mock.Mock()
        process.memory_info.return_value = SimpleNamespace(rss=sdxl.GIB)
        self.psutil = SimpleNamespace(Process=mock.Mock(return_value=process),
                                      NoSuchProcess=ProcessLookupError)
        patcher = mock.patch.dict(sys.modules, {'psutil': self.psutil})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_cleanup_only_after_twenty_steps_and_preserves_latents(self):
        hook = mock.Mock()
        ticks = iter(range(1, 21))
        saved = {}
        callback = sdxl.image_budget_callback(
            lambda name, data: saved.update({name: data}), 0, lambda: next(ticks),
            on_denoised=hook)
        pipeline = object()
        payload = {'latents': object()}
        for index in range(19):
            self.assertIs(callback(pipeline, index, None, payload), payload)
        hook.assert_not_called()
        self.assertIs(callback(pipeline, 19, None, payload), payload)
        hook.assert_called_once_with(pipeline, payload['latents'])
        self.assertEqual(saved['denoising.json']['completed_steps'], 20)

    def test_checkpoint_is_exact_and_decoder_is_not_released(self):
        array = np.arange(4 * 128 * 128, dtype=np.float32).reshape(1, 4, 128, 128)
        latent = mock.Mock()
        latent.detach.return_value.cpu.return_value.numpy.return_value = array
        names = ('unet', 'text_encoder', 'text_encoder_2', 'vae_encoder', 'vae_decoder')
        parts = {name: mock.Mock() for name in names}
        pipeline = SimpleNamespace(**parts)
        with TemporaryDirectory() as tmp, mock.patch.object(sdxl, 'OUT', Path(tmp)):
            sdxl.prepare_decode(pipeline, latent)
            np.testing.assert_array_equal(np.load(Path(tmp, 'denoised-latents.npy'), allow_pickle=False), array)
            metadata = json.loads(Path(tmp, 'denoised-latents.json').read_text())
            self.assertEqual(metadata['sha256'], hashlib.sha256(Path(tmp, metadata['file']).read_bytes()).hexdigest())
            self.assertEqual(metadata['scaling'], 'raw_scheduler_output_unscaled')
            self.assertEqual(metadata['images_generated'], 0)
            for key in ('approved', 'production_ready', 'published'):
                self.assertIs(metadata[key], False)
            self.assertIs(metadata['manual_visual_review_required'], True)
            self.assertEqual(json.loads(Path(tmp, 'stage.json').read_text())['stage'], 'decode')
            self.assertFalse(list(Path(tmp).glob('*.png')))
            self.assertFalse(list(Path(tmp).glob('*.tmp')))
        for name in names[:-1]:
            parts[name].clear_requests.assert_called_once_with()
        parts['vae_decoder'].clear_requests.assert_not_called()

    def test_cleanup_failure_preserves_checkpoint_and_propagates(self):
        latent = mock.Mock()
        latent.detach.return_value.cpu.return_value.numpy.return_value = np.zeros((1, 4, 128, 128), dtype=np.float32)
        pipeline = SimpleNamespace(unet=mock.Mock())
        pipeline.unet.clear_requests.side_effect = RuntimeError('cleanup failed')
        with TemporaryDirectory() as tmp, mock.patch.object(sdxl, 'OUT', Path(tmp)):
            with self.assertRaisesRegex(RuntimeError, 'cleanup failed'):
                sdxl.prepare_decode(pipeline, latent)
            self.assertTrue(Path(tmp, 'denoised-latents.json').exists())
            self.assertFalse(Path(tmp, 'image-review.json').exists())

    def test_supervisor_decode_uses_original_inference_deadline(self):
        process = mock.Mock(pid=123, poll=mock.Mock(side_effect=[None, None]),
                            wait=mock.Mock(return_value=-9))
        root = mock.Mock()
        root.children.return_value = []
        root.is_running.return_value = True
        root.memory_info.return_value = SimpleNamespace(rss=sdxl.GIB)
        def start(*args, **kwargs):
            sdxl.stage('inference')
            return process
        def advance(*args):
            sdxl.stage('decode')
        with TemporaryDirectory() as tmp, \
             mock.patch.object(sdxl, 'OUT', Path(tmp)), \
             mock.patch.object(sdxl.subprocess, 'Popen', side_effect=start), \
             mock.patch.object(self.psutil, 'Process', return_value=root), \
             mock.patch.object(sdxl, 'available_memory', return_value=5 * sdxl.GIB), \
             mock.patch.object(sdxl.time, 'monotonic', side_effect=[0, 10, 10, 910, 911]), \
             mock.patch.object(sdxl.time, 'sleep', side_effect=advance), \
             mock.patch.object(sdxl.os, 'killpg') as kill, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sdxl.supervise(one_image=True), 1)
            report = json.loads(Path(tmp, 'report.json').read_text())
            self.assertEqual(report['status'], 'inference_timeout')
            self.assertEqual(report['images_generated'], 0)
            self.assertIn('decode', report['peak_rss_bytes_by_stage'])
            kill.assert_called_once_with(123, sdxl.signal.SIGKILL)


if __name__ == '__main__':
    unittest.main()
