"""Hosted-video adapter. Unknown billing is blocked before any request."""
from __future__ import annotations
import os

# Populate only after verifying the deployed account cannot incur charges,
# model terms, endpoint, and quota behavior. A 'free' model name is not proof.
VERIFIED_FREE_ROUTES: frozenset[tuple[str, str]] = frozenset()


def configuration():
    return (os.getenv("OMNIROUTE_BASE_URL", "").rstrip("/"),
            os.getenv("OMNIROUTE_API_KEY", ""))


def readiness(model: str = "") -> dict:
    base, _ = configuration()
    blockers = []
    if not base:
        blockers.append("omniroute_endpoint_not_configured")
    if not model or "/" not in model:
        blockers.append("provider_prefixed_video_model_required")
    if (base, model) not in VERIFIED_FREE_ROUTES:
        blockers.append("zero_cost_video_route_not_verified")
    return {"status": "blocked" if blockers else "configured",
            "blockers": blockers, "generation_attempted": False}


def generate_video(prompt: str, model: str, **kwargs):
    if not model or "/" not in model:
        raise ValueError("Use provider-prefixed OmniRoute video model")
    if os.getenv("ASTRA_ALLOW_PAID_VIDEO", "false").lower() == "true":
        raise RuntimeError("Paid video remains disabled by Astra policy")
    check = readiness(model)
    if check["blockers"]:
        raise RuntimeError("Video blocked: " + ", ".join(check["blockers"]))
    base, key = configuration()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    payload = {**kwargs, "model": model, "prompt": prompt}
    import requests
    response = requests.post(f"{base}/videos/generations", headers=headers,
                             json=payload, timeout=120, allow_redirects=False)
    if 300 <= response.status_code < 400:
        raise RuntimeError("Video gateway redirect refused")
    response.raise_for_status()
    return response.json()


def policy():
    return {"execution": "hosted_upstream_via_omniroute",
            "local_gpu_required": False, "paid_fallback": False,
            "private_canary": True, "quality_gate_required": True}


if __name__ == "__main__":
    import json
    print(json.dumps(readiness(os.getenv("ASTRA_OMNI_VIDEO_MODEL", "")), indent=2))
