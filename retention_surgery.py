from __future__ import annotations

"""Retention-aware scene surgery for Astra Shorts.

Produces bounded editorial operations from a finished render report. The module
never mutates source stories in place and never removes protected payoff/evidence
beats. It is deterministic so CI and production make the same decision.
"""

from copy import deepcopy

PROTECTED_BEATS = {"reveal", "evidence", "payoff"}
OPTIONAL_DROP_PRIORITY = {
    "contrast": 0,
    "map": 1,
    "mechanism": 2,
    "consequence": 3,
    "uncertainty": 4,
    "build": 5,
}


def diagnose_scenes(render_report: dict) -> dict:
    scenes = render_report.get("scenes") or []
    rows = []
    for index, scene in enumerate(scenes):
        duration = float(scene.get("duration") or 0)
        beat = str(scene.get("story_beat") or "")
        role = str(scene.get("director_role") or "")
        rows.append({
            "index": index,
            "beat": beat,
            "role": role,
            "duration": round(duration, 3),
            "protected": beat in PROTECTED_BEATS,
            "too_long": duration > 3.2,
            "very_long": duration > 4.2,
        })

    total = sum(x["duration"] for x in rows)
    max_scene = max((x["duration"] for x in rows), default=0.0)
    avg_scene = total / len(rows) if rows else 0.0
    payoff_index = next((x["index"] for x in rows if x["beat"] == "payoff"), None)
    payoff_late = payoff_index is not None and len(rows) >= 5 and payoff_index >= len(rows) - 1

    return {
        "scene_count": len(rows),
        "total_duration": round(total, 3),
        "avg_scene_duration": round(avg_scene, 3),
        "max_scene_duration": round(max_scene, 3),
        "payoff_index": payoff_index,
        "payoff_late": payoff_late,
        "scenes": rows,
    }


def propose_surgery(render_report: dict) -> dict:
    diag = diagnose_scenes(render_report)
    ops = []

    # First: shorten the longest non-protected scenes.
    candidates = [
        x for x in diag["scenes"]
        if not x["protected"] and x["duration"] > 2.6
    ]
    candidates.sort(key=lambda x: x["duration"], reverse=True)
    for row in candidates[:2]:
        ops.append({
            "op": "shorten",
            "index": row["index"],
            "target_duration": round(max(1.35, min(2.35, row["duration"] * 0.72)), 2),
            "reason": "long_optional_beat",
        })

    # If pacing remains structurally heavy, drop at most one optional beat.
    if diag["scene_count"] >= 6 and (diag["avg_scene_duration"] > 2.5 or diag["max_scene_duration"] > 4.2):
        droppable = [
            x for x in diag["scenes"]
            if not x["protected"] and x["beat"] in OPTIONAL_DROP_PRIORITY
        ]
        if droppable:
            victim = min(droppable, key=lambda x: (OPTIONAL_DROP_PRIORITY[x["beat"]], -x["duration"]))
            ops.append({
                "op": "drop",
                "index": victim["index"],
                "reason": "compress_middle",
            })

    # If the payoff is last in a long sequence, move it one slot earlier, but
    # never ahead of source evidence.
    if diag["payoff_late"] and diag["scene_count"] >= 6:
        payoff = diag["payoff_index"]
        evidence_indices = [x["index"] for x in diag["scenes"] if x["beat"] == "evidence"]
        target = max(evidence_indices + [0]) + 1
        if payoff is not None and target < payoff:
            ops.append({
                "op": "move",
                "from_index": payoff,
                "to_index": target,
                "reason": "surface_payoff_earlier",
            })

    return {
        "diagnosis": diag,
        "operations": ops[:4],
        "bounded": True,
        "protected_beats": sorted(PROTECTED_BEATS),
    }


def apply_surgery(plan: list[dict], surgery: dict) -> list[dict]:
    out = [deepcopy(x) for x in plan]
    operations = surgery.get("operations") or []

    # Apply duration edits before structural edits using original indexes.
    for op in operations:
        if op.get("op") != "shorten":
            continue
        i = int(op.get("index", -1))
        if 0 <= i < len(out):
            if str(out[i].get("story_beat") or "") in PROTECTED_BEATS:
                continue
            out[i]["min_duration"] = float(op["target_duration"])
            out[i]["retention_surgery"] = "shortened"

    # One drop maximum; protect critical beats.
    drops = [op for op in operations if op.get("op") == "drop"][:1]
    for op in sorted(drops, key=lambda x: int(x.get("index", -1)), reverse=True):
        i = int(op.get("index", -1))
        if 0 <= i < len(out) and str(out[i].get("story_beat") or "") not in PROTECTED_BEATS:
            out.pop(i)

    # Resolve move against the post-drop list by locating payoff by semantic beat.
    moves = [op for op in operations if op.get("op") == "move"][:1]
    if moves:
        payoff_i = next((i for i, x in enumerate(out) if x.get("story_beat") == "payoff"), None)
        if payoff_i is not None:
            evidence_i = max((i for i, x in enumerate(out) if x.get("story_beat") == "evidence"), default=-1)
            target = min(len(out) - 1, max(evidence_i + 1, int(moves[0].get("to_index", payoff_i))))
            if target < payoff_i:
                item = out.pop(payoff_i)
                out.insert(target, item)
                item["retention_surgery"] = "moved_earlier"

    return out
