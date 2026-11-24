import unittest

from astra_v2.caption_only_renderer import caption_chunks


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

    def test_empty_input(self):
        self.assertEqual(caption_chunks("   "), [])


if __name__ == "__main__":
    unittest.main()
