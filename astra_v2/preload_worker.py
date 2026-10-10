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
    # A reservation/pending upload is not an approved render. In serialized
    # preload mode, only confirmed publications and queued artifacts exclude
    # an episode; otherwise a stale reservation can starve every render lane.
    serialized = os.getenv("ASTRA_SERIALIZED_PRELOAD", "0") == "1"
    excluded = set(state.get("published", {}))
    if not serialized:
        excluded.update(state.get("reserved", {}))
        excluded.update(x.get("content_id", "") for x in state.get("pending", {}).values())
    usable = [a for a in queue if str(a["name"])[len("astra-preloaded-"):] not in excluded
              and (a.get("workflow_run") or {}).get("id")]
    print("ASTRA_QUEUE_COUNTS=" + json.dumps({"target": target, "usable": len(usable), "artifacts": len(queue)}))
    if len(usable) >= target:
        print("ASTRA_PRELOAD="+json.dumps({"outcome":"buffer_full","usable_count":len(usable),"total_artifacts":len(queue)}))
        return
    # Reuse the already-fetched artifact listing: avoid a second GitHub API call.
    excluded.update(str(a['name'])[len('astra-preloaded-'):] for a in queue)
    if serialized:
        for number in range(1, 5):
            cid = f"rayvan-season-01-episode-{number:02d}"
            queued = any(str(a["name"]) == "astra-preloaded-" + cid for a in queue)
            print("ASTRA_SERIES_ELIGIBILITY=" + json.dumps({
                "episode": number, "published": cid in state.get("published", {}),
                "queued_artifact": queued, "excluded": cid in excluded,
            }))
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
