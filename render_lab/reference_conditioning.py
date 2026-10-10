"""Reference-conditioned SD1.5 image-to-image CPU scene generation (experimental).

This is not a character identity lock; low denoising strength tends to preserve
composition and appearance, at the cost of less variation between scenes.
"""
from pathlib import Path

def generate_from_reference(prompt: str, reference: Path, output: Path, *,
                            steps: int = 20, seed: int = 1235,
                            strength: float = 0.35) -> dict:
    if not reference.is_file():
        raise FileNotFoundError(reference)
    if not 0.15 <= strength <= 0.65:
        raise ValueError("strength must be 0.15..0.65")
    if not 5 <= steps <= 100:
        raise ValueError("steps must be 5..100")
    import torch
    from PIL import Image
    from diffusers import StableDiffusionImg2ImgPipeline
    model="stable-diffusion-v1-5/stable-diffusion-v1-5"
    pipe=StableDiffusionImg2ImgPipeline.from_pretrained(model,torch_dtype=torch.float32,safety_checker=None)
    pipe=pipe.to("cpu")
    pipe.enable_attention_slicing()
    with Image.open(reference) as im:
        init=im.convert("RGB").resize((512,512))
    generator=torch.Generator(device="cpu").manual_seed(seed)
    image=pipe(prompt=prompt,image=init,strength=strength,
               num_inference_steps=steps,guidance_scale=7.0,
               generator=generator).images[0]
    output.parent.mkdir(parents=True,exist_ok=True)
    image.save(output)
    return {"reference":str(reference),"output":str(output),"strength":strength,
            "method":"SD1.5 image-to-image","published":False}
