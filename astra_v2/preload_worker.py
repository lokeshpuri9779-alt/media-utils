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
    # Artifact presence does not imply publishability: older packages can fail
    # current policy, media QA, or freshness checks. Never let a raw artifact
    # count permanently starve production of new original Shorts.
    if len(usable) >= target and not long_lane:
        print("ASTRA_PRELOAD_BUFFER_UNVERIFIED=" + json.dumps({
            "usable_count": len(usable), "target": target,
            "action": "attempt_new_approved_render",
        }))
    # Carry recently published YouTube content IDs into the renderer exclusion
    # set. This prevents rebuilding an ID that the publisher would reject.
    # Fail closed to the existing local-state checks if this optional snapshot
    # is unavailable; the publisher independently checks YouTube before upload.
    snapshot = Path("astra_recent_youtube_ids.json")
    if snapshot.is_file():
        try:
            payload = json.loads(snapshot.read_text(encoding="utf-8"))
            ids = payload.get("ids", [])
            if not isinstance(ids, list):
                raise ValueError("Invalid YouTube ID snapshot")
            live_exclusions = {x for x in ids if isinstance(x, str) and x.strip()}
            excluded.update(live_exclusions)
            print("ASTRA_PRELOAD_YOUTUBE_EXCLUSIONS=" + str(len(live_exclusions)))
        except (OSError, ValueError, TypeError) as exc:
            print("ASTRA_PRELOAD_YOUTUBE_SNAPSHOT_INVALID=" + type(exc).__name__)
    # Read the live channel before rendering: a queued candidate can already
    # have been published without appearing in the local journal.
    try:
        from astra_v2.run import channel_config
        from astra_v2.youtube import Youtube
        _, expected_channel_id = channel_config()
        with Youtube(expected_channel_id) as youtube:
            channel = youtube.authorize()
            recent_ids, _ = youtube.recent(channel)
        excluded.update(recent_ids)
        print("ASTRA_PRELOAD_LIVE_YOUTUBE_EXCLUSIONS=" + str(len(recent_ids)))
    except Exception as exc:
        # Publisher still enforces the authoritative live duplicate check.
        print("ASTRA_PRELOAD_LIVE_YOUTUBE_UNAVAILABLE=" + type(exc).__name__)
    # Only *scheduled* non-canary Shorts lanes can skip an expensive render
    # when the recent buffer meets the target and a bounded sample passes
    # ZIP hash and current independent publication policy. A raw artifact
    # count alone is never sufficient. On any uncertainty, render as before.
    from astra_v2.preload_saturation import scheduled_shorts_skip, print_decision
    saturation = scheduled_shorts_skip(excluded_ids=excluded)
    print_decision(saturation)
    if saturation["skip"]:
        print("ASTRA_PRELOAD=" + json.dumps({
            "outcome": "skipped_verified_saturation",
            "reason": saturation["reason"],
            "publisher_approval": False,
        }, sort_keys=True))
        return

    # Exclude queued content only AFTER evaluating the still-usable buffer.
    # Previously this exclusion happened before the saturation audit, making
    # every existing artifact disappear from its candidate set and returning
    # preflight_eligible=0 even for healthy recent packages.
    # The render itself still excludes every queued ID: no duplicate episodes.
    excluded.update(str(item["name"])[len("astra-preloaded-"):] for item in usable)
    if serialized:
        for number in range(1, 5):
            cid = f"rayvan-season-01-episode-{number:02d}"
            queued = any(str(a["name"]) == "astra-preloaded-" + cid for a in queue)
            print("ASTRA_SERIES_ELIGIBILITY=" + json.dumps({
                "episode": number, "published": cid in state.get("published", {}),
                "queued_artifact": queued, "excluded": cid in excluded,
            }))

    # Optional immutable reviewed-art handoff; never enables publishing or
    # chooses/approves stories. Missing or corrupted receipts fail closed.
    from astra_v2.preload_art_receipt import restore_for_preload
    restore_for_preload()
    # The renderer's own creative director and independent media QA must pass.
    with tempfile.TemporaryDirectory(prefix="astra-preload-") as tmp:
        video = Path(tmp) / "render.mp4"
        try:
            # Keep Shorts lanes intact. Only a deliberately enabled lane zero
            # may attempt the licensed, QA-gated long-form renderer. An absent
            # or rejected long candidate must never starve the Shorts backlog.
            candidate = None
            if long_lane:
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
                if os.getenv("ASTRA_LONG_ONLY", "0") == "1":
                    print("ASTRA_LONG_PRELOAD_SKIP=no_approved_long_episode")
                    return
                candidate = make_candidate(video, excluded, set())
        except CreativeSkip as exc:
            print("ASTRA_PRELOAD="+json.dumps({"outcome":"no_approved_candidate","reason":str(exc)[:100]}))
            return
        rendered = time.monotonic()
        if candidate["content_id"] in excluded:
            raise RuntimeError("Duplicate preloaded content ID")
        # Independent media proof after the real Studio renderer returns,
        # before archiving or offering the package to the publisher.
        from astra_v2.creative import inspect_video
        media_proof = inspect_video(video, fmt="long" if candidate.get("format") == "long" else "short")
        print("ASTRA_PRODUCTION_MEDIA_VERIFIED=" + json.dumps({
            "content_id": candidate["content_id"], **media_proof}, sort_keys=True))
        package = prepare(video, candidate)
        from astra_v2.adaptive_package_archive import archive_preload_if_enabled
        archive_preload_if_enabled(package)
        destination = Path("preload-package")
        destination.mkdir(exist_ok=True)
        for name in ("candidate.json", "video.mp4", "cover.jpg", "cover_wide.jpg"):
            if (package / name).is_file():
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
