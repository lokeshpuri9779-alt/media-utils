import hashlib
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np
from tools import experimental_sdxl_load as load
from tools import experimental_sdxl_reference_image as replay


class Tensor(np.ndarray):
    def detach(self): return self
    def cpu(self): return self
    def numpy(self): return np.asarray(self)


class ReferenceImageTests(unittest.TestCase):
    def test_reference_image_requires_the_slow_single_image_gate(self):
        for entry in (load.worker, load.supervise):
            with self.assertRaisesRegex(ValueError, 'reference_image requires'):
                entry(reference_image=True)
        self.assertEqual(load.time_budget(True, False, True, True), (2400, 2700))

    def test_first_prediction_rejects_different_sample_or_latent(self):
        sample = np.zeros((2, 2), dtype=np.float32)
        digest = hashlib.sha256(sample.tobytes()).hexdigest()
        replay.validate_first(sample, 951, sample[0], sample[0], digest)
        with self.assertRaises(ValueError):
            replay.validate_first(sample + 1, 951, sample[0], sample[0], digest)
        with self.assertRaises(AssertionError):
            replay.validate_first(sample, 951, sample[0] + 1, sample[0], digest)

    def test_cached_first_prediction_then_nineteen_real_calls(self):
        tensor = lambda a: np.asarray(a).view(Tensor)
        pack = {k: np.array([[1], [2]], dtype=np.float32) for k in ('sequence','pooled','time_ids')}
        first = np.full((2,1), 99, dtype=np.float32)
        original = mock.Mock(return_value=(tensor([[3],[4]]),))
        outputs = []
        class Pipe:
            unet = SimpleNamespace(forward=original)
            scheduler = SimpleNamespace(timesteps=list(range(951, -1, -50)), init_noise_sigma=1.)
            def __call__(self, **kw):
                seq = tensor(np.concatenate([kw['negative_prompt_embeds'], kw['prompt_embeds']]))
                pooled = tensor(np.concatenate([kw['negative_pooled_prompt_embeds'], kw['pooled_prompt_embeds']]))
                for t in self.scheduler.timesteps:
                    value = self.unet.forward(tensor([0]), t, encoder_hidden_states=seq,
                        added_cond_kwargs={'text_embeds': pooled, 'time_ids': tensor(pack['time_ids'])})
                    outputs.append(value[0])
                return 'finished'
        pipe, saved = Pipe(), {}
        with mock.patch.dict(sys.modules, {'torch': SimpleNamespace(from_numpy=tensor)}), \
             mock.patch.object(replay, 'validate_first') as verify:
            self.assertEqual(replay.render(pipe, (pack, first, tensor([0])),
                lambda key,data: saved.update({key:data}), latents=tensor([0])), 'finished')
        verify.assert_called_once()
        np.testing.assert_array_equal(outputs[0], first)
        self.assertEqual(original.call_count, 19)
        self.assertIs(pipe.unet.forward, original)
        self.assertEqual(saved['reference-trajectory.json']['live_predictions_completed'], 19)
