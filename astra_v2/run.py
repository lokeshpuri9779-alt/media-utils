"""ASTRA V2 publication controller: single run, durable journal, verifiable URLs."""
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from astra_v2.control import (
    QUOTA_REASONS, REPORT_FILE, STATE_FILE, due, quota_resume, parse_time,
    read_json, state_for_day, utcnow, write_json,
)
from astra_v2.creative import CreativeSkip, make_candidate
from astra_v2.youtube import Youtube, YoutubeError
from astra_v2.long_cadence import long_upload_due as historical_long_upload_due
from astra_v2.publication_quality import publication_rejection


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
                "genre": item.get("genre", ""), "renderer": item.get("renderer") or "unknown",
            }
            legacy.record_video(video_id, item.get("title", "RAYVAN Short"))
            state["published"][cid] = {"video_id": video_id, "confirmed_at": utcnow().isoformat(),
                                        "uploaded_at": item.get("uploaded_at"),
                                        "format": item.get("format", "short"),
                                        "title": item.get("title", ""),
                                        "plot_key": item.get("plot_key", ""),
                                        "plot_fingerprint": item.get("plot_fingerprint", ""),
                                        "story_beats": item.get("story_beats") or [],
                                        "renderer": item.get("renderer") or "unknown"}
            # Record only API-confirmed public, processed uploads. A failed
            # history write must not misclassify an already-published video.
            try:
                from astra_v2.verified_story_history import record_confirmed
                recorded = record_confirmed(
                    os.getenv("ASTRA_STORY_HISTORY_PATH", "astra_story_history.json"),
                    cid, state["published"][cid])
                print("ASTRA_VERIFIED_STORY_HISTORY=" + ("recorded" if recorded else "already_present"))
            except (OSError, ValueError, TypeError) as history_error:
                print("ASTRA_VERIFIED_STORY_HISTORY=unavailable:" + type(history_error).__name__)
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


