#!/usr/bin/env python3
"""Read-only CPU image-generation readiness check; never downloads model weights."""
import argparse, importlib.util, json, shutil, sys
from pathlib import Path

def probe(model):
    modules={name:importlib.util.find_spec(name) is not None
             for name in ("torch","diffusers","transformers","safetensors","openvino")}
    tools={name:shutil.which(name) is not None for name in ("ffmpeg","espeak")}
    path=Path(model).expanduser().resolve() if model else None
    local_model=bool(path and path.is_dir() and (path/"model_index.json").is_file())
    requirements={"torch":modules["torch"],"diffusers":modules["diffusers"],
                  "transformers":modules["transformers"],
                  "safetensors":modules["safetensors"],
                  "local_diffusers_model":local_model}
    return {"mode":"offline_cpu","modules":modules,"tools":tools,
            "model_path":str(path) if path else None,
            "requirements":requirements,
            "image_generation_ready":all(requirements.values()),
            "generation_executed":False,
            "character_consistency_verified":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",help="Existing local diffusers model directory")
    p.add_argument("--output",help="Optional JSON report path")
    a=p.parse_args()
    report=probe(a.model)
    serialized=json.dumps(report,indent=2)
    if a.output:
        dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(serialized+"\\n",encoding="utf-8")
    print(serialized)
    return 0 if report["image_generation_ready"] else 2

if __name__=="__main__":sys.exit(main())
