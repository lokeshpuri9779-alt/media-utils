"""Object-colored pixel tracks for the isolated frog rescue (review only).

Unlike generic frame-difference checks, this traces the largest contiguous
gold-colored fishing mechanism and the left edge of a pale airplane-shaped
region through fixed-camera shots. It cannot identify objects semantically:
an unrelated warm/pale prop could satisfy these proxies. No production gates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.experimental_visual_motion_audit import decode, green_pixels, SIZE, W, H, SCENES

WARM_ROI = (60, 305, 355, 348)
PAPER_ROI = (30, 250, 250, 355)
MAGNET_FRAMES = tuple(range(8, 13))
AIRPLANE_FRAMES = tuple(range(13, 22))
# Hand-calibrated from real PNG pixels; frame 25 excludes pot soil at x>=240.
# Stop before brown seed overlaps pot soil in later frames.
SEED_ROIS = {
    22: (64, 244, 125, 296),
    23: (83, 249, 145, 295),
    24: (140, 250, 196, 299),
    25: (192, 270, 239, 327),
}
SEED_MIN_PIXELS = {22: 175, 23: 175, 24: 35, 25: 175}
SPROUT_ROI = (195, 242, 325, 292)


def _assert_rgb(frame):
    if len(frame) != SIZE:
        raise ValueError("Wrong fixed-story RGB frame size")


def _is_warm(red, green, blue):
    return (red > 125 and green > 75 and red > green * 1.2
            and green > blue * 1.25 and red > blue * 1.8)


def _is_pale(red, green, blue):
    return (red > 145 and green > 135 and blue > 115
            and red > blue * 1.07 and red < green * 1.28
            and green > blue * 1.02)


def gold_region_center(frame):
    """Largest connected warm-color component, not declared Blender positions."""
    _assert_rgb(frame)
    left, top, right, bottom = WARM_ROI
    width, height = right - left, bottom - top
    foreground = bytearray(width * height)
    for yy in range(height):
        y = yy + top
        for xx in range(width):
            x = xx + left
            k = 3 * (y * W + x)
            if _is_warm(frame[k], frame[k + 1], frame[k + 2]):
                foreground[yy * width + xx] = 1

    visited = bytearray(len(foreground))
    best = (0, None)
    for pos in range(len(foreground)):
        if not foreground[pos] or visited[pos]:
            continue
        stack = [pos]
        visited[pos] = 1
        count, total_x = 0, 0
        while stack:
            current = stack.pop()
            yy, xx = divmod(current, width)
            count += 1
            total_x += xx + left
            for ny in (yy - 1, yy, yy + 1):
                if ny < 0 or ny >= height:
                    continue
                for nx in (xx - 1, xx, xx + 1):
                    if nx < 0 or nx >= width:
                        continue
                    other = ny * width + nx
                    if foreground[other] and not visited[other]:
                        visited[other] = 1
                        stack.append(other)
        if count > best[0]:
            best = (count, round(total_x / count, 2))
    return {"pixels": best[0], "center_x": best[1]}


def seed_brown_center(frame, roi):
    """Bounded RGB seed-color proxy, independent of renderer position data."""
    _assert_rgb(frame)
    left, top, right, bottom = roi
    if not (0 <= left < right <= W and 0 <= top < bottom <= H):
        raise ValueError("Invalid seed ROI")
    xs = []
    for y in range(top, bottom):
        for x in range(left, right):
            k = 3 * (y * W + x)
            red, green, blue = frame[k], frame[k + 1], frame[k + 2]
            if (67 < red < 185 and 42 < green < 138 and blue > 28
                    and red > green * 1.16 and red < green * 1.68
                    and blue > green * .65 and green > blue * 1.04):
                xs.append(x)
    return {"pixels": len(xs),
            "center_x": round(sum(xs) / len(xs), 2) if xs else None}


def pale_region_left(frame):
    """Leftmost bright cream-colored pixel in the airplane shot corridor."""
    _assert_rgb(frame)
    left, top, right, bottom = PAPER_ROI
    xs = []
    for y in range(top, bottom):
        for x in range(left, right):
            k = 3 * (y * W + x)
            if _is_pale(frame[k], frame[k + 1], frame[k + 2]):
                xs.append(x)
    return {"pixels": len(xs), "left_x": min(xs) if xs else None}


def score(frames, report):
    valid = (
        isinstance(frames, (list, tuple)) and len(frames) == 32
        and all(len(f) == SIZE for f in frames)
        and isinstance(report, dict)
        and report.get("success") is True
        and report.get("editorial_review_required") is True
        and report.get("semantic_quality") == "not_verified"
        and all(report.get(k) is False for k in
                ("approved", "published", "production_ready", "paid_apis_used"))
        and len(report.get("frames", [])) == 32
        and [r.get("frame") for r in report["frames"]] == list(range(32))
        and all(report["frames"][i]["phase"] == "rescue" for i in range(8, 22))
        and all(report["frames"][i]["camera_xyz"]
                == report["frames"][8]["camera_xyz"] for i in range(8, 22))
    )
    checks = {"review_only_fixed_camera_trace": valid}
    measurements = {}
    if valid:
        gold = {str(i): gold_region_center(frames[i]) for i in MAGNET_FRAMES}
        paper = {str(i): pale_region_left(frames[i]) for i in AIRPLANE_FRAMES}
        seed = {str(i): seed_brown_center(frames[i], roi)
                for i, roi in SEED_ROIS.items()}
        sprout = {str(i): green_pixels(frames[i], SPROUT_ROI)
                  for i in (28, 29, 30, 31)}
        measurements = {"magnet_gold": gold, "airplane_pale": paper,
                        "seed_brown": seed, "sprout_green": sprout}
        x = [gold[str(i)]["center_x"] for i in MAGNET_FRAMES]
        p = [paper[str(i)]["left_x"] for i in AIRPLANE_FRAMES]
        checks["magnet_golden_pixels_present"] = all(
            gold[str(i)]["pixels"] >= 70 and v is not None
            for i, v in zip(MAGNET_FRAMES, x))
        checks["gold_cluster_travels_leftward_to_clip"] = (
            all(v is not None for v in x)
            and all(a - b >= 24 for a, b in zip(x, x[1:]))
            and x[0] - x[-1] >= 170
        )
        checks["airplane_bright_pixels_present"] = all(
            paper[str(i)]["pixels"] >= 95 and v is not None
            for i, v in zip(AIRPLANE_FRAMES, p))
        checks["paper_region_moves_right_after_contact"] = (
            all(v is not None for v in p)
            and all(b > a for a, b in zip(p, p[1:]))
            and p[-1] - p[0] >= 125
        )
        seed_x = [seed[str(i)]["center_x"] for i in SEED_ROIS]
        checks["seed_brown_blob_before_soil"] = all(
            seed[str(i)]["pixels"] >= SEED_MIN_PIXELS[i]
            and seed[str(i)]["center_x"] is not None for i in SEED_ROIS
        )
        checks["seed_pixel_path_advances_toward_pot"] = (
            all(x is not None for x in seed_x)
            and all(b - a >= 12 for a, b in zip(seed_x, seed_x[1:]))
            and seed_x[-1] - seed_x[0] >= 105
        )
        checks["sprout_pixels_follow_seed_transfer"] = (
            sprout["28"] <= 5 and 80 <= sprout["29"] <= 500
            and 150 <= sprout["30"] <= 800
            and 800 <= sprout["31"] <= 5000
            and sprout["29"] < sprout["30"] < sprout["31"]
        )
        # Scene-specific color cues are not semantic recognition, especially
        # when brown seed pixels overlap the soil after frame 25.
    failed = sorted(name for name, state in checks.items() if not state)
    return {
        "experiment": "isolated frog colored-pixel object tracks",
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
        "measurements": measurements,
        "evidence_scope": "fixed-scene color/position proxies from actual RGB PNGs",
        "limitations": ("Fixed-scene color/position proxies cannot identify "
                        "objects semantically. Seed-colored pixels become "
                        "indistinguishable from pot soil after frame 25; "
                        "subject and cinematic quality require manual review."),
        "semantic_quality": "not_verified",
        "cinematic_quality": "not_verified",
        "manual_visual_review_required": True,
        "approved": False, "published": False,
        "production_ready": False, "paid_apis_used": False,
    }


def negative_controls(frames, report):
    unmodified = score(frames, report)
    if not unmodified["passed"]:
        raise AssertionError("Source pixel-track evidence must pass first")
    cases = []
    scenarios = (
        ("magnet_freezes", 10, 9, "gold_cluster_travels_leftward_to_clip"),
        ("magnet_reverses", 11, 8, "gold_cluster_travels_leftward_to_clip"),
        ("paper_airplane_stalls", 16, 15,
         "paper_region_moves_right_after_contact"),
        ("paper_airplane_returns_to_drain", 19, 13,
         "paper_region_moves_right_after_contact"),
        ("wrong_rescue_shot", 17, 31,
         "paper_region_moves_right_after_contact"),
        ("seed_pixels_erased", 24, None, "seed_brown_blob_before_soil"),
        ("seed_rewinds", 25, 22, "seed_pixel_path_advances_toward_pot"),
        ("sprout_appears_early", 28, 31, "sprout_pixels_follow_seed_transfer"),
        ("sprout_never_grows", 31, 28, "sprout_pixels_follow_seed_transfer"),
    )
    for name, destination, source, expected in scenarios:
        corrupted = list(frames)
        corrupted[destination] = frames[source] if source is not None else bytes(SIZE)
        result = score(corrupted, report)
        cases.append({
            "case": name,
            "rejected": result["passed"] is False and
                        result["checks"].get(expected) is False,
            "expected_detection": expected,
            "failed_checks": result["failed_checks"],
        })
    output = {
        "source_passed": True,
        "negative_case_count": len(cases),
        "all_corruptions_rejected": all(item["rejected"] for item in cases),
        "cases": cases,
        "manual_visual_review_required": True,
        "semantic_quality": "not_verified",
        "approved": False, "published": False,
        "production_ready": False, "paid_apis_used": False,
    }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.directory / "review.json").read_text())
    frames = decode(args.directory, SCENES["frog"]["frames"])
    audit = score(frames, report)
    controls = negative_controls(frames, report) if audit["passed"] else None
    args.output_directory.mkdir(parents=True, exist_ok=True)
    (args.output_directory / "object_pixel_tracks.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    if controls is not None:
        (args.output_directory / "object_pixel_negative_controls.json").write_text(
            json.dumps(controls, indent=2) + "\n", encoding="utf-8")
    print("ASTRA_FROG_OBJECT_PIXEL_TRACKS=" + json.dumps({
        "passed": audit["passed"], "checks": audit["checks"],
        "negative_controls": controls["all_corruptions_rejected"] if controls else False,
        "approved": False, "production_ready": False,
    }), flush=True)
    if not audit["passed"] or not controls["all_corruptions_rejected"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
