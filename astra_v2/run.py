"""ASTRA V2 publication controller: single run, durable journal, verifiable URLs."""
import json
import os
import tempfile
from pathlib import Path

from astra_v2.control import (
    QUOTA_REASONS, REPORT_FILE, STATE_FILE, due, quota_resume,
    read_json, state_for_day, utcnow, write_json,
)
from astra_v2.creative import CreativeSkip, make_candidate, make_long_candidate
from astra_v2.youtube import Youtube, YoutubeError


def channel_config():
    cfg = read_json("channels.json")
    key = os.getenv("ASTRA_CHANNEL", cfg.get("default", "rayvan"))
    channel = (cfg.get("channels") or {}).get(key)
    if not channel or not channel.get("publish_enabled", False):
        raise RuntimeError("Invalid or disabled publishing channel.")
    expected = str(channel.get("expected_channel_id") or "")
    if not expected.startswith("UC") or len(expected) < 15:
        raise RuntimeError("Expected YouTube channel ID is invalid.")
    return key, expected


def reconcile(youtube, state):
    verified = []
    for video_id, item in list(state["pending"].items()):
        status = youtube.status(video_id)
        visibility = status.get("privacyStatus")
        processing = status.get("uploadStatus")
        if visibility == "public" and processing == "processed":
            cid = item["content_id"]
            # Preserve the established learning database and public video feed.
            # Do not record a success until the API confirms public processing.
            import cloud_once as legacy
            legacy.CONTENT_META = {
                "content_id": cid, "format": item.get("format", "short"), "visibility": "public",
                "genre": item.get("genre", ""), "renderer": "astra-v2",
            }
            legacy.record_video(video_id, item.get("title", "RAYVAN Short"))
            state["published"][cid] = {"video_id": video_id, "confirmed_at": utcnow().isoformat(),
                                        "title": item.get("title", "")}
            if item.get("day") == state["day"]:
                state["confirmed_today"] += 1
            del state["pending"][video_id]
            verified.append(video_id)
        elif visibility == "private" or processing in ("failed", "rejected", "deleted"):
            state.setdefault("needs_review", {})[video_id] = {
                "reason": "video_not_public_or_processing_failed", "observed_at": utcnow().isoformat()
            }
            del state["pending"][video_id]
    return verified


def run():
    state = state_for_day(read_json(STATE_FILE))
    report = {"at": utcnow().isoformat(), "outcome": "starting",
              "video_url": None, "channel": None}
    try:
        channel_name, expected_id = channel_config()
        report["channel"] = channel_name
        with Youtube(expected_id) as youtube:
            youtube_channel = youtube.authorize()
            report["confirmed_prior"] = reconcile(youtube, state)
            limit = min(48, max(1, int(os.getenv("ASTRA_MAX_DAILY_UPLOADS", "48"))))
            interval = max(25, int(os.getenv("ASTRA_MIN_UPLOAD_INTERVAL_MINUTES", "25")))
            allowed, reason = due(state, utcnow(), limit=limit, spacing_minutes=interval)
            if not allowed:
                report.update(outcome="skipped", reason=reason)
                return report
            live_ids, live_titles = youtube.recent(youtube_channel)
            previous_ids = set(state["published"]) | set(state.get("reserved", {}))
            previous_ids.update(item.get("content_id", "") for item in state["pending"].values())
            with tempfile.TemporaryDirectory(prefix="astra-v2-") as temp:
                video = Path(temp) / "short.mp4"
                try:
                    candidate = (make_long_candidate(video, previous_ids | live_ids, live_titles)
                                 or make_candidate(video, previous_ids | live_ids, live_titles))
                except CreativeSkip as exc:
                    report.update(outcome="quality_skip", reason=str(exc)[:250])
                    return report
                cid = candidate["content_id"]
                title = candidate["title"]
                if cid in live_ids | previous_ids or title.casefold().strip() in live_titles:
                    report.update(outcome="duplicate_blocked", content_id=cid)
                    return report
                description = candidate["description"] + "\nASTRA-V2-ID:" + cid
                # Reserve identity and interval BEFORE upload; never auto-retry an
                # indeterminate transfer as this risks a duplicate public video.
                state.setdefault("reserved", {})[cid] = {
                    "at": utcnow().isoformat(), "title": title, "result": "transfer_pending",
                }
                state["last_attempt_at"] = utcnow().isoformat()
                state["attempts"] += 1
                write_json(STATE_FILE, state)
                video_id = youtube.upload(
                    video, title, description, candidate["synthetic"])
                state["reserved"][cid]["result"] = "accepted"
                state["pending"][video_id] = {
                    "content_id": cid, "title": title, "day": state["day"],
                    "uploaded_at": utcnow().isoformat(),
                    "genre": candidate["genre"], "format": candidate["format"],
                }
                write_json(STATE_FILE, state)
                result = youtube.status(video_id)
                if result.get("privacyStatus") != "public":
                    raise RuntimeError("YouTube did not confirm public visibility: review uploaded video.")
                confirmed = reconcile(youtube, state)
                report.update(
                    outcome="published" if video_id in confirmed else "processing",
                    video_url="https://www.youtube.com/watch?v=" + video_id,
                    content_id=cid, media=candidate["media"],
                )
                return report
    except YoutubeError as exc:
        state["last_error"] = str(exc)
        if exc.reason in QUOTA_REASONS:
            state["blocked_until"] = quota_resume(utcnow(), exc.reason).isoformat()
            state["quota_reason"] = exc.reason
            report.update(outcome="quota_pause", reason=exc.reason)
            return report
        report.update(outcome="failure", reason=str(exc))
        raise
    except Exception as exc:
        state["last_error"] = str(exc)[:300]
        report.update(outcome="failure", reason=str(exc)[:300])
        raise
    finally:
        state["last_outcome"] = report["outcome"]
        write_json(STATE_FILE, state)
        report.update(
            attempts_today=state["attempts"],
            confirmed_today=state["confirmed_today"],
            pending=len(state["pending"]),
            blocked_until=state.get("blocked_until") or None,
        )
        write_json(REPORT_FILE, report)
        print("ASTRA_V2_RESULT=" + json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    run()
