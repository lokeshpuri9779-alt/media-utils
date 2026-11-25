"""Offline tests for natural sentence-aware narration timing."""
import unittest
from unittest.mock import patch

import numpy as np

import studio_renderer as studio


class FakeVoice:
    def __init__(self):
        self.calls = []

    def create(self, text, voice, speed, lang):
        self.calls.append((text, voice, speed, lang))
        return np.full(2400, 0.1, dtype=np.float32), studio.RATE


class StudioNarrationTests(unittest.TestCase):
    def test_sentence_segments_preserve_words_and_punctuation(self):
        text = 'A real change happened. Why did it happen? Here is what matters!'
        self.assertEqual(
            studio.narration_segments(text),
            ['A real change happened.', 'Why did it happen?', 'Here is what matters!'],
        )

    def test_sentence_split_does_not_break_abbreviations_or_decimals(self):
        text = 'Dr. Rao visited the U.S. in 2026. The value was 3.14. It worked.'
        self.assertEqual(
            studio.narration_segments(text),
            ['Dr. Rao visited the U.S. in 2026.', 'The value was 3.14.', 'It worked.'],
        )

    def test_sentence_split_keeps_initials_and_quoted_endings(self):
        text = 'A. Smith said, “It is ready.” Then it shipped.'
        self.assertEqual(
            studio.narration_segments(text),
            ['A. Smith said, “It is ready.”', 'Then it shipped.'],
        )

    def test_empty_narration_has_no_segments(self):
        self.assertEqual(studio.narration_segments('   '), [])

    def test_sentence_endings_receive_different_pause_lengths(self):
        self.assertGreater(studio._sentence_pause_seconds('Really?'),
                           studio._sentence_pause_seconds('It happened.'))
        self.assertGreater(studio._sentence_pause_seconds('Stop!'),
                           studio._sentence_pause_seconds('It happened.'))

    def test_voice_plan_synthesizes_sentences_separately_and_keeps_pauses(self):
        voice = FakeVoice()
        plan = [{'speech': 'First sentence. Second sentence?', 'min_duration': 0}]
        with patch.object(studio, 'voice_engine', return_value=voice):
            total = studio.voice_plan(plan, 'current')
        self.assertEqual([call[0] for call in voice.calls],
                         ['First sentence.', 'Second sentence?'])
        self.assertTrue(all(call[2] == 1.04 for call in voice.calls))
        expected_samples = 2400 * 2 + int(.18 * studio.RATE)
        self.assertEqual(len(plan[0]['audio']), expected_samples)
        self.assertAlmostEqual(plan[0]['duration'], expected_samples / studio.RATE + .24)
        self.assertGreater(total, 0)

    def test_empty_scene_is_rejected(self):
        with patch.object(studio, 'voice_engine', return_value=FakeVoice()):
            with self.assertRaisesRegex(RuntimeError, 'Empty narration'):
                studio.voice_plan([{'speech': ' ', 'min_duration': 0}], 'current')


if __name__ == '__main__':
    unittest.main()
