import unittest

import pyscenedetect_adapter


class PySceneDetectAdapterTests(unittest.TestCase):
    def test_backend_info(self):
        info = pyscenedetect_adapter.backend_info()
        self.assertEqual(info["engine"], "Breakthrough/PySceneDetect")
        self.assertIn("pacing-QA", info["purpose"])

    def test_missing_video_is_rejected_before_import_use(self):
        with self.assertRaises(FileNotFoundError):
            pyscenedetect_adapter.detect_scenes("/definitely/not/here.mp4")


if __name__ == "__main__":
    unittest.main()
