"""Four-image manual diagnostic. No approval, production integration or publishing."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import time

from tools.experimental_openvino_benchmark import APPROVED_MODELS, PROMPT

CASES = ((42, 8), (42, 20), (123, 8), (123, 20))


def run(output=Path("artifacts/experimental-openvino"), *, square=False, objects=False):
    square = square or objects
    cases = ((42, 20), (123, 20)) if square else CASES
    prompts = [PROMPT] * len(cases)
    labels = [f"seed-{seed}-steps-{steps}" for seed, steps in cases]
    if objects:
        cases = ((42, 20), (42, 20))
        labels = ["truck-only", "school-only"]
        prompts = [
            "family-friendly illustration of a single bright red toy fire truck, side view, fully visible, on a plain white background, clear colorful detailed shapes, no people, no text",
            "family-friendly illustration of a single yellow school building, front view, fully visible, on a plain white background, clear colorful detailed shapes, no people, no text",
        ]
    height = 512 if square else 768
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = dict(approved=False, production_ready=False, published=False,
                  semantic_quality="not_verified", character_continuity="not_verified",
                  manual_visual_review_required=True, still_image_only=True,
                  diagnostic_only=True, square_resolution_test=square, object_isolation_test=objects,
                  prompt=PROMPT, model=APPROVED_MODELS["export"],
                  code_revision=os.getenv("GITHUB_SHA", "local"), cases=[])
    try:
        import numpy as np
        from huggingface_hub import HfApi
        from optimum.intel import OVStableDiffusionPipeline
        from astra_v2.omniroute_image_assets import image_quality_report
        report["packages"] = {d.metadata["Name"]: d.version
                              for d in importlib.metadata.distributions()
                              if d.metadata["Name"]}
        # Resolve once, then load this immutable revision for every case.
        revision = ("451f4fe16113bff5a5d2269ed5ad43b0592e9a14" if square
                    else HfApi().model_info(report["model"]).sha)
        if not revision:
            raise ValueError("Missing immutable model revision")
        report["model_revision"] = revision
        pipe = OVStableDiffusionPipeline.from_pretrained(
            report["model"], revision=revision, export=True, compile=False,
            device="CPU", load_in_8bit=False,
            ov_config={"INFERENCE_PRECISION_HINT": "f32"})
        pipe.reshape(batch_size=1, height=height, width=512, num_images_per_prompt=1)
        pipe.compile()
        report["setup_seconds"] = round(time.monotonic() - started, 2)
        report["scheduler"] = type(pipe.scheduler).__name__
        report["scheduler_config"] = dict(pipe.scheduler.config)
        report["precision_hint"] = "f32"
        report["disable_auto_8bit"] = True
        for (seed, steps), prompt, label in zip(cases, prompts, labels):
            row = dict(case_id=label, prompt=prompt, seed=seed, steps=steps, approved=False, published=False,
                       production_ready=False, semantic_quality="not_verified",
                       manual_visual_review_required=True, render_completed=False,
                       pixel_quality_passed=False)
            report["cases"].append(row)
            case_started = time.monotonic()
            try:
                # Fresh RNG gives each step-count comparison the same initial seed.
                image = pipe(prompt, height=height, width=512,
                             num_inference_steps=steps, guidance_scale=7.5,
                             generator=np.random.RandomState(seed)).images[0]
                row["inference_seconds"] = round(time.monotonic() - case_started, 2)
                target = output / f"{label}.png"
                image.save(target, format="PNG")
                raw = target.read_bytes()
                quality = image_quality_report(raw, "background" if square else "scene")
                # Square diagnostics are never eligible portrait scene assets.
                row["portrait_scene_eligible"] = not square
                row.update(render_completed=True, pixel_quality_passed=bool(quality["passed"]),
                           quality=quality, image_sha256=hashlib.sha256(raw).hexdigest(),
                           output=target.name, width=image.width, height=image.height,
                           guidance_scale=7.5)
            except Exception as exc:
                row["error_type"] = type(exc).__name__
            finally:
                row["elapsed_seconds"] = round(time.monotonic() - case_started, 2)
                row["process_peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                (output / f"{label}.json").write_text(json.dumps(row, indent=2))
                (output / "comparison.json").write_text(json.dumps(report, indent=2, default=str))
    except Exception as exc:
        report["error_type"] = type(exc).__name__
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        report["process_peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report["technical_comparison_completed"] = (
            len(report["cases"]) == len(cases)
            and all(c["render_completed"] and c["pixel_quality_passed"] for c in report["cases"]))
        (output / "comparison.json").write_text(json.dumps(report, indent=2, default=str))
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--square", action="store_true")
    parser.add_argument("--objects", action="store_true")
    args = parser.parse_args()
    raise SystemExit(0 if run(square=args.square, objects=args.objects)["technical_comparison_completed"] else 1)
