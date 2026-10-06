import unittest

from hyperframes_adapter import _project_html


class HyperFramesAdapterTests(unittest.TestCase):
    def test_project_is_local_deterministic_portrait(self):
        story = {"title": "Test", "genre": "space"}
        plan = [
            {
                "start": 0.0, "duration": 3.0, "voice_start": 0.08,
                "speech": "The Moon rotates around Earth.", "audio": [0] * 24000,
                "headline": "THE MOON ROTATES", "visual": "tidal_lock",
            },
            {
                "start": 3.0, "duration": 3.0, "voice_start": 3.08,
                "speech": "The same face stays pointed inward.", "audio": [0] * 24000,
                "headline": "WATCH THE MARKER", "visual": "media",
                "media_fit": "contain", "media_motion": "push",
            },
            {
                "start": 6.0, "duration": 3.0, "voice_start": 6.08,
                "speech": "That is synchronous rotation.", "audio": [0] * 24000,
                "headline": "ONE ORBIT ONE SPIN", "visual": "media",
                "comparison_labels": ["NEAR", "FAR"],
            },
        ]
        page = _project_html(story, plan, 9.0, {2: "scene-2.png", 3: "scene-3.png"})
        self.assertIn('data-width="1080"', page)
        self.assertIn('data-height="1920"', page)
        self.assertIn('src="./gsap.min.js"', page)
        self.assertIn('src="media/scene-2.png"', page)
        self.assertNotIn("http://", page)
        self.assertNotIn("https://", page)
        self.assertIn('window.__timelines["rayvan"]', page)


if __name__ == "__main__":
    unittest.main()
