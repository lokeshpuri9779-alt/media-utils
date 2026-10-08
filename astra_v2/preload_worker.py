"""Render one approved original video ahead of publishing, no YouTube writes."""
from __future__ import annotations
import json
import os
import tempfile
import time
from pathlib import Path

from astra_v2.control import STATE_FILE, read_json, state_for_day
from astra_v2.creative import CreativeSkip, make_candidate
from astra_v2.preload_queue import artifacts, prepare


def main():
    started = time.monotonic()
    state = state_for_day(read_json(STATE_FILE))
    queue = artifacts()
    queue_checked = time.monotonic()
    target = max(1, min(24, int(os.getenv("ASTRA_PRELOAD_BUFFER", "6"))))
    if len(queue) >= target:
        print("ASTRA_PRELOAD="+json.dumps({"outcome":"buffer_full","count":len(queue)}))
        return
    excluded = set(state.get("published", {})) | set(state.get("reserved", {}))
    excluded.update(x.get("content_id", "") for x in state.get("pending", {}).values())
    # Reuse the already-fetched artifact listing: avoid a second GitHub API call.
    excluded.update(str(a['name'])[len('astra-preloaded-'):] for a in queue)
    # The renderer's own creative director and independent media QA must pass.
    with tempfile.TemporaryDirectory(prefix="astra-preload-") as tmp:
        video = Path(tmp) / "render.mp4"
        try:
            candidate = make_candidate(video, excluded, set())
        except CreativeSkip as exc:
            print("ASTRA_PRELOAD="+json.dumps({"outcome":"no_approved_candidate","reason":str(exc)[:100]}))
            return
        rendered = time.monotonic()
        if candidate["content_id"] in excluded:
            raise RuntimeError("Duplicate preloaded content ID")
        package = prepare(video, candidate)
        destination = Path("preload-package")
        destination.mkdir(exist_ok=True)
        for name in ("candidate.json", "video.mp4"):
            (destination / name).write_bytes((package / name).read_bytes())
        packaged = time.monotonic()
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write("content_id="+candidate["content_id"]+"\n")
        print("ASTRA_PRELOAD="+json.dumps({"outcome":"ready","content_id":candidate["content_id"],
                                            "buffer_before":len(queue),
                                            "timing_seconds":{"queue_lookup":round(queue_checked-started,2),
                                            "render_and_qa":round(rendered-queue_checked,2),
                                            "packaging":round(packaged-rendered,2)}}))


if __name__ == "__main__":
    main()
