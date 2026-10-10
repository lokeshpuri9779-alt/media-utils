"""Create a tamper-evident local publishing handoff only for validated videos.

This is NOT a YouTube uploader. A separate publisher must explicitly consume
the JSON and independently revalidate the file before calling YouTube.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
try:
    from integrations.meta_publish_gate import validate
except ModuleNotFoundError:
    from meta_publish_gate import validate

def prepare_handoff(video: Path, handoff: Path, title: str, description: str = "") -> dict:
    video = video.resolve()
    # Revoke any previous approval before attempting a new handoff.
    handoff.unlink(missing_ok=True)
    if not title.strip():
        raise ValueError("Video title is required")
    result = validate(video, require_audio=True, min_duration=10)
    if not result["ready"]:
        raise ValueError("Video rejected: " + "; ".join(result["errors"]))
    digest = hashlib.sha256()
    with video.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    payload = {
        "schema": "astra-meta-handoff-v1",
        "video": str(video),
        "sha256": digest.hexdigest(),
        "title": title.strip(),
        "description": description,
        "duration_seconds": result["duration_seconds"],
        "ready_for_publisher_review": True,
        "uploaded": False,
    }
    handoff.parent.mkdir(parents=True, exist_ok=True)
    tmp = handoff.with_suffix(handoff.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(handoff)
    return payload

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--handoff", type=Path, required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    a = p.parse_args()
    print(json.dumps(prepare_handoff(a.video, a.handoff, a.title, a.description), indent=2))

if __name__ == "__main__":
    main()
