"""Manual, isolated CPU OpenVINO image feasibility benchmark. Never publishes."""
import argparse
import json
import os
import resource
import time
from pathlib import Path

APPROVED_MODELS = {
    "preconverted": "OpenVINO/stable-diffusion-v1-5-int8-ov",
    "export": "stable-diffusion-v1-5/stable-diffusion-v1-5",
}
PROMPT = ("original cinematic animated-film illustration, a small copper robot holding "
          "a glowing star in a magical forest, dramatic lighting, detailed background, "
          "no text, portrait composition")


PROMPTS = {
    "baseline": PROMPT,
    "simple": "a small copper toy robot standing in a green forest, full body, centered, illustration",
    "geometry": "a red wooden cube on a plain blue table, centered, simple studio illustration",
}

def run(*, profile="preconverted", steps=8, prompt_profile="baseline", output=Path("artifacts/experimental-openvino/keyframe.png")):
    if profile not in APPROVED_MODELS:
        raise ValueError("Unapproved model profile")
    if not isinstance(steps, int) or not 1 <= steps <= 20:
        raise ValueError("steps must be 1..20")
    if prompt_profile not in PROMPTS:
        raise ValueError("Unapproved prompt profile")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Never leave a stale image that could be mistaken for this run's output.
    output.unlink(missing_ok=True)
    model = APPROVED_MODELS[profile]
    report = {"engine": "OpenVINO CPU", "model": model, "steps": steps, "prompt_profile": prompt_profile,
              "seed": 42, "success": False, "published": False, "approved": False,
              "production_ready": False, "still_image_only": True,
              "render_completed": False,
              "semantic_quality": "not_verified",
              "manual_visual_review_required": True,
              "safety_rejection_policy": "discard_image_and_fail",
              "safety_false_positive": "not_determined"}
    started = time.monotonic()
    stage = "import_pipeline"
    try:
        from optimum.intel import OVStableDiffusionPipeline
        stage = "import_pillow"
        from PIL import Image
        if profile == "preconverted":
            stage = "model_manifest"
            from huggingface_hub import list_repo_files
            available_files = set(list_repo_files(model))
            required_files = ("model_index.json", "unet/config.json", "unet/openvino_model.xml")
            missing_files = [name for name in required_files if name not in available_files]
            if missing_files:
                report["missing_model_files"] = missing_files
                raise ValueError("Preconverted OpenVINO model is missing required configuration or model files")
            # The INT8 repo may only carry an OpenVINO safety checker IR.
            # Load a real Transformers checkpoint from the original SD1.5
            # repository instead; never disable the checker to make loading work.
            checker_repo = "stable-diffusion-v1-5/stable-diffusion-v1-5"
            stage = "safety_checker_load"
            from transformers import CLIPImageProcessor
            from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker
            checker = StableDiffusionSafetyChecker.from_pretrained(
                checker_repo, subfolder="safety_checker", use_safetensors=True
            )
            feature_extractor = CLIPImageProcessor.from_pretrained(
                checker_repo, subfolder="feature_extractor"
            )
            if checker is None or feature_extractor is None:
                raise ValueError("Compatible safety checker or image processor unavailable")
            report["safety_checker_source"] = checker_repo
            report["safety_checker_loaded"] = True

        stage = "model_load"
        load_started = time.monotonic()
        pipe = OVStableDiffusionPipeline.from_pretrained(
            model, export=profile == "export", compile=False, device="CPU",
            **({"safety_checker": checker, "feature_extractor": feature_extractor}
               if profile == "preconverted" else {}))
        report["model_load_seconds"] = round(time.monotonic() - load_started, 2)
        if profile == "preconverted" and (
            getattr(pipe, "safety_checker", None) is None
            or getattr(pipe, "feature_extractor", None) is None
        ):
            raise ValueError("Pipeline did not retain required safety components")
        stage = "reshape_compile"
        compile_started = time.monotonic()
        pipe.reshape(batch_size=1, height=768, width=512, num_images_per_prompt=1)
        pipe.compile()
        report["reshape_compile_seconds"] = round(time.monotonic() - compile_started, 2)
        stage = "inference"
        inference_started = time.monotonic()
        try:
            result = pipe(PROMPTS[prompt_profile], height=768, width=512,
                          num_inference_steps=steps, generator=__import__("torch").Generator(device="cpu").manual_seed(42))
            if profile == "preconverted":
                flags = getattr(result, "nsfw_content_detected", None)
                if not isinstance(flags, (list, tuple)) or len(flags) != 1 or type(flags[0]) is not bool:
                    raise ValueError("Safety checker result missing or malformed")
                report["safety_checker_applied"] = True
                report["nsfw_content_detected"] = flags[0]
                if flags[0]:
                    report["safety_rejection_observed"] = True
                    raise ValueError("Safety checker flagged generated content")
            image = result.images[0]
        finally:
            report["inference_seconds"] = round(time.monotonic() - inference_started, 2)
        stage = "validate_image"
        if not isinstance(image, Image.Image):
            raise ValueError("No PIL image returned")
        stage = "save_image"
        image.save(output, format="PNG")
        stage = "pixel_quality"
        from astra_v2.omniroute_image_assets import image_quality_report
        quality = image_quality_report(output.read_bytes(), "scene")
        report["quality"] = quality
        report["dimensions"] = {"width": image.width, "height": image.height}
        report["bytes"] = output.stat().st_size
        report["render_completed"] = True
        if not quality["passed"]:
            raise ValueError("Pixel-quality gate rejected generated image")
        report["success"] = True
        report["output"] = str(output)
    except Exception as exc:
        # A failed safety or pixel-quality gate must not retain a reviewable PNG.
        output.unlink(missing_ok=True)
        # No prompt, credentials, provider bodies or exception text in diagnostics.
        report["error_type"] = type(exc).__name__
        if isinstance(exc, ValueError):
            report["error_message"] = str(exc)[:500]
        elif isinstance(exc, OSError) and stage == "model_load":
            # Redact URLs, absolute paths and long opaque tokens; never print raw exceptions.
            import re
            message = str(exc)
            message = re.sub(r"https?://\\S+|(?:/[^\\s:]+)+|[A-Za-z0-9_-]{32,}", "[redacted]", message)
            report["error_message"] = message[:500]
        report["error_stage"] = stage
        if isinstance(exc, AttributeError):
            report["missing_attribute"] = getattr(exc, "name", None)
        import traceback
        frames = traceback.extract_tb(exc.__traceback__)
        report["error_frames"] = [
            {"module_file": Path(frame.filename).name,
             "function": frame.name, "line": frame.lineno}
            for frame in frames[-4:]
        ]
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
    parser.add_argument("--prompt-profile", choices=sorted(PROMPTS), default="baseline")
    parser.add_argument("--output", type=Path, default=Path("artifacts/experimental-openvino/keyframe.png"))
    args = parser.parse_args()
    if not run(profile=args.profile, steps=args.steps, prompt_profile=args.prompt_profile, output=args.output)["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
