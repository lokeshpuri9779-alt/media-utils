"""Render one approved original video ahead of publishing, no YouTube writes."""
from __future__ import annotations
import json
import os
import tempfile
import time
from pathlib import Path

from astra_v2.control import STATE_FILE, read_json, state_for_day
from astra_v2.creative import CreativeSkip, make_candidate, make_long_candidate
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
    # Long-form has a separate daily lane: a full Shorts buffer must not
    # prevent its first approved episode from ever being prepared.
    long_lane = (os.getenv("ASTRA_LONG_ENABLED", "0") == "1"
                 and int(os.getenv("ASTRA_PRELOAD_LANE", "0")) == 0)
    long_queued = any(str(a.get("name", "")).startswith("astra-preloaded-")
                      and str(a.get("name", ""))[len("astra-preloaded-"):].startswith(("planet-clocks-", "trend-brief-"))
                      for a in usable)
    if len(usable) >= target and (not long_lane or long_queued):
        print("ASTRA_PRELOAD="+json.dumps({"outcome":"buffer_full","usable_count":len(usable),"total_artifacts":len(queue)}))
        return
    # Reuse the already-fetched artifact listing: avoid a second GitHub API call.
    excluded.update(str(item["name"])[len("astra-preloaded-"):] for item in usable)
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
            # Keep Shorts lanes intact. Only a deliberately enabled lane zero
            # may attempt the licensed, QA-gated long-form renderer. An absent
            # or rejected long candidate must never starve the Shorts backlog.
            candidate = None
            if long_lane and not long_queued:
                # The analytics refresh does not populate trend_snapshot.
                # Fetch source-linked trends for this render only; fail closed
                # when upstream data is missing or insufficiently sourced.
                try:
                    from datetime import datetime
                    from zoneinfo import ZoneInfo
                    import cloud_once as legacy
                    from longform_trends import available
                    now = datetime.now(ZoneInfo("Asia/Kolkata"))
                    trends = legacy.fetch_trends(now)
                    if trends and available(trends):
                        perf = legacy.load_performance()
                        perf["trend_snapshot"] = {
                            "checked_at": now.isoformat(), "items": trends[:120]}
                        legacy.save_performance(perf)
                        print("ASTRA_LONG_RESEARCH=eligible_sourced_topics")
                    else:
                        print("ASTRA_LONG_RESEARCH=no_eligible_sourced_topics")
                except Exception as research_error:
                    print("ASTRA_LONG_RESEARCH_ERROR=" + type(research_error).__name__
                          + ": " + str(research_error)[:150])
                try:
                    candidate = make_long_candidate(video, excluded, set())
                    if candidate is None:
                        print("ASTRA_LONG_PRELOAD_SKIP=no_eligible_long_episode")
                except CreativeSkip as exc:
                    print("ASTRA_LONG_PRELOAD_SKIP=" + str(exc)[:150])
            if candidate is None:
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
