import unittest

from caption_audio_qa import _coverage, expected_narration
from videolingo_adapter import segment_for_captions


class CaptionAudioQATests(unittest.TestCase):
    def test_expected_narration_joins_rendered_scenes(self):
        report={"scenes":[{"speech":"First line."},{"speech":"Second line."}]}
        self.assertEqual(expected_narration(report),"First line. Second line.")

    def test_coverage_penalizes_missing_words(self):
        self.assertEqual(_coverage(["one","two","three"],["one","three"]),2/3)

    def test_caption_bridge_bounds_chunks(self):
        text="This is a deliberately longer sentence that should split into readable caption chunks for a vertical video."
        chunks=segment_for_captions(text,max_words=7,max_chars=42)
        self.assertTrue(chunks)
        self.assertTrue(all(len(x.split())<=7 for x in chunks))
        self.assertTrue(all(len(x)<=42 for x in chunks))

    def test_caption_chunks_keep_natural_clause_punctuation(self):
        text="The fox ran toward the river bridge, but the rabbit spotted a broken plank and waved a warning."
        chunks=segment_for_captions(text,max_words=7,max_chars=42)
        self.assertTrue(any(chunk.endswith(",") for chunk in chunks))
        self.assertEqual(" ".join(chunks),text)
        self.assertTrue(all(len(chunk.split())<=7 for chunk in chunks))
        self.assertTrue(all(len(chunk)<=42 for chunk in chunks))


if __name__=="__main__":
    unittest.main()
