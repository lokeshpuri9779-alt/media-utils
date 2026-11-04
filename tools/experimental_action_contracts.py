"""Review-only, data-driven timing contracts for isolated ASTRA story renders.

A shared verifier evaluates event traces from independent scenes. Each profile
declares its own fields, expected order, forbidden states and numeric trends.
This checks *reported action state*, NOT whether pixels depict the action.
It cannot approve, publish, or establish cinematic/semantic quality.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PROFILES = {
    "lighthouse": {
        "frames": 20,
        "events": [
            {"name": "spark_launch", "field": "energy_transfer_started",
             "op": "eq", "value": True, "window": [15, 16]},
            {"name": "energy_arrives", "field": "energy_front_at_beacon",
             "op": "eq", "value": True, "window": [17, 17]},
            {"name": "beacon_ignites", "field": "beacon_on",
             "op": "eq", "value": True, "window": [18, 19]},
        ],
        "guards": [
            {"name": "no_early_beam", "field": "energy_transfer_started",
             "op": "eq", "value": False, "window": [0, 14]},
            {"name": "beacon_dark_through_contact", "field": "beacon_on",
             "op": "eq", "value": False, "window": [0, 17]},
            {"name": "beacon_stays_on", "field": "beacon_on",
             "op": "eq", "value": True, "window": [18, 19]},
        ],
        "trends": [
            {"name": "energy_front_advances", "field": "energy_transfer_progress",
             "window": [15, 17], "direction": "up", "minimum_delta": .65},
        ],
    },
    "frog": {
        "frames": 32,
        "events": [
            {"name": "magnet_cast", "field": "magnet_clip_gap",
             "op": "gt", "value": 1.0, "window": [8, 8]},
            {"name": "magnet_attaches", "field": "magnet_clip_gap",
             "op": "lte", "value": .001, "window": [12, 12]},
            {"name": "airplane_lifted", "field": "plane_xyz.2",
             "op": "gte", "value": .5, "window": [17, 21]},
            {"name": "seed_in_pot", "field": "seed_xyz.0",
             "op": "gte", "value": 1.44, "window": [27, 27]},
            {"name": "rain_waters_seed", "field": "rain_streaks_visible",
             "op": "gte", "value": 7, "window": [27, 28],
             "allow_same_frame": True},
            {"name": "stem_sprouts", "field": "sprout_visible",
             "op": "eq", "value": True, "window": [29, 30]},
            {"name": "leaves_open", "field": "leaf_visible",
             "op": "eq", "value": True, "window": [31, 31]},
        ],
        "guards": [
            {"name": "plane_stays_trapped_before_contact", "field": "plane_xyz.2",
             "op": "eq", "value": .23, "window": [0, 12]},
            {"name": "no_early_sprout", "field": "sprout_visible",
             "op": "eq", "value": False, "window": [0, 28]},
            {"name": "no_early_leaves", "field": "leaf_visible",
             "op": "eq", "value": False, "window": [0, 30]},
            {"name": "rain_not_early", "field": "rain_streaks_visible",
             "op": "eq", "value": 0, "window": [0, 26]},
            {"name": "seed_at_soil_before_sprout", "field": "seed_xyz.2",
             "op": "lte", "value": .52, "window": [27, 28]},
            {"name": "seed_hidden_as_sprout_grows", "field": "seed_visible",
             "op": "eq", "value": False, "window": [29, 31]},
        ],
        "trends": [
            {"name": "magnet_approaches_without_reversal",
             "field": "magnet_clip_gap", "window": [8, 12],
             "direction": "down", "minimum_delta": 1.5},
            {"name": "plane_lifts_after_contact",
             "field": "plane_xyz.2", "window": [13, 21],
             "direction": "up", "minimum_delta": .4},
            {"name": "seed_moves_into_pot",
             "field": "seed_xyz.0", "window": [22, 27],
             "direction": "up", "minimum_delta": 1.4},
        ],
    },
}

OPERATORS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: type(a) in (int, float) and a > b,
    "gte": lambda a, b: type(a) in (int, float) and a >= b,
    "lt": lambda a, b: type(a) in (int, float) and a < b,
    "lte": lambda a, b: type(a) in (int, float) and a <= b,
}


def lookup(frame, field):
    """Read a declarative dotted path; numeric components index arrays."""
    value = frame
    for part in field.split("."):
        if isinstance(value, dict):
            value = value[part]
        elif isinstance(value, (list, tuple)) and part.isdigit():
            value = value[int(part)]
        else:
            raise KeyError(field)
    return value


def matches(frame, rule):
    try:
        value = lookup(frame, rule["field"])
        result = OPERATORS[rule["op"]](value, rule["value"])
        return bool(result)
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def monotonic(values, direction, minimum_delta):
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        return False
    if direction == "up":
        return (values[-1] - values[0] >= minimum_delta
                and all(a <= b for a, b in zip(values, values[1:])))
    if direction == "down":
        return (values[0] - values[-1] >= minimum_delta
                and all(a >= b for a, b in zip(values, values[1:])))
    raise ValueError("Invalid trend direction")


def evaluate(report, profile):
    if profile not in PROFILES:
        raise ValueError("Unsupported isolated review profile")
    contract = PROFILES[profile]
    frames = report.get("frames", [])
    count = contract["frames"]
    structural_ok = (
        isinstance(frames, list) and len(frames) == count
        and [f.get("frame") for f in frames if isinstance(f, dict)]
           == list(range(count))
        and report.get("success") is True
        and report.get("editorial_review_required") is True
        and all(report.get(flag) is False for flag in
                ("approved", "published", "production_ready", "paid_apis_used"))
    )
    if not structural_ok:
        return {
            "profile": profile, "passed": False, "events": {},
            "checks": {"trace_and_review_gates": False},
            "diagnostics": ["Incomplete trace, failed render or unsafe review flags"],
        }

    checks = {"trace_and_review_gates": True}
    events = {}
    last_frame = -1
    for rule in contract["events"]:
        lo, hi = rule["window"]
        qualifying = [i for i in range(lo, hi + 1) if matches(frames[i], rule)]
        event_frame = qualifying[0] if qualifying else None
        ordered = (event_frame is not None and
                   event_frame >= last_frame if rule.get("allow_same_frame")
                   else event_frame is not None and event_frame > last_frame)
        checks["event_" + rule["name"]] = bool(ordered)
        events[rule["name"]] = event_frame
        if ordered:
            last_frame = event_frame

    for rule in contract["guards"]:
        lo, hi = rule["window"]
        checks["guard_" + rule["name"]] = all(
            matches(frames[i], rule) for i in range(lo, hi + 1)
        )
    for rule in contract["trends"]:
        lo, hi = rule["window"]
        try:
            values = [lookup(frames[i], rule["field"]) for i in range(lo, hi + 1)]
            checks["trend_" + rule["name"]] = monotonic(
                values, rule["direction"], rule["minimum_delta"])
        except (KeyError, IndexError, TypeError, ValueError):
            checks["trend_" + rule["name"]] = False

    failed = sorted(k for k, passed in checks.items() if not passed)
    return {
        "profile": profile,
        "passed": not failed,
        "events": events,
        "checks": checks,
        "diagnostics": failed,
        "approved": False, "published": False, "production_ready": False,
        "paid_apis_used": False, "manual_review_required": True,
        "evidence_scope": "reported action-state metadata only",
        "semantic_quality": "not_verified",
        "cinematic_quality": "not_verified",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES))
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    result = evaluate(json.loads(options.report.read_text(encoding="utf-8")),
                      options.profile)
    target = options.output or options.report.with_name("action_contract.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("ASTRA_ACTION_CONTRACT=" + json.dumps(result), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
