#!/usr/bin/env python3
"""Offline, CPU-only OpenVINO/SD1.5 feasibility preflight. Never downloads models."""
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

def main():
    out=Path(os.environ.get("ASTRA_LAB_OUT","render_lab/output"))
    out.mkdir(parents=True,exist_ok=True)
    names=("openvino","diffusers","torch","transformers","safetensors")
    installed={name:importlib.util.find_spec(name) is not None for name in names}
    model_path=os.environ.get("ASTRA_SD15_MODEL_PATH","").strip()
    local_model=bool(model_path and Path(model_path).is_dir())
    report={
        "engine":"openvino-stable-diffusion-1.5",
        "mode":"offline-preflight-only",
        "dependencies":installed,
        "local_model_present":local_model,
        "model_download_attempted":False,
        "paid_api_used":False,
        "ready_to_attempt_inference":all(installed.values()) and local_model,
        "reason":"local dependencies and licensed model required; no automatic network download"
    }
    if installed["openvino"]:
        try:
            from openvino import Core
            report["available_devices"]=Core().available_devices
        except Exception as exc:
            report["openvino_error"]=str(exc)[:400]
            report["ready_to_attempt_inference"]=False
    (out/"openvino_preflight.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))
if __name__=="__main__":
    main()
