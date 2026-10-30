import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublisherCodecBootstrapContract(unittest.TestCase):
    def test_publisher_uses_proven_longform_codec_bootstrap_only_when_render_due(self):
        publisher = (ROOT / ".github/workflows/astra-v2-publish.yml").read_text(encoding="utf-8")
        longform = (ROOT / ".github/workflows/astra-v2-longform.yml").read_text(encoding="utf-8")
        bootstrap = (ROOT / "tools/astra_ffmpeg_bootstrap.sh").read_text(encoding="utf-8")
        publisher_install = publisher.split("- name: Install free rendering dependencies", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("if: steps.preflight.outputs.render_due == 'true'", publisher_install)
        self.assertIn("bash tools/astra_ffmpeg_bootstrap.sh", publisher_install)
        self.assertIn("bash tools/astra_ffmpeg_bootstrap.sh", longform)
        self.assertNotIn("ffmpeg-release-amd64-static.tar.xz", publisher_install)
        self.assertNotIn("apt-get download ffmpeg", publisher_install)
        self.assertIn("set -euo pipefail", bootstrap)
        self.assertIn("command -v ffmpeg", bootstrap)
        self.assertIn("command -v ffprobe", bootstrap)
        self.assertIn("ffprobe -version", bootstrap)


if __name__ == "__main__":
    unittest.main()
