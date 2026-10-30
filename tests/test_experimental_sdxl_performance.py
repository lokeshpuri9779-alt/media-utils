import copy
import unittest
from tools.experimental_sdxl_performance import run_probe, runtime_details
from tools.experimental_sdxl_load import limit_reason, GIB

class PerformanceTests(unittest.TestCase):
    def test_optimum_list_conversion_and_latent_passthrough(self):
        latent = object()
        def pipeline(**kwargs):
            # Reproduce the pinned wrapper's unconditional list[0] access.
            for value in kwargs.values():
                if isinstance(value, list):
                    first = value[0]
            self.assertEqual(kwargs['callback_on_step_end_tensor_inputs'], ['latents'])
            for i in range(20):
                payload = {'latents': latent}
                returned = kwargs['callback_on_step_end'](None, i, 999-i, payload)
                self.assertIs(returned, payload)
                self.assertIs(returned['latents'], latent)
            self.fail('Probe must stop before decode')
        run_probe(pipeline, {'num_inference_steps': 20}, lambda *args: None)

    def test_stops_after_three_callbacks_without_decode(self):
        saved = {}
        calls = []
        def pipeline(**kwargs):
            self.assertEqual(kwargs['num_inference_steps'], 20)
            self.assertEqual(kwargs['output_type'], 'latent')
            for i in range(20):
                calls.append(i)
                kwargs['callback_on_step_end'](None, i, 999-i, {})
            self.fail('Decode/return must be unreachable')
        times = iter([0, 10, 12, 15])
        run_probe(pipeline, {'num_inference_steps': 20},
                  lambda n, d: saved.update({n: copy.deepcopy(d)}),
                  clock=lambda: next(times))
        self.assertEqual(calls, [0, 1, 2])
        r = saved['performance.json']
        self.assertEqual([x['seconds_since_previous_callback'] for x in r['steps']], [10, 2, 3])
        self.assertEqual(r['status'], 'performance_probe_complete')
        self.assertEqual(r['images_generated'], 0)
        for key in ('approved', 'published', 'production_ready'):
            self.assertIs(r[key], False)

    def test_unexpected_error_propagates(self):
        def broken(**kwargs):
            raise ValueError('real failure')
        with self.assertRaisesRegex(ValueError, 'real failure'):
            run_probe(broken, {'num_inference_steps': 20}, lambda *args: None)

    def test_missing_callbacks_fails(self):
        with self.assertRaisesRegex(RuntimeError, 'without the required early stop'):
            run_probe(lambda **kwargs: None, {'num_inference_steps': 20}, lambda *args: None)

    def test_short_deadline_keeps_memory_limits(self):
        self.assertEqual(limit_reason(GIB, 4*GIB, 451, None, 450, 450), 'inference_timeout')
        self.assertIsNone(limit_reason(GIB, 4*GIB, 450, None, 449, 450))
        self.assertEqual(limit_reason(12*GIB, 4*GIB, 1, None, 1, 450), 'rss_limit')
        self.assertEqual(limit_reason(GIB, GIB, 1, None, 1, 450), 'available_ram_limit')
