#!/usr/bin/env python3
"""Offline Stable Diffusion image adapter. Fails closed if weights/deps absent.
Does not download weights, invoke hosted inference, or silently use existing images.
"""
import argparse, json, os, time
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True,help="Local diffusers-format SD1.5 model directory")
    p.add_argument("--prompts",required=True,help="UTF-8 text file, one prompt per line")
    p.add_argument("--output",default="generated_scenes")
    p.add_argument("--steps",type=int,default=12)
    p.add_argument("--seed",type=int,default=42)
    a=p.parse_args()
    model=Path(a.model).resolve()
    if not model.is_dir() or not (model/"model_index.json").is_file():
        p.error("A real local diffusers model directory is required; no download/fallback")
    if not 1<=a.steps<=80: p.error("steps must be 1..80")
    prompts=[x.strip() for x in Path(a.prompts).read_text(encoding="utf-8").splitlines() if x.strip()]
    if not prompts: p.error("No prompts")
    os.environ["HF_HUB_OFFLINE"]="1"
    os.environ["TRANSFORMERS_OFFLINE"]="1"
    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except ImportError as e:
        p.error("Install CPU torch + diffusers + transformers + safetensors: "+str(e))
    pipe=StableDiffusionPipeline.from_pretrained(str(model),local_files_only=True,
        safety_checker=None,torch_dtype=torch.float32).to("cpu")
    pipe.enable_attention_slicing()
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
    details=[]
    for i,prompt in enumerate(prompts,1):
        started=time.monotonic()
        generator=torch.Generator(device="cpu").manual_seed(a.seed+i-1)
        result=pipe(prompt,num_inference_steps=a.steps,generator=generator,
                    height=512,width=512)
        if result.nsfw_content_detected and any(result.nsfw_content_detected):
            raise RuntimeError("Model reported unsafe content")
        filename=out/f"scene_{i:02d}.png"
        result.images[0].save(filename)
        details.append({"path":str(filename),"seconds":round(time.monotonic()-started,2),
                        "seed":a.seed+i-1})
    report={"ai_images_generated":True,"model":str(model),"offline":True,
            "scenes":details,"character_consistency_verified":False}
    (out/"image_generation_report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
