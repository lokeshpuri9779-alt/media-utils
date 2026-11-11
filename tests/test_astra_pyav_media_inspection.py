"""Independent MP4 inspection must work without a system ffprobe binary."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from astra_v2.creative import CreativeSkip, inspect_video
from imageio_ffmpeg import get_ffmpeg_exe


class PyAVMediaInspectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="astra-pyav-tests-")
        root = Path(cls.tmp.name)
        cls.valid = root / "valid.mp4"
        cls.silent = root / "silent.mp4"
        cls.landscape = root / "landscape.mp4"
        ffmpeg = get_ffmpeg_exe()

        def render(path, size, audio):
            command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                       "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=10"]
            if audio:
                command += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=24000"]
            command += ["-t", "2", "-c:v", "libx264", "-pix_fmt", "yuv420p"]
            if audio:
                command += ["-c:a", "aac", "-shortest"]
            command += [str(path)]
            subprocess.run(command, check=True, timeout=30)

        render(cls.valid, "360x640", True)
        render(cls.silent, "360x640", False)
        render(cls.landscape, "640x360", True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_decodes_real_video_and_audio(self):
        result = inspect_video(self.valid)
        self.assertEqual((result["width"], result["height"]), (360, 640))
        self.assertGreater(result["seconds"], 0)
        self.assertGreater(result["size"], 30_000)

    def test_missing_audio_is_rejected(self):
        with self.assertRaisesRegex(CreativeSkip, "video_or_audio_stream_missing"):
            inspect_video(self.silent)

    def test_wrong_orientation_is_rejected(self):
        with self.assertRaisesRegex(CreativeSkip, "video_audio_orientation_or_duration_failed"):
            inspect_video(self.landscape)

    def test_corrupt_mp4_is_rejected(self):
        corrupt = Path(self.tmp.name) / "corrupt.mp4"
        corrupt.write_bytes(b"not-an-mp4" * 5000)
        with self.assertRaises(CreativeSkip):
            inspect_video(corrupt)


if __name__ == "__main__":
    unittest.main()
