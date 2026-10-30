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



def fiction_compositor_coverage_rejection(story, rendered):
    """Block audited fiction with unresolved backgrounds before upload.

    Pixel coverage is a necessary minimum, NOT semantic or editorial approval.
    Keep unaffected genres and installations without the optional audit unchanged.
    """
    if story.get("genre") != "fiction" or os.getenv("ASTRA_ASSET_PACK_AUDIT") != "1":
        return None
    receipt = rendered.get("asset_pack_usage") if isinstance(rendered, dict) else None
    if not isinstance(receipt, dict):
        return "fiction_asset_usage_evidence_missing"
    shots = receipt.get("shot_count")
    composited = receipt.get("composited_shots")
    if (type(shots) is not int or shots < 1 or
            type(composited) is not int or composited != shots):
        return "fiction_scene_background_coverage_incomplete"
    return None


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
        "asset_coverage_ratio": round(counts.get("composited", 0) / count, 4) if count else 0.0,
        "asset_coverage_status": "none" if not counts.get("composited", 0) else ("full" if counts.get("composited", 0) == count else "partial"),
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
    if result["asset_coverage_status"] == "none":
        print("ASTRA_ASSET_COVERAGE_WARNING=zero_verified_backgrounds_composited", flush=True)
    directory = Path(os.getenv("ASTRA_ASSET_AUDIT_DIR", "runtime-health/asset-usage"))
    directory.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", state["content_id"])[:72] or "untitled"
    suffix = hashlib.sha256(state["content_id"].encode("utf-8")).hexdigest()[:12]
    receipt = directory / f"{safe}-{suffix}.json"
    receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Review-only decoded MP4 samples. Never treat pixel evidence as semantic
    # approval or let a diagnostic failure alter publication eligibility.
    if os.getenv("ASTRA_VISUAL_REVIEW_SHEET") == "1":
        try:
            from astra_v2.render_contact_sheet import create_contact_sheet
            review_dir = Path(os.getenv(
                "ASTRA_VISUAL_REVIEW_DIR", "runtime-health/visual-review"))
            evidence = create_contact_sheet(path, review_dir / f"{safe}-{suffix}.jpg")
            if evidence["source_mp4_sha256"] != result["video_sha256"]:
                raise RuntimeError("review_frame_source_hash_mismatch")
            print("ASTRA_VISUAL_REVIEW_SHEET=" + json.dumps(
                evidence, sort_keys=True), flush=True)
        except Exception as exc:
            # Log only fixed diagnostic codes: never echo exception text, paths,
            # subprocess stderr, credentials, or other potentially private data.
            known_reasons = {
                "ffprobe_unavailable", "ffmpeg_unavailable",
                "missing_decoded_frame", "unexpected_sample_size",
                "review_frame_source_hash_mismatch",
            }
            reason = str(exc) if type(exc) is RuntimeError and str(exc) in known_reasons else "unspecified"
            print("ASTRA_VISUAL_REVIEW_SHEET=" + json.dumps({
                "status": "unavailable", "exception_type": type(exc).__name__,
                "reason": reason, "semantic_quality": "not_verified",
            }, sort_keys=True), flush=True)
    print("ASTRA_ASSET_USAGE_RECEIPT=" + json.dumps({
        "path": str(receipt), "content_id": result["content_id"],
        "shot_count": count, "composited_shots": result["composited_shots"],
        "video_sha256": result["video_sha256"],
    }, sort_keys=True), flush=True)
    return {"path": str(receipt), "shot_count": count,
            "composited_shots": result["composited_shots"],
            "video_sha256": result["video_sha256"], "statuses": counts,
            "asset_coverage_ratio": result["asset_coverage_ratio"],
            "asset_coverage_status": result["asset_coverage_status"]}
