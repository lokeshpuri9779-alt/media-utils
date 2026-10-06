import unittest

import faster_whisper_adapter


class FasterWhisperAdapterTests(unittest.TestCase):
    def test_import_does_not_require_model(self):
        info = faster_whisper_adapter.backend_info()
        self.assertEqual(info["engine"], "SYSTRAN/faster-whisper")
        self.assertFalse(info["model_download_on_import"])

    def test_missing_audio_fails_before_model_load(self):
        with self.assertRaises(FileNotFoundError):
            faster_whisper_adapter.transcribe_words("/definitely/missing.wav")


if __name__ == "__main__":
    unittest.main()
