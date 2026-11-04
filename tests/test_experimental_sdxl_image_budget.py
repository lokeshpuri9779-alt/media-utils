import unittest
from tools.experimental_sdxl_load import image_budget_callback

class ImageBudgetTests(unittest.TestCase):
    def test_continuation_boundary_and_slow_stop(self):
        for times, allowed in [([34,67,100], True), ([85,169,253], False),
                               ([55,90,125], True), ([56,91,126], False)]:
            with self.subTest(times=times):
                saved = {}
                ticks = iter(times)
                payload = {'latents': object()}
                callback = image_budget_callback(
                    lambda name, data: saved.update(data), 0, lambda: next(ticks))
                for i in range(2):
                    self.assertIs(callback(None, i, None, payload), payload)
                if allowed:
                    self.assertIs(callback(None, 2, None, payload), payload)
                else:
                    with self.assertRaisesRegex(RuntimeError, 'inference_budget_exceeded'):
                        callback(None, 2, None, payload)
                self.assertEqual(saved['status'], 'continue_inference' if allowed else 'inference_budget_exceeded')
                for key in ('approved', 'published', 'production_ready'):
                    self.assertIs(saved[key], False)
