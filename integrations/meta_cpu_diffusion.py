"""Optional, CPU-only text-to-image benchmark for Meta ASTRA.

Explicit opt-in only. No publishing, no API keys, no paid services. Downloading
model weights may be subject to license and GitHub runner bandwidth limits.
Produces a still image, NOT AI-generated video; motion must be added separately.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

MODEL = 'segmind/tiny-sd'


def generate(prompt: str, output: Path, *, enabled: bool = False,
             steps: int = 25, seed: int = 1234) -> dict:
    if not enabled:
        raise RuntimeError('CPU diffusion disabled until explicitly opted in')
    if not prompt.strip():
        raise ValueError('Prompt is required')
    if not 1 <= steps <= 100:
        raise ValueError('steps must be 1-100')
    # Import only after opt-in, so basic CLI use requires no ML packages.
    import torch
    from diffusers import StableDiffusionPipeline
    pipe = StableDiffusionPipeline.from_pretrained(MODEL, torch_dtype=torch.float32,
                                                   safety_checker=None)
    pipe = pipe.to('cpu')
    pipe.enable_attention_slicing()
    generator = torch.Generator(device='cpu').manual_seed(seed)
    image = pipe(prompt, num_inference_steps=steps, guidance_scale=7.0,
                 generator=generator).images[0]
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return {'output': str(output), 'model': MODEL, 'source': 'cpu_diffusion',
            'still_image_only': True, 'published': False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=25)
    parser.add_argument('--seed', type=int, default=1234)
    parser.add_argument('--enable', action='store_true')
    args = parser.parse_args()
    print(json.dumps(generate(args.prompt, args.output, enabled=args.enable,
                              steps=args.steps, seed=args.seed), indent=2))

if __name__ == '__main__':
    main()
