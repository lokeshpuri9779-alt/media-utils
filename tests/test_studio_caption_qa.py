import unittest

from studio_renderer import caption_qa_report, _caption_chunks_for_shot


class StudioCaptionQATests(unittest.TestCase):
    def test_all_narration_words_are_covered_by_burned_in_phrases(self):
        plan = [
            {"speech": "This is the first hook. Watch what happens next."},
            {"speech": "The answer changes everything.", "director_caption_mode": "question"},
            {"speech": "Look closely at the hidden detail.", "director_caption_mode": "keyword"},
        ]
        report = caption_qa_report(plan)
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["burned_in"])
        self.assertEqual(report["covered_scenes"], 3)
        self.assertEqual(report["scene_count"], 3)
        self.assertEqual(report["covered_words"], sum(len(s["speech"].split()) for s in plan))
        self.assertGreater(report["caption_phrases"], 3)

    def test_missing_scene_speech_blocks_caption_qa(self):
        report = caption_qa_report([
            {"speech": "A valid narration beat."},
            {"speech": ""},
        ])
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["covered_scenes"], 1)
        self.assertEqual(report["failures"][0]["scene"], 2)

    def test_keyword_mode_keeps_all_words_in_the_caption_chunks(self):
        shot = {"speech": "Every word remains visible in the phrase.", "director_caption_mode": "keyword"}
        chunks = _caption_chunks_for_shot(shot)
        self.assertEqual(sum(len(chunk.split()) for chunk in chunks), len(shot["speech"].split()))
        self.assertTrue(all(len(chunk.split()) <= 3 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
