from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import numpy as np
from tools import experimental_sdxl_first_prediction as probe


class FirstPredictionTests(unittest.TestCase):
    def test_guidance_uses_negative_then_positive_and_preserves_rows(self):
        raw = np.array([[10, -3], [12, -5]], dtype=np.float32)
        values = probe.branches(raw)
        np.testing.assert_array_equal(values['prompt_residual'], [2, -2])
        np.testing.assert_array_equal(values['guided'], [25, -18])
        np.testing.assert_array_equal(raw, [[10, -3], [12, -5]])
        with self.assertRaises(ValueError):
            probe.branches(raw[:1])

    def test_altered_pack_stops_before_denoiser_download(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'export-inputs.npz').write_bytes(b'altered')
            with mock.patch.object(probe, 'SOURCE', root), mock.patch.object(probe, 'OUT', root), \
                 mock.patch.object(probe, 'download_one') as download:
                with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    probe.worker()
                download.assert_not_called()
