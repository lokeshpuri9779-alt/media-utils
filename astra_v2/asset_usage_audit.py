"""Per-shot evidence of actual asset-pack compositing in ASTRA Studio.

Records only frames that pass through the production compositor. A restored
inventory, selection plan, or successful Actions job alone is not evidence
that artwork was rendered. The receipt deliberately distinguishes those cases.
"""
from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from PIL import ImageChops


_ACTIVE = ContextVar("astra_asset_pack_audit", default=None)


def begin(story, shot_count):
    """Start a fresh candidate audit; do not reuse evidence across stories."""
    if os.getenv("ASTRA_ASSET_PACK_ENABLED") != "1" or os.getenv("ASTRA_ASSET_PACK_AUDIT") != "1":
        _ACTIVE.set(None)
        return False
    _ACTIVE.set({
        "content_id": str(story.get("content_id") or ""),
        "title": str(story.get("title") or ""),
        "shot_count": int(shot_count),
        "shots": {},
    })
    return True


def observing(shot_number):
    state = _ACTIVE.get()
    return state is not None and shot_number is not None and int(shot_number) not in state["shots"]


def observe(shot_number, analysis, status, identity, *, asset=None, before=None, after=None):
    """Record first actual compositor invocation of a shot, not a planned pick."""
    if not observing(shot_number):
        return
    state = _ACTIVE.get()
    number = int(shot_number)
    decision = {
        "shot": number,
        "scene": analysis.get("scene"),
        "scene_source": analysis.get("source_field"),
        "matched_term": analysis.get("matched_term"),
        "identity_sha256": hashlib.sha256(str(identity).encode("utf-8")).hexdigest(),
        "status": status,
        "asset": None,
        "pixel_changed": False,
    }
    if asset is not None:
        decision["asset"] = {
            k: asset[k] for k in ("id", "path", "sha256", "license", "source", "artist")
            if k in asset
        }
        if before is None or after is None:
            raise ValueError("rendered asset evidence requires both compositor frames")
        # Pixel-level evidence from the actual background-compositing operation.
        # This does not claim a decoded video comparison or full semantic fit.
        changed = ImageChops.difference(before.convert("RGB"), after.convert("RGB")).getbbox() is not None
        decision["pixel_changed"] = changed
        decision["status"] = "composited" if changed else "selected_no_pixel_change"
    state["shots"][number] = decision
    print("ASTRA_ASSET_SHOT_EVIDENCE=" + json.dumps(decision, sort_keys=True), flush=True)


def finish(video_path, *, renderer, expected_shots=None):
    """After encoding succeeds, link the actual MP4 hash to each shot decision."""
    state = _ACTIVE.get()
    _ACTIVE.set(None)
    if state is None:
        return None
    count = state["shot_count"]
    if expected_shots is not None and int(expected_shots) != count:
        raise RuntimeError("asset audit plan length changed")
    shots = [state["shots"].get(i) for i in range(1, count + 1)]
    if not shots or any(row is None for row in shots):
        raise RuntimeError("asset audit incomplete: production compositor did not observe every shot")
    if any(row["status"] in ("manifest_missing", "selected_no_pixel_change") for row in shots):
        raise RuntimeError("asset audit: missing validated pack or ineffective compositing")
    path = Path(video_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("asset audit requires a successful nonempty encoded MP4")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    counts = {}
    for row in shots:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    result = {
        "schema_version": 1,
        "content_id": state["content_id"],
        "title": state["title"],
        "renderer": renderer,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "shot_count": count,
        "composited_shots": counts.get("composited", 0),
        "statuses": counts,
        "video_sha256": h.hexdigest(),
        "video_bytes": path.stat().st_size,
        "evidence_scope": (
            "Per-shot background source hash and pixel difference measured inside "
            "the actual Studio frame compositor, linked to the encoded MP4 hash. "
            "Not proof of foreground asset use, semantic accuracy, or decoded YouTube pixels."
        ),
        "shots": shots,
    }
    directory = Path(os.getenv("ASTRA_ASSET_AUDIT_DIR", "runtime-health/asset-usage"))
    directory.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", state["content_id"])[:72] or "untitled"
    suffix = hashlib.sha256(state["content_id"].encode("utf-8")).hexdigest()[:12]
    receipt = directory / f"{safe}-{suffix}.json"
    receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("ASTRA_ASSET_USAGE_RECEIPT=" + json.dumps({
        "path": str(receipt), "content_id": result["content_id"],
        "shot_count": count, "composited_shots": result["composited_shots"],
        "video_sha256": result["video_sha256"],
    }, sort_keys=True), flush=True)
    return {"path": str(receipt), "shot_count": count,
            "composited_shots": result["composited_shots"],
            "video_sha256": result["video_sha256"], "statuses": counts}
