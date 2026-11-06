import unittest

import numpy as np

from tools.experimental_sdxl_text_review import ENCODERS, LOCK, metrics, verify_packing


class TextReviewTests(unittest.TestCase):
    def test_guidance_branch_and_encoder_order_are_observable(self):
        records = {}
        for i, label in enumerate(('negative', 'positive')):
            for j, name in enumerate(ENCODERS):
                records[name, label] = {'sequence': np.full((1, 3, 1), i * 5 + j),
                                        'pooled': np.full((1, 1), i * 5 + j)}
        seq = np.repeat(np.array([[[0, 1]], [[5, 6]]]), 3, axis=1)
        pooled = np.array([[1], [6]])
        ids = [[1024, 1024, 0, 0, 1024, 1024]] * 2
        verify_packing(seq, pooled, ids, records)
        for wrong in (seq[::-1], seq[:, :, ::-1]):
            with self.assertRaises(AssertionError):
                verify_packing(wrong, pooled, ids, records)
        with self.assertRaises(AssertionError):
            verify_packing(seq, pooled[::-1], ids, records)

    def test_collapsed_or_invalid_conditioning_is_distinguished(self):
        zero, signal = np.zeros(3), np.array([-1, 2, 1])
        self.assertIsNone(metrics(zero, signal)['cosine'])
        self.assertEqual(metrics(zero, signal)['relative_l2'], 1)
        self.assertAlmostEqual(metrics(signal, -signal)['cosine'], -1)
        with self.assertRaises(ValueError):
            metrics(zero, np.array([np.nan] * 3))

    def test_locked_download_scope_excludes_denoiser_and_vae_weights(self):
        for backend in ('export', 'reference'):
            paths = set(LOCK[backend])
            self.assertEqual({p for p in paths if p.startswith(('vae', 'unet'))}, {'unet/config.json'})
            self.assertFalse(any(p.endswith(('.py', '.pkl', '.pt')) for p in paths))
            for name in ENCODERS:
                weight = 'model.safetensors' if backend == 'reference' else 'openvino_model.bin'
                self.assertEqual(len(LOCK[backend][f'{name}/{weight}'][1]), 64)
