"""Isolated CPU OpenVINO Stable Diffusion 1.5 keyframe benchmark. Never publishes."""
import argparse
import json
import time
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model',default='stable-diffusion-v1-5/stable-diffusion-v1-5')
    p.add_argument('--steps',type=int,default=12)
    p.add_argument('--output',type=Path,default=Path('artifacts/experimental-openvino/keyframe.png'))
    a=p.parse_args()
    if not 1<=a.steps<=40: p.error('steps must be 1..40')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    report={'engine':'OpenVINO Stable Diffusion','model':a.model,'steps':a.steps,'success':False,'published':False,'still_image_only':True}
    start=time.monotonic()
    try:
        from optimum.intel.openvino import OVStableDiffusionPipeline
        pipe=OVStableDiffusionPipeline.from_pretrained(a.model,export=True,device='CPU',compile=True)
        result=pipe('cinematic stylized 3D animated film still of a small copper robot holding a glowing star in a magical forest, cinematic lighting, original character, no text',num_inference_steps=a.steps)
        result.images[0].save(a.output)
        report['success']=a.output.is_file() and a.output.stat().st_size>1000
        report['output']=str(a.output)
        report['bytes']=a.output.stat().st_size
    except Exception as exc:
        report['error']=f'{type(exc).__name__}: {exc}'
    finally:
        report['elapsed_seconds']=round(time.monotonic()-start,2)
        a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\\n')
        print(json.dumps(report,indent=2))
    if not report['success']: raise SystemExit(1)

if __name__=='__main__':main()
