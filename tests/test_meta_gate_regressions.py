"""Offline publication gate regressions; no FFmpeg execution or uploads."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.meta_publish_gate import validate


def fixture(*, width=1080, height=1920, duration=12, audio=True, codec='h264'):
    streams = [{'codec_type': 'video', 'width': width, 'height': height, 'codec_name': codec}]
    if audio:
        streams.append({'codec_type': 'audio', 'codec_name': 'aac'})
    return {'streams': streams, 'format': {'duration': str(duration)}}


class MetaGateRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'video.mp4'
        self.path.write_bytes(b'fixture')

    def check(self, data, ready):
        with patch('integrations.meta_publish_gate.ffprobe', return_value=data):
            result = validate(self.path, require_audio=True, min_duration=10)
        self.assertEqual(result['ready'], ready, result)
        return result

    def test_valid_metadata(self):
        self.check(fixture(), True)

    def test_missing_audio(self):
        self.assertIn('Audio track missing', self.check(fixture(audio=False), False)['errors'])

    def test_short_duration(self):
        self.check(fixture(duration=9.9), False)

    def test_wrong_dimensions(self):
        self.check(fixture(width=720, height=1280), False)

    def test_wrong_codec(self):
        self.check(fixture(codec='hevc'), False)

    def test_missing_file(self):
        self.path.unlink()
        self.assertFalse(validate(self.path)['ready'])


if __name__ == '__main__':
    unittest.main()
