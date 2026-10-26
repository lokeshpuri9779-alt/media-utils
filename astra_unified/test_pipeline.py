"""Tests for unified stage orchestration. Run: python -m unittest discover -s astra_unified -p 'test_*.py'"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT=Path(__file__).with_name("pipeline.py")
STAGES=("STORY","IMAGES","CONSISTENCY","ANIMATION","NARRATION","EDIT","QUALITY","PUBLISH")
class PipelineTests(unittest.TestCase):
    def invoke(self, env_overrides=None, publish=False, dry=False):
        with tempfile.TemporaryDirectory() as directory:
            env=os.environ.copy()
            for stage in STAGES: env.pop("ASTRA_"+stage+"_CMD",None)
            env.update(env_overrides or {})
            args=[sys.executable,str(SCRIPT),"--output",directory]
            if publish: args.append("--publish")
            if dry: args.append("--dry-run")
            result=subprocess.run(args,env=env,capture_output=True,text=True)
            report=json.loads((Path(directory)/"run_report.json").read_text())
            return result,report
    def test_missing_story_fails_closed(self):
        r,p=self.invoke()
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(p["status"],"blocked")
        self.assertEqual(list(p["stages"]),["story"])
    def test_dry_run_plans_all_except_publish(self):
        commands={"ASTRA_"+s+"_CMD":"true" for s in STAGES}
        r,p=self.invoke(commands,dry=True)
        self.assertEqual(r.returncode,0)
        self.assertEqual(p["status"],"planned")
        self.assertEqual(p["stages"]["publish"]["status"],"skipped")
    def test_failing_stage_stops_pipeline(self):
        commands={"ASTRA_STORY_CMD":"false","ASTRA_IMAGES_CMD":"true"}
        r,p=self.invoke(commands)
        self.assertNotEqual(r.returncode,0)
        self.assertEqual(p["stages"]["story"]["status"],"failed")
        self.assertNotIn("images",p["stages"])
    def test_publish_requires_opt_in(self):
        commands={"ASTRA_"+s+"_CMD":"true" for s in STAGES}
        r,p=self.invoke(commands)
        self.assertEqual(r.returncode,0)
        self.assertEqual(p["stages"]["publish"]["status"],"skipped")
    def test_dry_run_never_executes_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/"executed"
            command=f"{sys.executable} -c 'from pathlib import Path; Path({str(marker)!r}).touch()'"
            r,p=self.invoke({"ASTRA_"+s+"_CMD":command for s in STAGES},dry=True)
            self.assertEqual(r.returncode,0)
            self.assertFalse(marker.exists())
    def test_publish_explicit_opt_in(self):
        commands={"ASTRA_"+s+"_CMD":"true" for s in STAGES}
        r,p=self.invoke(commands,publish=True)
        self.assertEqual(r.returncode,0)
        self.assertEqual(p["stages"]["publish"]["status"],"passed")
if __name__=="__main__":unittest.main()
