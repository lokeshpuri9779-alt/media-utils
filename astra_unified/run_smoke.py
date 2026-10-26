#!/usr/bin/env python3
"""Run all seven non-generative ASTRA smoke stages with one command."""
import argparse, os, shlex, subprocess, sys
from pathlib import Path

STAGES=("story","images","consistency","animation","narration","edit","quality")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--assets",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    base=Path(__file__).resolve().parent
    pipeline=base/"pipeline.py"
    adapter=base/"demo_stage.py"
    if not pipeline.is_file() or not adapter.is_file():
        p.error("pipeline.py and demo_stage.py must be beside run_smoke.py")
    assets=a.assets.expanduser().resolve()
    if len(list(assets.glob("scene_*.jpg")))<8:
        p.error("At least eight scene_*.jpg images are required")
    env=os.environ.copy()
    for stage in STAGES:
        env["ASTRA_"+stage.upper()+"_CMD"]=shlex.join(
            (sys.executable,str(adapter),stage,str(assets)))
    env.pop("ASTRA_PUBLISH_CMD",None)
    return subprocess.run((sys.executable,str(pipeline),"--output",
                           str(a.output.expanduser().resolve())),
                          env=env,check=False).returncode
if __name__=="__main__":sys.exit(main())
