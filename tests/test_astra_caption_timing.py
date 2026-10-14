"""Reusable caption timing checks for narration and dialogue."""
import unittest
from astra_v2.caption_timing import build_caption_windows, active_caption


class CaptionTimingTests(unittest.TestCase):
    def test_real_word_timestamps_are_preserved(self):
        windows = build_caption_windows(
            "A duck jumps out now",
            word_times=[(1.0, 1.2), (1.2, 1.5), (1.5, 2.1),
                        (2.1, 2.3), (2.3, 2.7)],
            words_per_caption=2)
        self.assertEqual([x["text"] for x in windows],
                         ["A duck", "jumps out", "now"])
        self.assertEqual([x["start"] for x in windows], [1., 1.5, 2.3])
        self.assertEqual(active_caption(windows, 1.8), "jumps out")
        self.assertIsNone(active_caption(windows, 2.7))
        self.assertTrue(all(x["timing_source"] == "word_timestamps"
                            for x in windows))

    def test_estimated_timing_never_claims_alignment(self):
        windows = build_caption_windows(
            "This is a long and interesting story",
            start=4.0, duration=3.5, words_per_caption=3)
        self.assertEqual(windows[0]["start"], 4.0)
        self.assertEqual(windows[-1]["end"], 7.5)
        self.assertTrue(all(x["timing_source"] == "estimated_text_length"
                            for x in windows))
        self.assertEqual(" ".join(x["text"] for x in windows),
                         "This is a long and interesting story")

    def test_hindi_token_windows(self):
        windows = build_caption_windows("यह एक मजेदार कहानी है",
                                        start=0.5, duration=2.5,
                                        words_per_caption=2)
        self.assertEqual(" ".join(x["text"] for x in windows),
                         "यह एक मजेदार कहानी है")

    def test_invalid_timing_fails_closed(self):
        with self.assertRaises(ValueError):
            build_caption_windows("hello world", word_times=[(0, 1)])
        with self.assertRaises(ValueError):
            build_caption_windows("hello world", word_times=[(0, 1), (.5, 2)])
        with self.assertRaises(ValueError):
            build_caption_windows("hello world")
        self.assertEqual(build_caption_windows("  "), [])


if __name__ == "__main__":
    unittest.main()
