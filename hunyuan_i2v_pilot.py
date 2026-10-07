"""Build a reproducible HunyuanVideo-1.5 I2V pilot command.

Does not execute paid inference. Intended for an available CUDA notebook/session.
"""
from __future__ import annotations
import json, os, shlex
from pathlib import Path
from animation_director import direction

def build_job(reference_image: str, prompt: str, output_path: str="outputs/astra_i2v_pilot.mp4",
              aspect_ratio: str="16:9", seed: int=7) -> dict:
    spec=direction("short")
    full_prompt=(prompt.strip()+"\nAnimation direction: "+"; ".join(spec["principles"]))
    args=[
        "python","generate.py","--prompt",full_prompt,
        "--image_path",reference_image,
        "--resolution","480p","--aspect_ratio",aspect_ratio,
        "--seed",str(seed),"--rewrite","false",
        "--cfg_distilled","true","--enable_step_distill","true",
        "--enable_cache","true","--cache_type","deepcache",
        "--sr","true","--save_pre_sr_video",
        "--output_path",output_path,"--model_path","./ckpts",
    ]
    return {
        "renderer":"hunyuanvideo_1_5",
        "mode":"i2v",
        "private_pilot":True,
        "minimum_vram_gb":14,
        "reference_image":reference_image,
        "output_path":output_path,
        "command":" ".join(shlex.quote(x) for x in args),
        "checkpoint_manifest":output_path+".json",
        "animation_profile":spec["version"],
    }

def save_manifest(job: dict) -> str:
    p=Path(job["checkpoint_manifest"])
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(job,indent=2),encoding="utf-8")
    return str(p)
