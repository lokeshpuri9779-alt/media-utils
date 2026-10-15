"""Confirm Studio's real frame compositor invokes Pillow for a named pair."""
import unittest
from unittest.mock import patch
import numpy as np
from studio_renderer import render_frame, RATE
from astra_v2.pillow_duo_scene import draw_duo

class PillowStudioHookTests(unittest.TestCase):
    def test_fiction_duo_uses_actual_studio_frame_path(self):
        shot = {"start": 0.0, "end": 2.4, "duration": 2.4,
                "voice_start": .08, "audio": np.zeros(RATE, dtype=np.float32),
                "speech": "The fox and rabbit carry a gift box.",
                "headline": "The surprise delivery",
                "visual": "story", "story_subject": "fox",
                "story_cast": ("fox", "rabbit"), "story_action": "carry",
                "director_camera": "still", "creative_format": "microfiction_cinematic"}
        with patch("astra_v2.pillow_duo_scene.draw_duo", wraps=draw_duo) as spy:
            frame = render_frame([shot], 1.3, "fiction", 2.4)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(frame.size, (1080, 1920))
        self.assertEqual(frame.mode, "RGB")
    def test_strict_mode_rejects_unsupported_duo(self):
        from studio_renderer import CreativeReject
        shot = {"start": 0.0, "end": 2.4, "duration": 2.4,
                "voice_start": .08, "audio": np.zeros(RATE, dtype=np.float32),
                "speech": "A lone fox enters the doorway.",
                "headline": "A lonely fox", "label": "A lonely fox", "visual": "story",
                "director_camera": "still", "creative_format": "microfiction_cinematic"}
        with patch.dict("os.environ", {"ASTRA_PILLOW_DUO_STRICT": "1", "ASTRA_STUDIO_PILLOW_DUO": "1"}):
            with self.assertRaisesRegex(CreativeReject, "Pillow Duo cannot represent"):
                render_frame([shot], 1.3, "fiction", 2.4)

    def test_default_mode_preserves_legacy_fallback(self):
        shot = {"start": 0.0, "end": 2.4, "duration": 2.4,
                "voice_start": .08, "audio": np.zeros(RATE, dtype=np.float32),
                "speech": "A lone fox enters the doorway.",
                "headline": "A lonely fox", "label": "A lonely fox", "visual": "story",
                "director_camera": "still", "creative_format": "microfiction_cinematic"}
        with patch.dict("os.environ", {"ASTRA_PILLOW_DUO_STRICT": "0", "ASTRA_STUDIO_PILLOW_DUO": "1"}):
            frame = render_frame([shot], 1.3, "fiction", 2.4)
        self.assertEqual(frame.size, (1080, 1920))

if __name__ == "__main__":
    unittest.main()
