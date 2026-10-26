"""Manual, isolated CPU OpenVINO image feasibility benchmark. Never publishes."""
import argparse
import json
import os
import resource
import time
import traceback
from pathlib import Path

APPROVED_MODELS = {
    "preconverted": "piimaila/stable-diffusion-v1-5-openvino",
    "export": "stable-diffusion-v1-5/stable-diffusion-v1-5",
}
PROMPT = ("a single tall red-and-white striped lighthouse standing on a small rocky island, "
          "wide establishing shot with the ENTIRE lighthouse visible from base to top, "
          "blue ocean below, soft blue sky above, illustrated storybook painting, "
          "one clear focal subject, balanced composition with open space around the lighthouse")
NEGATIVE_PROMPT = ("multiple lighthouses, duplicate buildings, floating objects, "
                   "cropped tower, tower cut off by image border, extra towers, "
                   "abstract distortions, disjointed architecture, text, watermark")

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
    stage = "initialize"
    try:
        from optimum.intel import OVStableDiffusionPipeline
        from PIL import Image
        import torch
        load_options = {"export": profile == "export", "compile": False,
                        "device": "CPU",
                        "ov_config": {"INFERENCE_PRECISION_HINT": "f32"}}
        if profile == "export":
            # Avoid implicit large-model 8-bit weight compression in this diagnostic.
            load_options["load_in_8bit"] = False
        report["precision_hint"] = "f32"
        report["disable_auto_8bit"] = profile == "export"
        stage = "model_loading_or_export"
        print("ASTRA_CPU_STAGE: model_loading_or_export", flush=True)
        pipe = OVStableDiffusionPipeline.from_pretrained(model, **load_options)
        stage = "model_reshape_compile"
        print("ASTRA_CPU_STAGE: model_reshape_compile", flush=True)
        pipe.reshape(batch_size=1, height=768, width=512, num_images_per_prompt=1)
        pipe.compile()
        report["guidance_scale"] = 8.0
        report["seed"] = 42
        report["negative_prompt_enabled"] = True
        stage = "inference_and_safety_checker"
        print("ASTRA_CPU_STAGE: inference_and_safety_checker", flush=True)
        image = pipe(PROMPT, negative_prompt=NEGATIVE_PROMPT,
                     height=768, width=512, num_inference_steps=steps,
                     guidance_scale=8.0,
                     generator=torch.Generator(device="cpu").manual_seed(42)).images[0]
        if not isinstance(image, Image.Image):
            raise ValueError("No PIL image returned")
        stage = "image_quality"
        print("ASTRA_CPU_STAGE: image_quality", flush=True)
        image.save(output, format="PNG")
        from astra_v2.omniroute_image_assets import image_quality_report
        quality = image_quality_report(output.read_bytes(), "scene")
        report["quality"] = quality
        report["dimensions"] = {"width": image.width, "height": image.height}
        report["bytes"] = output.stat().st_size
        report["success"] = bool(quality["passed"])
        report["output"] = str(output)
    except Exception as exc:
        report["failed_stage"] = stage
        # No prompt, credentials, provider bodies or exception text in diagnostics.
        report["error_type"] = type(exc).__name__
        frames = traceback.extract_tb(exc.__traceback__)
        report["error_frames"] = [{"module_file": Path(frame.filename).name,
                                  "function": frame.name, "line": frame.lineno}
                                 for frame in frames[-5:]]
        if isinstance(exc, AttributeError):
            report["missing_attribute"] = getattr(exc, "name", None)
        if isinstance(exc, ValueError):
            # This isolated job passes no credentials to model loading; preserve a
            # bounded diagnostic without URLs, home paths or multiline content.
            import re
            message = str(exc).splitlines()[0][:350]
            message = re.sub(r"https?://\\S+", "[url]", message)
            message = re.sub(r"/(?:home|tmp|opt)/\\S+", "[path]", message)
            report["value_error_detail"] = message
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
