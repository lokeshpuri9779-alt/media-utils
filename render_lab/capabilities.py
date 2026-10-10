#!/usr/bin/env python3
"""Static CPU renderer capability inventory; no installs, downloads, or publishing."""
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

TOOLS=("ffmpeg","ffprobe","blender","godot","godot4")
def probe_version(name):
    executable=shutil.which(name)
    if not executable:
        return {"installed":False}
    try:
        p=subprocess.run([executable,"--version"],capture_output=True,text=True,timeout=12)
        return {"installed":True,"path":executable,"returncode":p.returncode,
                "version":(p.stdout or p.stderr).splitlines()[:3]}
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {"installed":True,"error":str(exc)[:300]}

def main():
    out=Path(os.environ.get("ASTRA_LAB_OUT","render_lab/output"))
    out.mkdir(parents=True,exist_ok=True)
    data={"platform":platform.platform(),"cpu_count":os.cpu_count(),
          "tools":{name:probe_version(name) for name in TOOLS},
          "python_packages":{}}
    for name in ("openvino","diffusers","torch","PIL"):
        try:
            from importlib.util import find_spec
            data["python_packages"][name]=find_spec(name) is not None
        except (ImportError,ValueError):
            data["python_packages"][name]=False
    (out/"capabilities.json").write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps(data))
if __name__=="__main__":
    main()
