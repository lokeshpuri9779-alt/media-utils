"""Bounded CPU backend parity diagnostic; never approves or publishes assets."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"
REVISION = "451f4fe16113bff5a5d2269ed5ad43b0592e9a14"
PROMPT = "family-friendly illustration of a single bright red toy fire truck, side view, fully visible, on a plain white background, clear colorful detailed shapes, no people, no text"
GATES = dict(approved=False, production_ready=False, published=False,
             semantic_quality="not_verified", character_continuity="not_verified",
             manual_visual_review_required=True, diagnostic_only=True,
             portrait_scene_eligible=False)


def save(path, data):
    path.write_text(json.dumps(data, indent=2, default=str))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def worker(backend, output):
    import numpy as np
    import torch
    from diffusers import PNDMScheduler, StableDiffusionPipeline
    from astra_v2.omniroute_image_assets import image_quality_report

    started = time.monotonic()
    row = dict(GATES, backend=backend, render_completed=False, model=MODEL,
               model_revision=REVISION, prompt=PROMPT, negative_prompt="",
               width=512, height=512, steps=20, guidance_scale=7.5,
               precision="float32", code_revision=os.getenv("GITHUB_SHA", "local"))
    try:
        torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
        arr = np.load(output / "initial-latents.npy", allow_pickle=False)
        if arr.shape != (1, 4, 64, 64) or arr.dtype != np.float32 or not np.isfinite(arr).all():
            raise ValueError("Invalid initial latent tensor")
        row["latent_sha256"] = sha(arr.tobytes())
        row["packages"] = {n: importlib.metadata.version(n) for n in
                           ("torch", "diffusers", "transformers", "optimum-intel", "openvino", "numpy")}
        if backend == "pytorch":
            pipe = StableDiffusionPipeline.from_pretrained(
                MODEL, revision=REVISION, torch_dtype=torch.float32).to("cpu")
        else:
            from optimum.intel import OVStableDiffusionPipeline
            pipe = OVStableDiffusionPipeline.from_pretrained(
                MODEL, revision=REVISION, export=True, compile=False,
                device="CPU", load_in_8bit=False,
                ov_config={"INFERENCE_PRECISION_HINT": "f32"})
            pipe.reshape(batch_size=1, height=512, width=512, num_images_per_prompt=1)
            pipe.compile()
        # Explicitly reconstruct the same scheduler from the pinned source config.
        config = json.loads((output / "scheduler.json").read_text())
        pipe.scheduler = PNDMScheduler.from_config(config)
        row["scheduler_config"] = dict(pipe.scheduler.config)
        row["setup_seconds"] = round(time.monotonic() - started, 2)
        inference = time.monotonic()
        with torch.inference_mode():
            result = pipe(PROMPT, negative_prompt="", height=512, width=512,
                          num_inference_steps=20, guidance_scale=7.5,
                          latents=torch.from_numpy(arr.copy()),
                          generator=torch.Generator(device="cpu").manual_seed(42))
        row["inference_seconds"] = round(time.monotonic() - inference, 2)
        image = result.images[0]
        target = output / (backend + ".png")
        image.save(target)
        raw = target.read_bytes()
        row.update(render_completed=True, output=target.name, image_sha256=sha(raw),
                   quality=image_quality_report(raw, "background"),
                   nsfw_content_detected=result.nsfw_content_detected)
    except Exception as exc:
        row["error_type"] = type(exc).__name__
        raise
    finally:
        row["elapsed_seconds"] = round(time.monotonic() - started, 2)
        row["process_peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        save(output / (backend + ".json"), row)


def run(output):
    import numpy as np
    import torch
    from diffusers import PNDMScheduler

    output.mkdir(parents=True, exist_ok=True)
    report = dict(GATES, cases=[], technical_pair_completed=False,
                  model=MODEL, model_revision=REVISION, prompt=PROMPT)
    try:
        # Save one unscaled tensor, then reload a copy in each isolated process.
        arr = torch.randn((1, 4, 64, 64),
                          generator=torch.Generator(device="cpu").manual_seed(42),
                          dtype=torch.float32).numpy()
        np.save(output / "initial-latents.npy", arr, allow_pickle=False)
        report["latent_sha256"] = sha(arr.tobytes())
        scheduler = PNDMScheduler.from_pretrained(MODEL, subfolder="scheduler", revision=REVISION)
        save(output / "scheduler.json", dict(scheduler.config))
        for backend in ("pytorch", "openvino"):
            # Process exit releases model memory before the next backend loads.
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "tools.experimental_backend_parity",
                     "--worker", backend, "--output", str(output)],
                    timeout=600, check=False)
                status = {"backend": backend, "exit_code": result.returncode}
            except subprocess.TimeoutExpired:
                status = {"backend": backend, "timeout": True}
            path = output / (backend + ".json")
            if path.exists():
                status["result"] = json.loads(path.read_text())
            report["cases"].append(status)
            save(output / "parity.json", report)
        rows = [c.get("result", {}) for c in report["cases"]]
        report["technical_pair_completed"] = (
            len(rows) == 2
            and all(c.get("exit_code") == 0 for c in report["cases"])
            and all(r.get("render_completed") and r.get("latent_sha256") == report["latent_sha256"] for r in rows)
            and rows[0].get("scheduler_config") == rows[1].get("scheduler_config"))
    finally:
        save(output / "parity.json", report)
    return report["technical_pair_completed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=("pytorch", "openvino"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/experimental-openvino/parity"))
    args = parser.parse_args()
    if args.worker:
        worker(args.worker, args.output)
    else:
        raise SystemExit(0 if run(args.output) else 1)
