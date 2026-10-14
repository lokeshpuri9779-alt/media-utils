"""Smoke-test real Studio rendering with opt-in shared timed captions."""
import unittest
from PIL import ImageChops
import studio_renderer


class SharedStudioIntegrationTests(unittest.TestCase):
    def test_opt_in_changes_actual_frame_without_changing_default(self):
        stories = studio_renderer._story_plan({
            "genre": "fiction", "content_id": "caption-integration-smoke",
            "title": "The surprise", "topic": "A fox finds a gift",
        })
        self.assertTrue(stories)
        shot = dict(stories[0])
        shot.update({
            "start": 0.0, "end": 2.0, "duration": 2.0,
            "voice_start": 0.0,
            "audio": [0.0] * int(2 * studio_renderer.RATE),
            "experimental_cast_enabled": False,
            "experimental_shared_captions": True,
            "shared_caption_style": "dialogue",
            "speech": "The surprise arrives right now",
            "caption_word_times": [
                (0., .35), (.35, .7), (.7, 1.1), (1.1, 1.5), (1.5, 2.)
            ],
        })
        enabled = studio_renderer.render_frame([shot], .8, "fiction", 2.0)
        shot["experimental_shared_captions"] = False
        disabled = studio_renderer.render_frame([shot], .8, "fiction", 2.0)
        self.assertIsNotNone(ImageChops.difference(
            enabled.convert("RGB"), disabled.convert("RGB")).getbbox())

    def test_opt_in_has_no_captions_before_voice(self):
        from astra_v2.caption_timing import build_caption_windows, active_caption
        windows = build_caption_windows("A sudden surprise", start=1.0,
                                        duration=2.0, words_per_caption=2)
        self.assertIsNone(active_caption(windows, .5))
        self.assertIsNone(active_caption(windows, 3.0))


if __name__ == "__main__":
    unittest.main()
