from __future__ import annotations

"""Admission control for Astra character-video generation."""

from video_provider_policy import autonomous_provider_allowed, capability


def evaluate_generation_admission(
    provider_status: dict,
    *,
    publish_mode: str = "private",
    scene_count: int,
    max_scene_count: int = 8,
    max_target_seconds: float = 8.0,
    requested_scene_seconds: list[float] | None = None,
) -> dict:
    selected=str(provider_status.get("selected") or "")
    cap=capability(selected)
    failures=[]

    if not provider_status.get("ready"):
        failures.append("video backend not ready")
    if not selected:
        failures.append("no video provider selected")
    if selected and not autonomous_provider_allowed(selected):
        failures.append("selected provider is not approved for autonomous execution")
    if str(publish_mode).lower() != "private":
        failures.append("character generation is restricted to private-review mode")
    if scene_count <= 0:
        failures.append("storyboard has no scenes")
    if scene_count > max_scene_count:
        failures.append(f"scene count exceeds limit {max_scene_count}")

    for sec in requested_scene_seconds or []:
        try:
            value=float(sec)
        except Exception:
            failures.append("invalid scene duration")
            continue
        if value <= 0:
            failures.append("scene duration must be positive")
        if value > max_target_seconds:
            failures.append(f"scene duration exceeds {max_target_seconds:.1f}s limit")

    return {
        "allowed": not failures,
        "provider": selected,
        "provider_capability": cap,
        "publish_mode": str(publish_mode).lower(),
        "scene_count": scene_count,
        "failures": failures,
    }


def assert_generation_admitted(*args, **kwargs) -> dict:
    report=evaluate_generation_admission(*args, **kwargs)
    if not report["allowed"]:
        raise RuntimeError("Character generation admission denied: " + "; ".join(report["failures"]))
    return report
