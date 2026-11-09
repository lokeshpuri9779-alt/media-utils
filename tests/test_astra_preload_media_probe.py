"""PyAV fallback keeps preload MP4 inspection independent of system ffprobe."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from astra_v2.creative import CreativeSkip, inspect_video


class _FakeContainer:
    duration = 2_000_000

    def __init__(self, *, has_audio=True, decodable=True):
        self.streams = [
            SimpleNamespace(type="video", index=0, duration=None, time_base=None)
        ]
        if has_audio:
            self.streams.append(SimpleNamespace(type="audio", index=1))
        self._decodable = decodable

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def decode(self, video=None, audio=None):
        if not self._decodable:
            return iter(())
        if audio is not None:
            return iter((SimpleNamespace(samples=1024),))
        return iter((SimpleNamespace(width=360, height=640),))


class PreloadMediaProbeTests(unittest.TestCase):
    def _video_file(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "fixture.mp4"
        path.write_bytes(b"x" * 30_001)
        return path

    def test_pyav_fallback_accepts_decodable_portrait_video_with_audio(self):
        container = _FakeContainer()
        with patch("astra_v2.creative.subprocess.run", side_effect=FileNotFoundError), \
             patch("av.open", return_value=container):
            report = inspect_video(self._video_file())
        self.assertEqual((report["width"], report["height"]), (360, 640))
        self.assertEqual(report["seconds"], 2.0)

    def test_pyav_fallback_rejects_video_without_audio(self):
        with patch("astra_v2.creative.subprocess.run", side_effect=FileNotFoundError), \
             patch("av.open", return_value=_FakeContainer(has_audio=False)):
            with self.assertRaisesRegex(CreativeSkip, "video_audio_orientation_or_duration_failed"):
                inspect_video(self._video_file())

    def test_pyav_fallback_rejects_undecodable_audio(self):
        class BrokenAudioContainer(_FakeContainer):
            def decode(self, video=None, audio=None):
                if audio is not None:
                    return iter(())
                return super().decode(video=video, audio=audio)
        with patch("astra_v2.creative.subprocess.run", side_effect=FileNotFoundError), \\
             patch("av.open", return_value=BrokenAudioContainer()):
            with self.assertRaisesRegex(CreativeSkip, "video_audio_orientation_or_duration_failed"):
                inspect_video(self._video_file())

    def test_pyav_fallback_rejects_undecodable_video(self):
        with patch("astra_v2.creative.subprocess.run", side_effect=FileNotFoundError), \
             patch("av.open", return_value=_FakeContainer(decodable=False)):
            with self.assertRaisesRegex(CreativeSkip, "pyav_decode_failed"):
                inspect_video(self._video_file())


if __name__ == "__main__":
    unittest.main()