def long_upload_due(state, now, spacing_hours=24):
    """Conservative per-format cooldown, including uploads still processing."""
    latest = []
    for entry in (state.get("published") or {}).values():
        if isinstance(entry, dict) and entry.get("format") == "long":
            instant = parse_time(entry.get("uploaded_at") or entry.get("confirmed_at"))
            if instant:
                latest.append(instant)
    for entry in (state.get("pending") or {}).values():
        if isinstance(entry, dict) and entry.get("format") == "long":
            instant = parse_time(entry.get("uploaded_at"))
            if instant:
                latest.append(instant)
    for entry in (state.get("reserved") or {}).values():
        if isinstance(entry, dict) and entry.get("format") == "long":
            instant = parse_time(entry.get("at"))
            if instant:
                latest.append(instant)
    return not latest or now - max(latest) >= timedelta(hours=spacing_hours)


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
            # Learn from real YouTube views/likes/comments on a bounded cadence,
            # even if this scheduled slot is not due to publish. This is
            # observation, never purchased traffic or artificial engagement.
            last_feedback = parse_time(state.get("last_feedback_attempt_at"))
            if not last_feedback or utcnow() - last_feedback >= timedelta(hours=12):
                state["last_feedback_attempt_at"] = utcnow().isoformat()
                try:
                    import cloud_once as legacy
                    legacy.refresh_performance()
                    # Run the existing private Analytics collector and update
                    # channel learning on the same bounded feedback cadence.
                    from autonomy import refresh_analytics
                    from channel_memory import refresh_channel_memory
                    learning = legacy.load_performance()
                    refresh_analytics(learning, datetime.now(ZoneInfo("Asia/Kolkata")))
                    memory = refresh_channel_memory(learning)
                    legacy.save_performance(learning)
                    analytics_state = learning.get("analytics_state") or {}
                    from astra_v2.stage_feedback import record
                    record("analytics", "private_reports", "pass" if analytics_state.get("videos_updated", 0) else "unknown", evidence={"status": analytics_state.get("status"), "videos_updated": analytics_state.get("videos_updated", 0)})
                    record("learning", "channel_memory", "pass" if memory.get("video_count", 0) else "unknown", evidence={"video_count": memory.get("video_count", 0)})
                    report["feedback"] = {
                        "analytics_status": analytics_state.get("status", "unknown"),
                        "videos_updated": analytics_state.get("videos_updated", 0),
                        "queries_succeeded": analytics_state.get("queries_succeeded", 0),
                        "channel_memory_videos": memory.get("video_count", 0),
                    }
                except Exception as feedback_error:
                    report["feedback"] = "unavailable_" + type(feedback_error).__name__
            limit = min(100, max(1, int(os.getenv("ASTRA_MAX_DAILY_UPLOADS", "100"))))
            interval = max(5, int(os.getenv("ASTRA_MIN_UPLOAD_INTERVAL_MINUTES", "5")))
            allowed, reason = due(state, utcnow(), limit=limit, spacing_minutes=interval)
            if not allowed:
                report.update(outcome="skipped", reason=reason)
                return report
            long_due = historical_long_upload_due(state, utcnow(), spacing_hours=12, performance=read_json("performance.json"))
            report["longform_due"] = bool(long_due)
            print("ASTRA_LONGFORM_DUE=" + str(bool(long_due)).lower())
            live_ids, live_titles = youtube.recent(youtube_channel)
            previous_ids = set(state["published"]) | set(state.get("reserved", {}))
            previous_ids.update(item.get("content_id", "") for item in state["pending"].values())
            print("ASTRA_QUEUE_EXCLUSIONS=" + json.dumps({"state_ids": len(previous_ids), "youtube_ids": len(live_ids), "anthology_matches": [{"content_id": cid, "state": cid in previous_ids, "youtube": cid in live_ids} for cid in ("rayvan-anthology-90c111ee3cab7400", "rayvan-anthology-535144f2435abf94")]}))
            with tempfile.TemporaryDirectory(prefix="astra-v2-") as temp:
                video = Path(temp) / "short.mp4"
                try:
                    # Prefer previously rendered, approved MP4s from the durable
                    # queue; never skip duplicate/format/channel safety checks.
                    candidate = None
                    candidate_from_preload = False
                    # Shorts remain the primary publisher. Never render a long
                    # episode synchronously in this lane: a slow render could
                    # delay or suppress scheduled Shorts.
                    # Long-form uploads may only use independently pre-rendered,
                    # quality-approved queue artifacts.
                    if long_due:
                        report["longform_selection"] = "pre_rendered_queue_only"
                        print("ASTRA_LONGFORM_SELECTION=pre_rendered_queue_only")
                    # Warehouse intake is opt-in. No implicit fallback after a claim:
                    # a failed restore must not silently render/upload another item.
                    if candidate is None and os.getenv("ASTRA_WAREHOUSE_PUBLISH", "0") == "1":
                        from astra_v2.warehouse_preload import take as take_warehouse
                        candidate = take_warehouse(video)
                        if candidate is not None:
                            from astra_v2.creative import inspect_video
                            candidate["media"] = inspect_video(video, candidate["format"])
                            candidate_from_preload = True
                    if candidate is None and os.getenv("ASTRA_WAREHOUSE_PUBLISH", "0") != "1" and os.getenv("ASTRA_PRELOAD_ENABLED", "1") == "1":
                        try:
                            from astra_v2.preload_queue import take
                            candidate = take(previous_ids | live_ids, live_titles, video, allow_long=long_due)
                        except Exception as queue_error:
                            report["queue_error_type"] = type(queue_error).__name__
                            print("ASTRA_PRELOAD_FALLBACK=" + type(queue_error).__name__)
                            import traceback
                            print("ASTRA_PRELOAD_EXCEPTION_DETAIL=" + str(queue_error)[:500])
                            traceback.print_exc()
                    if candidate is None:
                        if os.getenv("ASTRA_PRELOAD_ONLY", "0") == "1":
                            report.update(outcome="skipped", reason=("preload_queue_error" if report.get("queue_error_type") else "preload_queue_empty"))
                            return report
                        candidate = make_candidate(video, previous_ids | live_ids, live_titles)
                    else:
                        candidate_from_preload = bool(candidate.get("queue_artifact_id") or candidate.get("warehouse_claim"))
                        if candidate_from_preload:
                            print("ASTRA_PRELOAD_CONSUMED=" + candidate["content_id"])
                except CreativeSkip as exc:
                    from astra_v2.stage_feedback import record
                    record("quality", "candidate_selection", "fail", evidence={"reason": str(exc)[:200]}, action="Diagnose story supply and creative gate failures")
                    report.update(outcome="quality_skip", reason=str(exc)[:250], story_selection=getattr(exc, "selection", None) or {})
                    return report
                if candidate.get("format") == "long" and not historical_long_upload_due(
                    state, utcnow(), spacing_hours=12, performance=read_json("performance.json")):
                    report.update(outcome="skipped", reason="longform_12h_cooldown")
                    return report
                rejection = publication_rejection(candidate)
                if rejection and candidate_from_preload and os.getenv("ASTRA_PRELOAD_ONLY", "0") != "1":
                    # Old queue artifacts can predate the current publication
                    # policy. Never upload them; render a fresh approved story
                    # instead of wasting every scheduled slot on stale media.
                    print("ASTRA_PRELOAD_REJECTED=" + json.dumps({
                        "content_id": candidate.get("content_id"),
                        "reason": rejection, "action": "fresh_candidate_fallback",
                    }))
                    try:
                        candidate = make_candidate(video, previous_ids | live_ids, live_titles)
                    except CreativeSkip as exc:
                        report.update(outcome="quality_skip", reason=str(exc)[:250], story_selection=getattr(exc, "selection", None) or {})
                        return report
                    rejection = publication_rejection(candidate)
                if rejection:
                    report.update(outcome="quality_skip", reason=rejection)
                    return report
                cid = candidate["content_id"]
                title = candidate["title"]
                if cid in live_ids | previous_ids or title.casefold().strip() in live_titles:
                    report.update(outcome="duplicate_blocked", content_id=cid)
                    return report
                # Report whether character memory is eligible for this Short.
                # This is diagnostic only: it never changes upload eligibility.
                report["character_memory"] = (
                    "approved" if candidate.get("character_approved") is True
                    and candidate.get("format") == "short"
                    and isinstance(candidate.get("character_id"), str)
                    and bool(candidate.get("character_id"))
                    else "not_approved_or_missing_identity"
                )
                # Optional continuity metadata must never abort a valid upload.
                # Invalid approved records are diagnosed and skipped; publication
                # policy, duplicate checks, and verified persistence stay intact.
                if candidate.get("character_approved") is True and candidate.get("format") == "short":
                    try:
                        from astra_v2.character_manifest_bridge import build_character_manifests
                        from astra_v2.character_bootstrap import register_approved_character
                        from astra_v2.character_snapshot import read_snapshot
                        snapshot_path = Path("character-continuity.json")
                        snapshot = (
                            read_snapshot(snapshot_path) if snapshot_path.is_file()
                            else {"version": 1, "characters": {}}
                        )
                        character_id = candidate.get("character_id")
                        manifest_dir = Path("runtime-health")
                        manifest_dir.mkdir(parents=True, exist_ok=True)
                        if character_id not in snapshot["characters"]:
                            staged = register_approved_character(snapshot, candidate)
                            first_state = staged["characters"][character_id]
                            build_character_manifests(candidate, first_state)
                            write_json(manifest_dir / "character-first-candidate.json", {
                                "content_id": cid,
                                "character_id": character_id,
                                "character_name": candidate["character_name"],
                                "character_approved": True,
                                "format": "short",
                                "character_episode": candidate["character_episode"],
                            })
                            report["character_memory"] = "first_episode_staged"
                        else:
                            proposal, episode = build_character_manifests(
                                candidate, snapshot["characters"][character_id]
                            )
                            write_json(manifest_dir / "character-proposal.json", proposal)
                            write_json(manifest_dir / "character-episode.json", episode)
                            report["character_memory"] = "existing_episode_staged"
                    except (ValueError, TypeError, KeyError) as exc:
                        report["character_memory"] = "invalid_approved_metadata"
                        report["character_memory_error"] = type(exc).__name__
                        print("ASTRA_CHARACTER_MEMORY=invalid_approved_metadata", type(exc).__name__)
                description = candidate["description"] + "\nASTRA-V2-ID:" + cid
                # Reserve identity and interval BEFORE upload; never auto-retry an
                # indeterminate transfer as this risks a duplicate public video.
                state.setdefault("reserved", {})[cid] = {
                    "at": utcnow().isoformat(), "title": title, "format": candidate["format"],
                    "plot_key": candidate.get("plot_key", ""),
                    "plot_fingerprint": candidate.get("plot_fingerprint", ""),
                    "story_beats": candidate.get("story_beats") or [],
                    "renderer": candidate.get("renderer") or "unknown",
                    "result": "transfer_pending",
                }
                state["last_attempt_at"] = utcnow().isoformat()
                state["attempts"] += 1
                write_json(STATE_FILE, state)
                # A warehouse reservation is not publication permission. Never upload
                # while this experimental handoff is incomplete.
                if candidate.get("warehouse_claim"):
                    raise RuntimeError("warehouse_publisher_confirmation_not_enabled")
                video_id = youtube.upload(
                    video, title, description, candidate["synthetic"],
                    made_for_kids=candidate.get("made_for_kids"))
                state["reserved"][cid]["result"] = "accepted"
                state["pending"][video_id] = {
                    "content_id": cid, "title": title, "day": state["day"],
                    "uploaded_at": utcnow().isoformat(),
                    "genre": candidate["genre"], "format": candidate["format"],
                    "plot_key": candidate.get("plot_key", ""),
                    "plot_fingerprint": candidate.get("plot_fingerprint", ""),
                    "story_beats": candidate.get("story_beats") or [],
                    "renderer": candidate.get("renderer") or "unknown",
                }
                write_json(STATE_FILE, state)
                result = youtube.status(video_id)
                if result.get("privacyStatus") != "public":
                    raise RuntimeError("YouTube did not confirm public visibility: review uploaded video.")
                # Thumbnail failures must not duplicate or invalidate an accepted upload.
                # YouTube's custom-thumbnail endpoint is for eligible long-form videos;
                # Shorts cannot be assigned arbitrary cover files here.
                if candidate.get("format") == "long":
                    wide_cover = video.with_name(video.stem + "_cover_wide.jpg")
                    if wide_cover.is_file():
                        try:
                            youtube.set_thumbnail(video_id, wide_cover)
                            report["thumbnail"] = "applied"
                        except Exception as thumbnail_error:
                            report["thumbnail"] = "not_applied_" + type(thumbnail_error).__name__
                    else:
                        report["thumbnail"] = "cover_missing"
                confirmed = reconcile(youtube, state)
                report.update(
                    outcome="published" if video_id in confirmed else "processing",
                    video_url="https://www.youtube.com/watch?v=" + video_id,
                    content_id=cid, media=candidate["media"],
                    renderer=candidate.get("renderer") or "unknown",
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
        # Persist a bounded, non-sensitive production outcome so scheduled-run
        # failures remain diagnosable even when Actions logs are unavailable.
        state["last_production_result"] = {
            "at": report["at"],
            "outcome": str(report["outcome"])[:80],
            "reason": str(report.get("reason") or "")[:250],
            "content_id": str(report.get("content_id") or "")[:160],
            "video_url": str(report.get("video_url") or "")[:250],
            "story_selection": report.get("story_selection") or {},
        }
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
