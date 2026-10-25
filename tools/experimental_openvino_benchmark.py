"""Manual, isolated CPU OpenVINO image feasibility benchmark. Never publishes."""
import argparse
import json
import os
import resource
import time
from pathlib import Path

APPROVED_MODELS = {
    "preconverted": "echarlaix/stable-diffusion-v1-5-openvino",
    "export": "stable-diffusion-v1-5/stable-diffusion-v1-5",
}
PROMPT = ("original cinematic animated-film illustration, a small copper robot holding "
          "a glowing star in a magical forest, dramatic lighting, detailed background, "
          "no text, portrait composition")


def run(*, profile="preconverted", steps=8, output=Path("artifacts/experimental-openvino/keyframe.png")):
    if profile not in APPROVED_MODELS:
        raise ValueError("Unapproved model profile")
    if not isinstance(steps, int) or not 1 <= steps <= 20:
        raise ValueError("steps must be 1..20")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    model = APPROVED_MODELS[profile]
    report = {"engine": "OpenVINO CPU", "model": model, "steps": steps,
              "success": False, "published": False, "approved": False,
              "production_ready": False, "still_image_only": True}
    started = time.monotonic()
    try:
        from optimum.intel import OVStableDiffusionPipeline
        from PIL import Image
        pipe = OVStableDiffusionPipeline.from_pretrained(
            model, export=profile == "export", compile=False, device="CPU")
        pipe.reshape(batch_size=1, height=768, width=512, num_images_per_prompt=1)
        pipe.compile()
        image = pipe(PROMPT, height=768, width=512,
                     num_inference_steps=steps).images[0]
        if not isinstance(image, Image.Image):
            raise ValueError("No PIL image returned")
        image.save(output, format="PNG")
        from astra_v2.omniroute_image_assets import image_quality_report
        quality = image_quality_report(output.read_bytes(), "scene")
        report["quality"] = quality
        report["dimensions"] = {"width": image.width, "height": image.height}
        report["bytes"] = output.stat().st_size
        report["success"] = bool(quality["passed"])
        report["output"] = str(output)
    except Exception as exc:
        # No prompt, credentials, provider bodies or exception text in diagnostics.
        report["error_type"] = type(exc).__name__
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=sorted(APPROVED_MODELS), default="preconverted")
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("artifacts/experimental-openvino/keyframe.png"))
    args = parser.parse_args()
    if not run(profile=args.profile, steps=args.steps, output=args.output)["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
