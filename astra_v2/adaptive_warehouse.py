"""Persistent, adaptive, fail-closed inventory for preproduced ASTRA artifacts.

A single JSON state file is suitable for a single-writer pilot. Use a transactional
store with compare-and-swap for multi-run concurrency before live queue adoption.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

STAGES = ("proposed", "approved", "assets_ready", "rendered", "qa_passed", "reserved", "published")
NEXT = dict(zip(STAGES, STAGES[1:]))
TERMINAL = {"published", "failed"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def adaptive_target(daily_demand, production_lead_days, outage_days, safety_factor=1.5, maximum=10000):
    """Target changes with observed demand, lead time and outage duration."""
    if any(x < 0 for x in (daily_demand, production_lead_days, outage_days)) or safety_factor < 1:
        raise ValueError("invalid_forecast")
    import math
    return min(maximum, math.ceil(daily_demand * (production_lead_days + outage_days) * safety_factor))


class Warehouse:
    def __init__(self, state_path):
        self.path = Path(state_path)
        self.state = {"schema": 1, "items": {}}
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
        if self.state.get("schema") != 1 or not isinstance(self.state.get("items"), dict):
            raise ValueError("invalid_warehouse_schema")

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as stream:
            json.dump(self.state, stream, sort_keys=True, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, self.path)

    def register(self, content_id, *, story_sha256, reviewer, review_sha256, dependencies=None):
        if not all(isinstance(x, str) and x.strip() for x in
                   (content_id, story_sha256, reviewer, review_sha256)):
            raise ValueError("approval_evidence_required")
        if content_id in self.state["items"]:
            raise ValueError("duplicate_content_id")
        self.state["items"][content_id] = {
            "stage": "approved", "story_sha256": story_sha256,
            "reviewer": reviewer, "review_sha256": review_sha256,
            "dependencies": dependencies or {}, "artifact": None, "events": []
        }
        self._save()

    def advance(self, content_id, target, *, artifact_path=None, qa_report=None):
        item = self.state["items"][content_id]
        if target != NEXT.get(item["stage"]):
            raise ValueError("invalid_transition")
        if target == "qa_passed":
            if not isinstance(qa_report, dict) or qa_report.get("passed") is not True:
                raise ValueError("qa_evidence_required")
            if not artifact_path or not Path(artifact_path).is_file():
                raise ValueError("rendered_artifact_required")
            item["artifact"] = {"path": str(artifact_path), "sha256": sha256_file(artifact_path)}
            item["qa_report"] = qa_report
        if target == "reserved":
            self.verify(content_id)
        if target == "published":
            raise ValueError("use_confirm_published")
        item["stage"] = target
        item["events"].append({"stage": target, "at": datetime.now(timezone.utc).isoformat()})
        self._save()

    def verify(self, content_id):
        item = self.state["items"][content_id]
        artifact = item.get("artifact")
        if not artifact or not item.get("qa_report", {}).get("passed"):
            raise ValueError("not_ready")
        if sha256_file(artifact["path"]) != artifact["sha256"]:
            raise ValueError("artifact_integrity_failed")
        return artifact["path"]

    def ready(self):
        return [cid for cid, item in sorted(self.state["items"].items())
                if item["stage"] == "qa_passed"]

    def confirm_published(self, content_id, youtube_video_id):
        item = self.state["items"][content_id]
        if item["stage"] != "reserved" or not isinstance(youtube_video_id, str) or not youtube_video_id:
            raise ValueError("publication_confirmation_required")
        self.verify(content_id)
        item["stage"] = "published"
        item["youtube_video_id"] = youtube_video_id
        item["events"].append({"stage": "published", "at": datetime.now(timezone.utc).isoformat()})
        self._save()
