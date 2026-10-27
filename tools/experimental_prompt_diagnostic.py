"""One prompt-pair intervention, compared with saved run 40537578850."""
import json
from pathlib import Path

from tools.experimental_backend_parity import GATES, MODEL, REVISION, save, sha, worker

POSITIVE = "A single red toy fire engine, side view, one complete vehicle with attached wheels and ladder, fully visible, centered on a plain white studio background."
NEGATIVE = "multiple vehicles, duplicate, detached parts, disassembled, collage, text, letters, watermark, colored background, people"
BASELINE_LATENT_SHA256 = "e97f3de04c7c6ba86354db4402b91d4402ede9c72aabed29a96dd7d635a798ba"


def run(output=Path("artifacts/experimental-openvino/prompt-test")):
    import numpy as np
    import torch
    from diffusers import PNDMScheduler

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = dict(GATES, baseline_run=40537578850, prompt=POSITIVE,
                  negative_prompt=NEGATIVE, seed=42, model=MODEL,
                  model_revision=REVISION, technical_render_completed=False,
                  intervention="positive_and_negative_prompt_pair")
    try:
        arr = torch.randn((1, 4, 64, 64),
                          generator=torch.Generator(device="cpu").manual_seed(42),
                          dtype=torch.float32).numpy()
        report["latent_sha256"] = sha(arr.tobytes())
        if report["latent_sha256"] != BASELINE_LATENT_SHA256:
            raise ValueError("Initial noise differs from saved baseline")
        np.save(output / "initial-latents.npy", arr, allow_pickle=False)
        scheduler = PNDMScheduler.from_pretrained(MODEL, subfolder="scheduler", revision=REVISION)
        save(output / "scheduler.json", dict(scheduler.config))
        worker("openvino", output, prompt=POSITIVE, negative_prompt=NEGATIVE)
        row = json.loads((output / "openvino.json").read_text())
        report["result"] = row
        report["technical_render_completed"] = (
            row.get("render_completed") is True
            and row.get("latent_sha256") == BASELINE_LATENT_SHA256
            and row.get("prompt") == POSITIVE and row.get("negative_prompt") == NEGATIVE)
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        raise
    finally:
        save(output / "prompt-test.json", report)
    return report["technical_render_completed"]


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
