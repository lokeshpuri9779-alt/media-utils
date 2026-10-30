"""Publisher codec installation uses the same fail-closed path as long-form.

The original publisher-only .deb/static-xz fallback failed in live run
40992083726. Exercise the shared bootstrap offline with fake apt commands.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "astra_ffmpeg_bootstrap.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "astra-v2-publish.yml"


def write_script(path, body):
    path.write_text("#!/bin/sh\\nset -eu\\n" + body, encoding="utf-8")
    path.chmod(0o755)


class PublisherFfprobeRecoveryTests(unittest.TestCase):
    def test_publisher_uses_shared_bootstrap(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        step = workflow.split("- name: Install free rendering dependencies", 1)[1].split("\\n      - name:", 1)[0]
        self.assertIn("if: steps.preflight.outputs.render_due == 'true'", step)
        self.assertIn("bash tools/astra_ffmpeg_bootstrap.sh", step)

    def test_shared_bootstrap_has_valid_bash_syntax(self):
        result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def _exercise(self, install_succeeds=True, probe_works=True):
        with tempfile.TemporaryDirectory(prefix="astra-codec-test-") as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            (bin_dir / "head").symlink_to("/usr/bin/head")
            write_script(bin_dir / "timeout", 'shift\\nexec "$@"\\n')
            write_script(bin_dir / "sudo", """
case " $* " in
  *" install "*)
    if [ "$ASTRA_FAKE_INSTALL" != "yes" ]; then exit 1; fi
    printf '#!/bin/sh\\nprintf "ffmpeg test\\\\n"\\n' > "$ASTRA_FAKE_BIN/ffmpeg"
    printf '#!/bin/sh\\nprintf "ffprobe test\\\\n"\\n' > "$ASTRA_FAKE_BIN/ffprobe"
    if [ "$ASTRA_FAKE_PROBE" != "yes" ]; then
      printf '#!/bin/sh\\nexit 2\\n' > "$ASTRA_FAKE_BIN/ffprobe"
    fi
    /bin/chmod +x "$ASTRA_FAKE_BIN/ffmpeg" "$ASTRA_FAKE_BIN/ffprobe"
    ;;
esac
exit 0
""")
            env = {
                "PATH": str(bin_dir),
                "ASTRA_FAKE_BIN": str(bin_dir),
                "ASTRA_FAKE_INSTALL": "yes" if install_succeeds else "no",
                "ASTRA_FAKE_PROBE": "yes" if probe_works else "no",
            }
            return subprocess.run(["/bin/bash", str(SCRIPT)], cwd=root, env=env,
                                  capture_output=True, text=True, timeout=15)

    def test_missing_tools_installed_by_bounded_free_apt(self):
        result = self._exercise()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ASTRA_CODEC_BOOTSTRAP=ready", result.stdout)
        self.assertIn("ffprobe test", result.stdout)

    def test_failed_apt_install_blocks_publishing(self):
        result = self._exercise(install_succeeds=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cannot install free system ffmpeg/ffprobe", result.stderr)

    def test_unusable_probe_blocks_publishing(self):
        result = self._exercise(probe_works=False)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
