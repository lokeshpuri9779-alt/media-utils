"""Metadata-only SDXL resource gate. Never downloads weights or renders images."""
import json
import os
from pathlib import Path
import shutil
import urllib.request

MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
REVISION = "462165984030d82259a11f4367a4eed129e94a7b"
GIB = 1024 ** 3
WEIGHTS = (
    "text_encoder/model.safetensors",
    "text_encoder_2/model.safetensors",
    "unet/diffusion_pytorch_model.safetensors",
    "vae/diffusion_pytorch_model.safetensors",
)


def assess(weight_bytes, available_bytes, disk_free_bytes):
    # Screening budgets, not claims about measured peak memory.
    required_ram = weight_bytes + 4 * GIB
    required_disk = 2 * weight_bytes + 2 * GIB
    reasons = []
    if available_bytes < required_ram:
        reasons.append("insufficient_available_ram_for_fp32_screening_budget")
    if disk_free_bytes < required_disk:
        reasons.append("insufficient_disk_for_source_and_export_screening_budget")
    return {
        "status": "blocked_before_download" if reasons else "eligible_for_bounded_load_test",
        "reasons": reasons,
        "required_available_ram_bytes": required_ram,
        "required_free_disk_bytes": required_disk,
        "budget_basis": "FP32 weights + 4 GiB RAM; source + export weights + 2 GiB disk",
    }


def main():
    output = Path("artifacts/experimental-openvino/sdxl-preflight.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "model": MODEL, "revision": REVISION, "precision": "FP32",
        "approved": False, "production_ready": False, "published": False,
        "manual_visual_review_required": True, "semantic_quality": "not_verified",
        "character_consistency": "not_verified", "weights_downloaded": False,
        "model_loaded": False, "images_generated": 0, "peak_loading_memory_bytes": None,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "commit": os.environ.get("GITHUB_SHA"),
        "scope": "metadata resource screening only; passing does not prove load/export/inference fit",
    }
    try:
        request = urllib.request.Request(
            f"https://huggingface.co/api/models/{MODEL}/revision/{REVISION}?blobs=true",
            headers={"User-Agent": "astra-review-only-resource-preflight"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            metadata = json.load(response)
        if metadata["sha"] != REVISION:
            raise ValueError("Model revision mismatch")
        sizes = {f["rfilename"]: f.get("size") for f in metadata["siblings"]}
        manifest = {name: sizes[name] for name in WEIGHTS}
        if any(not isinstance(size, int) or size <= 0 for size in manifest.values()):
            raise ValueError("Missing or invalid component size")
        mem = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            mem[key] = int(value.strip().split()[0]) * 1024
        available = mem["MemAvailable"]
        # Account for a tighter cgroup limit if this is executed in a container.
        for root in (Path("/sys/fs/cgroup"),):
            try:
                limit = (root / "memory.max").read_text().strip()
                current = int((root / "memory.current").read_text())
                if limit != "max":
                    available = min(available, max(0, int(limit) - current))
            except FileNotFoundError:
                pass
        disk = shutil.disk_usage(output.parent)
        weight_bytes = sum(manifest.values())
        report.update({
            "component_sizes_bytes": manifest, "weight_bytes": weight_bytes,
            "host_total_ram_bytes": mem["MemTotal"],
            "effective_available_ram_bytes": available, "disk_free_bytes": disk.free,
            **assess(weight_bytes, available, disk.free),
        })
    except Exception as exc:
        report.update(status="preflight_error", error=f"{type(exc).__name__}: {exc}")
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 1 if report["status"] == "preflight_error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
