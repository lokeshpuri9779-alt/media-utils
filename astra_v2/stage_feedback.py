"""Bounded, evidence-aware per-stage improvement journal for ASTRA Main.

A recorded observation is not proof of a successful improvement.
This module never changes publication gates or self-modifies code.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

STAGES = ("research", "story", "script", "hook", "characters", "visuals",
          "animation", "camera", "lighting", "audio", "captions", "pacing",
          "render", "quality", "metadata", "thumbnail", "publish",
          "analytics", "learning")
PATH = Path("astra_stage_feedback.json")
MAX_EVENTS = 600


def record(stage, element, outcome, *, evidence=None, action=None, candidate_id=None):
    if stage not in STAGES:
        raise ValueError("Unknown ASTRA stage")
    if outcome not in ("pass", "fail", "skip", "unknown", "improved", "regressed"):
        raise ValueError("Unknown ASTRA outcome")
    if outcome in ("improved", "regressed") and not evidence:
        raise ValueError("Improvement claims require measured evidence")
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    events = data.get("events")
    if not isinstance(events, list):
        events = []
    event = {
        "at": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "element": str(element)[:100],
        "outcome": outcome,
        "evidence": evidence if isinstance(evidence, (dict, list, int, float, bool)) else str(evidence or "")[:350],
        "proposed_action": str(action or "")[:250],
        "candidate_id": str(candidate_id or "")[:100],
    }
    events.append(event)
    data["schema_version"] = 1
    data["events"] = events[-MAX_EVENTS:]
    data["stage_counts"] = {
        key: {status: sum(1 for item in data["events"]
                          if item.get("stage") == key and item.get("outcome") == status)
              for status in ("pass", "fail", "skip", "unknown", "improved", "regressed")}
        for key in STAGES
    }
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return event
