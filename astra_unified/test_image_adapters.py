"""Dependency-free failure-path checks for offline image adapters."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent

class ImageAdapterTests(unittest.TestCase):
    def test_readiness_without_model_reports_not_ready(self):
        result=subprocess.run([sys.executable,str(ROOT/"check_image_readiness.py")],
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,2)
        data=json.loads(result.stdout)
        self.assertFalse(data["image_generation_ready"])
        self.assertFalse(data["generation_executed"])
        self.assertFalse(data["requirements"]["local_diffusers_model"])

    def test_sd15_refuses_missing_model_before_loading_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prompts=root/"prompts.txt"
            prompts.write_text("A lighthouse at sunrise\\n",encoding="utf-8")
            result=subprocess.run([sys.executable,str(ROOT/"offline_sd15.py"),
                                   "--model",str(root/"absent"),"--prompts",str(prompts),
                                   "--output",str(root/"generated")],
                                  capture_output=True,text=True,timeout=30)
            self.assertNotEqual(result.returncode,0)
            self.assertIn("real local diffusers model directory",result.stderr)
            self.assertFalse((root/"generated").exists())

if __name__=="__main__":unittest.main()
