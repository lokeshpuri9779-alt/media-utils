"""Protect long-form free codec install from regressions."""
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class CodecBootstrapTests(unittest.TestCase):
    def test_script_is_valid_bash(self):
        subprocess.run(["bash","-n",str(ROOT/"tools/astra_ffmpeg_bootstrap.sh")],
                       check=True)

    def test_bootstrap_requires_encoder_and_probe(self):
        source=(ROOT/"tools/astra_ffmpeg_bootstrap.sh").read_text()
        self.assertIn("command -v ffmpeg",source)
        self.assertIn("command -v ffprobe",source)
        self.assertIn("apt-get install -y ffmpeg",source)
        self.assertIn("have_video_tools ||",source)
        self.assertIn("exit 1",source)

    def test_longform_uses_codec_bootstrap_after_python_packages(self):
        workflow=(ROOT/".github/workflows/astra-v2-longform.yml").read_text()
        self.assertIn("bash tools/astra_ffmpeg_bootstrap.sh",workflow)
        self.assertIn("timeout 360s python -m pip install",workflow)
        self.assertLess(workflow.index("timeout 360s python -m pip install"),
                        workflow.index("bash tools/astra_ffmpeg_bootstrap.sh"))


if __name__=="__main__":
    unittest.main()
