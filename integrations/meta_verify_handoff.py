"""Verify a Meta publishing handoff before any uploader uses it.

Never uploads. Rejects changed media, malformed metadata and failed media gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
try:
    from integrations.meta_publish_gate import validate
except ModuleNotFoundError:
    from meta_publish_gate import validate

def verify(handoff: Path) -> dict:
    try:
        payload = json.loads(handoff.read_text(encoding="utf-8"))
        if payload.get("schema") != "astra-meta-handoff-v1":
            raise ValueError("Unknown handoff schema")
        if payload.get("uploaded") is not False or payload.get("ready_for_publisher_review") is not True:
            raise ValueError("Handoff not eligible")
        if not isinstance(payload.get("title"), str) or not payload["title"].strip():
            raise ValueError("Missing title")
        expected = payload.get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid SHA-256")
        video = Path(payload["video"])
        if not video.is_file():
            raise ValueError("Video file missing")
        digest = hashlib.sha256()
        with video.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError("Video changed since validation")
        check = validate(video, require_audio=True, min_duration=10)
        if not check["ready"]:
            raise ValueError("Media gate failed: " + "; ".join(check["errors"]))
        return {"verified": True, "video": str(video), "sha256": expected, "title": payload["title"]}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return {"verified": False, "error": str(exc)}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path)
    args = parser.parse_args()
    result = verify(args.handoff)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["verified"] else 1)

if __name__ == "__main__":
    main()
