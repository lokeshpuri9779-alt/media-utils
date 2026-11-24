import unittest
from pathlib import Path
from unittest.mock import patch

from astra_v2.caption_only_renderer import caption_chunks, _fit_speed_to_duration, _verify_mp4_streams


class CaptionChunkTests(unittest.TestCase):
    def test_splits_on_sentence_boundaries(self):
        self.assertEqual(
            caption_chunks("A short first sentence. Here is another sentence."),
            ["A short first sentence.", "Here is another sentence."],
        )

    def test_caps_phrase_length(self):
        chunks = caption_chunks("One two three four five six seven eight nine ten.")
        self.assertEqual(chunks, ["One two three four five six", "seven eight nine ten."])
        self.assertTrue(all(len(chunk.split()) <= 6 for chunk in chunks))

    def test_keeps_short_question_together(self):
        self.assertEqual(caption_chunks("Would you notice?"), ["Would you notice?"])

    def test_speed_is_reduced_when_audio_is_too_short(self):
        self.assertLess(_fit_speed_to_duration(1.04, 24.0), 1.04)

    def test_speed_is_increased_when_audio_is_too_long(self):
        self.assertGreater(_fit_speed_to_duration(1.04, 44.0), 1.04)

    def test_speed_is_unchanged_inside_duration_contract(self):
        self.assertEqual(_fit_speed_to_duration(1.04, 34.0), 1.04)

    def test_speed_adjustment_stays_within_supported_bounds(self):
        self.assertEqual(_fit_speed_to_duration(1.04, 5.0), 0.75)
        self.assertEqual(_fit_speed_to_duration(1.04, 100.0), 1.25)

    def test_mp4_verification_requires_both_video_and_audio_streams(self):
        with patch("astra_v2.caption_only_renderer.get_ffmpeg_exe", return_value="ffmpeg"), \
             patch("astra_v2.caption_only_renderer.subprocess.run") as run:
            _verify_mp4_streams(Path("sample.mp4"))
        command = run.call_args.args[0]
        self.assertIn("0:v:0", command)
        self.assertIn("0:a:0", command)
        self.assertTrue(run.call_args.kwargs["check"])

    def test_empty_input(self):
        self.assertEqual(caption_chunks("   "), [])


if __name__ == "__main__":
    unittest.main()
