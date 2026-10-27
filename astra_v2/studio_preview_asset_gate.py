"""Fail-closed Studio preview QA from the actual compositor/MP4 receipt.

A successful asset-pack restore or a selection log alone is not proof of use.
This check does not approve semantics or publish anything.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys


MARKER = "ASTRA_ASSET_USAGE_RECEIPT="


def verify_asset_pack_use(log_path, video_path):
    log = Path(log_path)
    video = Path(video_path)
    if not log.is_file():
        raise ValueError("missing_studio_render_log")
    if not video.is_file() or video.stat().st_size == 0:
        raise ValueError("missing_nonempty_studio_mp4")
    entries = [line.split(MARKER, 1)[1].strip()
               for line in log.read_text(encoding="utf-8").splitlines()
               if MARKER in line]
    if len(entries) != 1:
        raise ValueError("expected_exactly_one_compositor_receipt")
    try:
        summary = json.loads(entries[0])
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_compositor_receipt_log") from exc
    if not isinstance(summary, dict):
        raise ValueError("invalid_compositor_receipt_log")
    receipt_path = summary.get("path")
    if not isinstance(receipt_path, str) or not receipt_path:
        raise ValueError("missing_compositor_receipt_path")
    receipt_file = Path(receipt_path)
    if not receipt_file.is_file():
        raise ValueError("missing_compositor_receipt_file")
    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("invalid_compositor_receipt_file") from exc
    if not isinstance(receipt, dict):
        raise ValueError("invalid_compositor_receipt_file")
    count = receipt.get("shot_count")
    used = receipt.get("composited_shots")
    shots = receipt.get("shots")
    if (type(count) is not int or count < 1 or
            type(used) is not int or not 1 <= used <= count or
            not isinstance(shots, list) or len(shots) != count):
        raise ValueError("no_verified_composited_backgrounds")
    verified = sum(
        type(row) is dict and row.get("status") == "composited"
        and row.get("pixel_changed") is True
        and isinstance(row.get("asset"), dict)
        and isinstance(row["asset"].get("sha256"), str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", row["asset"]["sha256"]))
        for row in shots
    )
    if verified != used:
        raise ValueError("compositor_receipt_shot_mismatch")
    sha = hashlib.sha256()
    with video.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    actual = sha.hexdigest()
    if (receipt.get("video_sha256") != actual or
            summary.get("video_sha256") != actual or
            summary.get("shot_count") != count or
            summary.get("composited_shots") != used):
        raise ValueError("compositor_receipt_mp4_mismatch")
    return {"status": "pass", "shot_count": count,
            "composited_shots": used, "video_sha256": actual,
            "semantic_quality": "not_verified"}


if __name__ == "__main__":
    print("ASTRA_STUDIO_ASSET_GATE=" + json.dumps(
        verify_asset_pack_use(sys.argv[1], sys.argv[2]), sort_keys=True))
