"""Offline checks for the explicitly selected longer single-image review."""
import unittest
from tools import experimental_sdxl_load as sdxl


class SlowReviewTests(unittest.TestCase):
    def test_default_budgets_are_unchanged(self):
        self.assertEqual(sdxl.time_budget(), (900, 1200))
        self.assertEqual(sdxl.time_budget(one_image=True), (900, 1200))
        self.assertEqual(sdxl.time_budget(performance_probe=True), (450, 1200))
        self.assertEqual(sdxl.time_budget(one_image=True, slow_review=True), (2400, 2700))

    def test_invalid_slow_modes_fail_before_download_or_supervision(self):
        for options in ({'slow_review': True},
                        {'slow_review': True, 'performance_probe': True},
                        {'slow_review': True, 'performance_probe': True, 'one_image': True}):
            for entry in (sdxl.worker, sdxl.supervise):
                with self.subTest(options=options, entry=entry.__name__):
                    with self.assertRaisesRegex(ValueError, 'slow_review requires'):
                        entry(**options)

    def test_observed_slow_runner_can_continue_all_twenty_callbacks(self):
        # Run 41838601016: same observed intervals, only the timebox differs.
        times = [95.038789442, 188.091240107, 282.422648859]
        times += [times[-1] + 94.331408752 * n for n in range(1, 18)]
        ticks = iter(times)
        saved = []
        callback = sdxl.image_budget_callback(
            lambda name, data: saved.append(data), 0, lambda: next(ticks),
            inference_limit=2400)
        payload = {'latents': object()}
        for index in range(20):
            self.assertIs(callback(None, index, None, payload), payload)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]['status'], 'continue_inference')
        self.assertAlmostEqual(saved[0]['projected_total_seconds'], 2066.056597643)
        for key in ('approved', 'published', 'production_ready'):
            self.assertIs(saved[0][key], False)
        self.assertIs(saved[0]['manual_visual_review_required'], True)

    def test_slow_review_still_rejects_over_budget(self):
        for times, allowed in (([130, 240, 350], True), ([131, 241, 351], False)):
            with self.subTest(times=times):
                ticks = iter(times)
                saved = {}
                callback = sdxl.image_budget_callback(
                    lambda name, data: saved.update(data), 0, lambda: next(ticks),
                    inference_limit=2400)
                payload = {'latents': object()}
                for index in range(2):
                    self.assertIs(callback(None, index, None, payload), payload)
                if allowed:
                    self.assertIs(callback(None, 2, None, payload), payload)
                else:
                    with self.assertRaisesRegex(RuntimeError, 'inference_budget_exceeded'):
                        callback(None, 2, None, payload)
                self.assertEqual(saved['inference_limit_seconds'], 2400)
                self.assertEqual(saved['status'], 'continue_inference' if allowed else 'inference_budget_exceeded')

    def test_supervisor_enforces_slow_timebox_and_original_memory_limits(self):
        def reason(rss=1, available=5, elapsed=1, load=None, inference=None):
            return sdxl.limit_reason(rss * sdxl.GIB, available * sdxl.GIB,
                                    elapsed, load, inference,
                                    inference_limit=2400, overall_limit=2700)
        self.assertIsNone(reason(elapsed=2399, inference=2399))
        self.assertEqual(reason(inference=2400), 'inference_timeout')
        self.assertEqual(reason(elapsed=2700), 'overall_timeout')
        self.assertEqual(reason(rss=12), 'rss_limit')
        self.assertEqual(reason(available=1), 'available_ram_limit')
        self.assertEqual(reason(load=600), 'load_compile_timeout')


if __name__ == '__main__':
    unittest.main()
