"""Publisher ffprobe recovery must survive incomplete Ubuntu mirror downloads.

This exercises the actual YAML shell fragment with isolated, zero-network tools.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "astra-v2-publish.yml"


def install_fragment():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    start = workflow.index("          # Only ffprobe is missing.")
    end = workflow.index("      # Long-form cover tests", start)
    fragment = workflow[start:end]
    # Stop at the end of this run: block; don't execute later workflow steps.
    return textwrap.dedent(fragment)


def write_script(path, body):
    path.write_text("#!/bin/sh\nset -eu\n" + body, encoding="utf-8")
    path.chmod(0o755)


class PublisherFfprobeRecoveryTests(unittest.TestCase):
    def test_fragment_has_valid_bash_syntax(self):
        fragment = install_fragment()
        result = subprocess.run(["bash", "-n", "-c", fragment], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def _exercise(self, create_corrupt_deb, curl_succeeds):
        with tempfile.TemporaryDirectory(prefix="astra-ffprobe-test-") as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            for name in ("find", "mkdir", "chmod"):
                (bin_dir / name).symlink_to("/usr/bin/" + name)
            write_script(bin_dir / "timeout", 'shift\nexec "$@"\n')
            write_script(bin_dir / "sudo", 'exit 0\n')
            write_script(
                bin_dir / "apt-get",
                ("if [ \"${1:-}\" = download ]; then\n"
                 + ("  printf truncated > ffmpeg_7_test.deb\n" if create_corrupt_deb else "")
                 + "fi\n"))
            write_script(bin_dir / "dpkg-deb", "exit 2\n")
            write_script(bin_dir / "curl",
                         "if [ " + ("1" if curl_succeeds else "0") + " -eq 0 ]; then exit 22; fi\n"
                         "previous=''\n"
                         "for arg in \"$@\"; do\n"
                         "  if [ \"$previous\" = '-o' ]; then : > \"$arg\"; fi\n"
                         "  previous=\"$arg\"\n"
                         "done\n")
            write_script(bin_dir / "tar",
                         "previous=''\n"
                         "for arg in \"$@\"; do\n"
                         "  if [ \"$previous\" = '-C' ]; then directory=\"$arg\"; fi\n"
                         "  previous=\"$arg\"\n"
                         "done\n"
                         "mkdir -p \"$directory\"\n"
                         "printf '#!/bin/sh\\nexit 0\\n' > \"$directory/ffprobe\"\n"
                         "chmod +x \"$directory/ffprobe\"\n")
            write_script(bin_dir / "ffmpeg", "exit 0\n")
            env = {
                "PATH": str(bin_dir),
                "RUNNER_TEMP": str(root / "runner"),
                "GITHUB_PATH": str(root / "github-path"),
            }
            (root / "runner").mkdir()
            result = subprocess.run(
                ["/bin/bash", "-e", "-c", install_fragment()],
                cwd=root, env=env, capture_output=True, text=True, timeout=15)
            recorded_path = (root / "github-path").read_text() if (root / "github-path").exists() else ""
            return result, recorded_path

    def test_truncated_deb_reaches_runtime_checked_static_fallback(self):
        result, path = self._exercise(create_corrupt_deb=True, curl_succeeds=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ASTRA_FFPROBE_DEB_EXTRACT_FAILED=1", result.stdout)
        self.assertIn("ASTRA_FFPROBE_SOURCE=static", result.stdout)
        self.assertIn("astra-static-probe", path)

    def test_missing_deb_reaches_runtime_checked_static_fallback(self):
        result, _ = self._exercise(create_corrupt_deb=False, curl_succeeds=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ASTRA_FFPROBE_SOURCE=static", result.stdout)

    def test_failed_fallback_blocks_publishing(self):
        result, _ = self._exercise(create_corrupt_deb=True, curl_succeeds=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ASTRA_FFPROBE_UNAVAILABLE=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
