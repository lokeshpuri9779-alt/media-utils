import sys
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np
from tools import experimental_sdxl_denoiser_review as probe


class Tensor(np.ndarray):
    def clone(self): return self.copy()
    def detach(self): return self
    def cpu(self): return self
    def numpy(self): return np.asarray(self)


class DenoiserReviewTests(unittest.TestCase):
    def test_screen_rejects_each_resource_shortfall(self):
        g = probe.GIB
        self.assertFalse(probe.screen(g, 15*g, 30*g)['reasons'])
        for args, reason in [((2*g,15*g,30*g), 'insufficient_rss_headroom'),
                             ((g,12*g,30*g), 'insufficient_available_ram'),
                             ((g,15*g,10*g), 'insufficient_disk')]:
            self.assertIn(reason, probe.screen(*args)['reasons'])

    def test_corrupt_inputs_stop_before_runtime_or_weight_download(self):
        with mock.patch.object(probe, 'save'), mock.patch.object(probe, 'load_inputs', side_effect=ValueError('hash mismatch')), \
             mock.patch.object(probe, 'download_one') as download:
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                probe.worker()
            download.assert_not_called()

    def test_source_config_mismatch_is_rejected(self):
        ref = {'_class_name': 'UNet2DConditionModel', 'sample_size':128, 'cross_attention_dim':2048}
        export = {**ref, '_name_or_path': f'/models/snapshots/{probe.REFERENCE_REVISION}/unet'}
        probe.validate_configs(export, ref)
        for override in ({'sample_size':64}, {'_name_or_path':'/different/source'}):
            with self.assertRaises(ValueError):
                probe.validate_configs({**export, **override}, ref)

    def test_sequential_rows_preserve_sample_and_conditioning_order(self):
        tensor = lambda x: np.asarray(x).view(Tensor)
        sample = tensor(np.zeros((2,4,128,128), dtype=np.float32))
        pack = {key: np.array([[2], [9]], dtype=np.float32) for key in ('sequence','pooled','time_ids')}
        seen = []
        def model(x, t, encoder_hidden_states, added_cond_kwargs, return_dict):
            seen.append(float(encoder_hidden_states[0,0]))
            self.assertEqual(x.shape,(1,4,128,128))
            self.assertEqual(t, 951)
            np.testing.assert_array_equal(encoder_hidden_states, added_cond_kwargs['text_embeds'])
            np.testing.assert_array_equal(encoder_hidden_states, added_cond_kwargs['time_ids'])
            x[:] = seen[-1]  # Must not mutate the archived shared sample.
            return (x,)
        record = mock.Mock()
        value = probe.predict_rows(model, sample, 951, pack, SimpleNamespace(from_numpy=tensor), record)
        self.assertEqual(seen, [2,9])
        self.assertEqual([call.args[0] for call in record.call_args_list], ['negative','positive'])
        self.assertEqual(value.dtype,np.float32)
        np.testing.assert_array_equal(sample, 0)
        np.testing.assert_array_equal(value[:,0,0,0], [2,9])

    def test_nonfinite_prediction_is_not_recorded_as_complete(self):
        bad = np.full((1,4,128,128), np.nan, dtype=np.float32).view(Tensor)
        sample = np.zeros((2,4,128,128), dtype=np.float32).view(Tensor)
        pack = {key: np.zeros((2,1),dtype=np.float32) for key in ('sequence','pooled','time_ids')}
        callback = mock.Mock()
        with self.assertRaisesRegex(ValueError, 'Invalid FP32'):
            probe.predict_rows(lambda *a,**kw:(bad,), sample, 951, pack,
                               SimpleNamespace(from_numpy=lambda x:x), callback)
        callback.assert_not_called()
