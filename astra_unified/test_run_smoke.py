"""CLI safety tests for the single-command smoke launcher."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT=Path(__file__).with_name("run_smoke.py")

class SmokeLauncherTests(unittest.TestCase):
    def invoke(self, assets, output, script=None):
        args=[sys.executable,str(SCRIPT),"--assets",str(assets),"--output",str(output)]
        if script is not None: args+=["--script",str(script)]
        return subprocess.run(args,capture_output=True,text=True,timeout=15)

    def test_missing_images_fail_before_running(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            result=self.invoke(root,root/"output")
            self.assertNotEqual(result.returncode,0)
            self.assertIn("eight scene_",result.stderr)
            self.assertFalse((root/"output").exists())

    def test_empty_narration_script_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for i in range(1,9):
                (root/f"scene_{i:02d}.jpg").write_bytes(b"not decoded by preflight")
            script=root/"empty.txt";script.write_text("  ")
            result=self.invoke(root,root/"output",script)
            self.assertNotEqual(result.returncode,0)
            self.assertIn("missing or empty",result.stderr)
            self.assertFalse((root/"output").exists())

if __name__=="__main__":unittest.main()
