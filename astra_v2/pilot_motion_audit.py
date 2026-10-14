"""Frame-motion diagnostics for the offline comedy pilot (no publishing).

Measures actual differences between sampled frames and writes inspectable
metrics. This is a technical diagnostic, not a subjective creative score.
"""
import json
from pathlib import Path
from PIL import ImageChops, ImageStat
from astra_v2.coordinated_development import frame


def compare_frames(a, b):
    if a.size != b.size:
        raise ValueError("frame size mismatch")
    # Downsample before computing robust mean absolute pixel change.
    left = a.convert("RGB").resize((136, 240))
    right = b.convert("RGB").resize((136, 240))
    difference = ImageChops.difference(left, right)
    means = ImageStat.Stat(difference).mean
    return round(sum(means) / (3 * 255), 6)


def audit(plan, output_path, fps=24, seconds_per_scene=3):
    if plan.get("pilot_type") != "offline_comedy":
        raise ValueError("motion audit restricted to isolated comedy pilot")
    if not 2 <= fps <= 24 or not 1 <= seconds_per_scene <= 10:
        raise ValueError("invalid timing")
    report = {"fps": fps, "seconds_per_scene": seconds_per_scene,
              "total_frames_expected": len(plan["scenes"]) * fps * seconds_per_scene,
              "scenes": [], "publication_allowed": False}
    for scene in plan["scenes"]:
        # Measure adjacent-frame motion at different moments. Static hold is
        # not always a failure; report the numbers rather than overfitting.
        probes = [max(1, int(fps * moment)) for moment in (.25, .75, 1.5, 2.25)
                  if moment < seconds_per_scene]
        readings = []
        for index in probes:
            t = index / fps
            prev = frame(scene, (index - 1) / fps)
            current = frame(scene, t)
            readings.append({"at_seconds": round(t, 3),
                             "changed_pixel_fraction_proxy": compare_frames(prev, current)})
        first = frame(scene, 0)
        last = frame(scene, seconds_per_scene - 1 / fps)
        report["scenes"].append({
            "scene": scene["scene"], "action": scene.get("action"),
            "adjacent_frame_differences": readings,
            "first_to_last_difference": compare_frames(first, last)
        })
    report["scene_count"] = len(report["scenes"])
    report["all_scenes_have_motion"] = all(
        scene["first_to_last_difference"] > .001 for scene in report["scenes"])
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2))
    return report
