"""Durable, bounded pre-render queue using private Actions artifacts.

The queue is opportunistic: if GitHub artifact API/storage is unavailable,
the normal publisher may still render on demand. Only accept artifacts from
this repository's own successful, trusted main-branch preload workflow.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

PREFIX = "astra-preloaded-"
MAX_BYTES = 200 * 1024 * 1024


def _studio_meets_floor(renderer, minimum):
    """Reject malformed and older Studio preload provenance, not fresh renders.

    No floor means legacy behavior. Compare dotted version numbers numerically
    (7.10.0 is newer than 7.2.0), never with lexical string comparison.
    """
    import re
    if not minimum:
        return True
    def parse(value):
        m = re.fullmatch(r"(?:studio-)?(\d+)\.(\d+)\.(\d+)", str(value or "").strip())
        return tuple(map(int, m.groups())) if m else None
    version = parse(renderer)
    floor = parse(minimum)
    if floor is None:
        raise ValueError("Invalid ASTRA_MIN_STUDIO_VERSION setting")
    return version is not None and version >= floor


def _api(path):
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True,
                            timeout=30, check=True)
    return json.loads(result.stdout)


def artifacts():
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not repo or "/" not in repo:
        return []
    matched = []
    seen = set()
    # GitHub's artifact listing is paginated. Keep a bounded scan, but
    # prioritize fresh renders even if older artifacts dominate the listing.
    for page in range(1, 31):
        data = _api(f"repos/{repo}/actions/artifacts?per_page=100&page={page}")
        batch = data.get("artifacts") if isinstance(data, dict) else None
        if not isinstance(batch, list):
            print("ASTRA_ARTIFACT_INVALID_PAGE=" + str(page))
            break
        for item in batch:
            if not isinstance(item, dict):
                continue
            workflow_run = item.get("workflow_run")
            if (not str(item.get("name") or "").startswith(PREFIX)
                    or item.get("expired", True)
                    or not isinstance(workflow_run, dict)
                    or workflow_run.get("head_branch") != "main"):
                continue
            key = item.get("id")
            if not isinstance(key, int) or isinstance(key, bool) or key <= 0:
                continue
            if key in seen:
                continue
            seen.add(key)
            matched.append(item)
        if len(batch) < 100:
            break
    matched.sort(key=_artifact_created_timestamp, reverse=True)
    print("ASTRA_ARTIFACT_DISCOVERY=" + json.dumps({"approved_artifacts": len(matched), "pages_scanned": page}))
    return matched



def inventory_snapshot(max_age_hours=None, now=None):
    """Metadata-only inventory; not proof of package or editorial validity."""
    if max_age_hours is None:
        max_age_hours = max(0, int(os.getenv("ASTRA_PRELOAD_MAX_AGE_HOURS", "48")))
    entries = artifacts()
    fresh = [entry for entry in entries if _artifact_fresh(entry, max_age_hours, now)]
    ids = {str(entry["name"])[len(PREFIX):] for entry in fresh}
    eligible_names = [entry for entry in fresh if str(entry.get("name", ""))[len(PREFIX):].strip()]
    return {
        "discovered_artifacts": len(entries),
        "fresh_artifacts": len(fresh),
        "unique_fresh_content_ids": len(ids),
        "fresh_named_artifacts": len(eligible_names),
        "stale_artifacts": len(entries) - len(fresh),
        "target_buffer": max(0, int(os.getenv("ASTRA_PRELOAD_BUFFER", "24"))),
        "freshness_hours": max_age_hours,
        "verification": "metadata_only_not_publishable_count",
    }



def inventory_eligibility_snapshot(excluded_ids=(), max_age_hours=None, now=None):
    """Bounded, non-downloading eligibility preflight; NOT package validation.

    Excludes consumed IDs and untrusted workflow runs. ZIP contents, editorial
    policy, media integrity and novelty still require the publisher's take().
    """
    if max_age_hours is None:
        max_age_hours = max(0, int(os.getenv("ASTRA_PRELOAD_MAX_AGE_HOURS", "48")))
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    excluded = set(excluded_ids)
    counts = {"fresh": 0, "excluded": 0, "invalid_id": 0,
              "untrusted_run": 0, "run_lookup_failed": 0,
              "preflight_eligible": 0}
    runs = {}
    seen = set()
    for entry in artifacts():
        if not _artifact_fresh(entry, max_age_hours, now):
            continue
        counts["fresh"] += 1
        cid = str(entry.get("name", ""))[len(PREFIX):]
        if not cid or "/" in cid or ".." in cid:
            counts["invalid_id"] += 1
            continue
        if cid in excluded or cid in seen:
            counts["excluded"] += 1
            continue
        seen.add(cid)
        run_id = (entry.get("workflow_run") or {}).get("id")
        if not repo or not run_id:
            counts["untrusted_run"] += 1
            continue
        if run_id not in runs:
            try:
                runs[run_id] = _api(f"repos/{repo}/actions/runs/{run_id}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                    OSError, ValueError, json.JSONDecodeError):
                runs[run_id] = None
        run = runs[run_id]
        if not isinstance(run, dict):
            counts["run_lookup_failed"] += 1
        elif (run.get("conclusion") != "success" or run.get("head_branch") != "main"
              or run.get("name") not in ("ASTRA V2 - Preload Approved Videos",
                                       "ASTRA V2 - Long-form Preload")):
            counts["untrusted_run"] += 1
        else:
            counts["preflight_eligible"] += 1
    return {
        **counts,
        "target_buffer": max(0, int(os.getenv("ASTRA_PRELOAD_BUFFER", "24"))),
        "verification": "preflight_only_package_and_policy_not_verified",
    }


def candidate_ids():
    return {str(a["name"])[len(PREFIX):] for a in artifacts()}


def valid_package_members(names):
    """Allow legacy video-only packages and verified optional JPEG covers."""
    names = set(names)
    return ({"candidate.json", "video.mp4"} <= names
            and names <= {"candidate.json", "video.mp4", "cover.jpg", "cover_wide.jpg"})


def prepare(path, candidate):
    """Write a self-describing package; called only after full creative QA."""
    from astra_v2.creative import inspect_video
    video = Path(path)
    fmt = candidate.get("format", "short")
    media = inspect_video(video, fmt)
    # Reject unreviewed template content before consuming artifact storage.
    from astra_v2.publication_quality import publication_rejection
    rejection = publication_rejection(candidate)
    if rejection:
        raise ValueError("Publication quality rejected: " + rejection)
    payload = {k: candidate[k] for k in (
        "content_id", "title", "description", "synthetic", "genre", "format")}
    if "made_for_kids" in candidate:
        if not isinstance(candidate["made_for_kids"], bool):
            raise ValueError("made_for_kids must be boolean")
        payload["made_for_kids"] = candidate["made_for_kids"]
    renderer = candidate.get("renderer")
    if not isinstance(renderer, str) or not renderer.strip() or renderer.strip() == "unknown":
        raise ValueError("Approved preload is missing verified renderer provenance")
    payload["renderer"] = renderer.strip()
    if fmt == "short":
        payload["plot_fingerprint"] = str(candidate.get("plot_fingerprint") or "")
        payload["plot_key"] = str(candidate.get("plot_key") or "")
        payload["story_beats"] = candidate.get("story_beats") or []
    video_bytes = video.read_bytes()
    payload["sha256"] = hashlib.sha256(video_bytes).hexdigest()
    payload["media"] = media
    package = video.parent / "preload-package"
    package.mkdir(exist_ok=True)
    (package / "candidate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (package / "video.mp4").write_bytes(video_bytes)
    for suffix, name in (("_cover.jpg", "cover.jpg"), ("_cover_wide.jpg", "cover_wide.jpg")):
        cover = video.with_name(video.stem + suffix)
        if cover.is_file() and 0 < cover.stat().st_size <= 5 * 1024 * 1024:
            (package / name).write_bytes(cover.read_bytes())
    return package


def _artifact_created_timestamp(entry):
    """Invalid GitHub timestamps must not crash the entire upload queue."""
    try:
        value = str(entry.get("created_at") or "1970-01-01T00:00:00Z")
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, OverflowError, OSError):
        return 0.0



def _artifact_fresh(entry, max_age_hours, now=None):
    """Reject old pre-renders when freshness policy is enabled."""
    if max_age_hours <= 0:
        return True
    created = _artifact_created_timestamp(entry)
    if created <= 0:
        return False
    current = (now or datetime.now(timezone.utc)).timestamp()
    return 0 <= current - created <= max_age_hours * 3600


def take(excluded_ids, excluded_titles, output, allow_long=True):
    """Get the newest eligible queued render. Return None for an empty queue.

    Corrupt/untrusted artifacts fail closed and are never published.
    """
    from astra_v2.creative import inspect_video
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    # Rendering can run in parallel; publication cannot skip story episodes.
    # Only confirmed published IDs unlock the following installment.
    from astra_v2.control import STATE_FILE, read_json, state_for_day
    published = set(state_for_day(read_json(STATE_FILE)).get("published", {}))
    # When the 12-hour long-form cadence is due, try approved long-form
    # artifacts first. Otherwise prefer Shorts and exclude cooling long-form.
    # Preserve newest-first order within each class.
    def priority(entry):
        is_long = str(entry.get("name", "")).startswith(
            ("astra-preloaded-planet-clocks-", "astra-preloaded-trend-brief-"))
        return (0 if (is_long and allow_long) or (not is_long and not allow_long) else 1,
                -_artifact_created_timestamp(entry))
    max_age_hours = max(0, int(os.getenv("ASTRA_PRELOAD_MAX_AGE_HOURS", "0")))
    # Several approved artifacts often belong to one four-lane preload run.
    # Verify each run once per queue scan rather than issuing duplicate API calls.
    trusted_runs = {}
    for entry in sorted(artifacts(), key=priority):
        if not _artifact_fresh(entry, max_age_hours):
            print("ASTRA_PRELOAD_STALE_SKIP=" + str(entry.get("name", "")))
            continue
        cid = str(entry["name"])[len(PREFIX):]
        if os.getenv("ASTRA_SERIES_PUBLICATION", "0") == "1" and not cid.startswith("rayvan-season-01-episode-"):
            continue
        if cid in excluded_ids or "/" in cid or ".." in cid:
            if cid.startswith("rayvan-anthology-"):
                print("ASTRA_ANTHOLOGY_SKIP=" + json.dumps({"content_id": cid, "reason": "duplicate_content_id" if cid in excluded_ids else "invalid_content_id"}))
            continue
        if cid.startswith("rayvan-season-01-episode-"):
            try:
                number = int(cid.rsplit("-", 1)[-1])
            except ValueError:
                continue
            if not 1 <= number <= 4:
                continue
            if any(f"rayvan-season-01-episode-{n:02d}" not in published
                   for n in range(1, number)):
                print("ASTRA_SERIES_WAITING_FOR_PUBLICATION=" + cid)
                continue
        run_id = (entry.get("workflow_run") or {}).get("id")
        if not run_id:
            continue
        if run_id not in trusted_runs:
            try:
                trusted_runs[run_id] = _api(f"repos/{repo}/actions/runs/{run_id}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                    OSError, ValueError, json.JSONDecodeError) as exc:
                # One missing or temporarily inaccessible preload run must not
                # prevent scanning other independently verified video artifacts.
                print("ASTRA_PRELOAD_RUN_LOOKUP_SKIP=" + json.dumps({
                    "workflow_run_id": run_id, "reason": type(exc).__name__}))
                trusted_runs[run_id] = None
        run = trusted_runs[run_id]
        if not isinstance(run, dict):
            continue
        if (run.get("conclusion") != "success"
                or run.get("head_branch") != "main"
                or run.get("name") not in ("ASTRA V2 - Preload Approved Videos", "ASTRA V2 - Long-form Preload")):
            if cid.startswith("rayvan-anthology-"):
                print("ASTRA_ANTHOLOGY_SKIP=" + json.dumps({"content_id": cid, "reason": "run_not_trusted", "run_status": run.get("conclusion")}))
            continue
        with tempfile.TemporaryDirectory(prefix="astra-queue-") as tmp:
            archive = Path(tmp) / "artifact.zip"
            with archive.open("wb") as dest:
                result = subprocess.run(
                    ["gh", "api", f"repos/{repo}/actions/artifacts/{entry['id']}/zip"],
                    stdout=dest, stderr=subprocess.PIPE, timeout=90, check=False)
            if result.returncode or archive.stat().st_size > MAX_BYTES:
                if cid.startswith("rayvan-anthology-"):
                    print("ASTRA_ANTHOLOGY_SKIP=" + json.dumps({"content_id": cid, "reason": "download_failed_or_oversized", "exit_code": result.returncode}))
                continue
            try:
                with zipfile.ZipFile(archive) as z:
                    names = set(z.namelist())
                    if not valid_package_members(names):
                        continue
                    if z.getinfo("video.mp4").file_size > MAX_BYTES:
                        continue
                    candidate = json.loads(z.read("candidate.json"))
                    # Artifact JSON is untrusted: malformed packages must not
                    # abort selection of other approved Shorts or long videos.
                    if not isinstance(candidate, dict):
                        print("ASTRA_PRELOAD_INVALID_CANDIDATE_TYPE=" + cid)
                        continue
                    if not all(isinstance(candidate.get(k), str) for k in
                               ("content_id", "title", "description", "genre", "format")):
                        print("ASTRA_PRELOAD_INVALID_CANDIDATE_FIELDS=" + cid)
                        continue
                    if candidate.get("content_id") != cid:
                        continue
                    if candidate.get("format") not in ("short", "long"):
                        continue
                    if run.get("name") == "ASTRA V2 - Long-form Preload" and candidate["format"] != "long":
                        continue
                    if candidate["format"] == "long" and not allow_long:
                        continue
                    if candidate.get("title", "").casefold().strip() in excluded_titles:
                        continue
                    # The controlled Studio 7.2 rollout must not consume an
                    # old 7.1 video just because its package is still fresh.
                    # Long-form remains unaffected by this Shorts-only floor.
                    floor = os.getenv("ASTRA_MIN_STUDIO_VERSION", "").strip()
                    if candidate["format"] == "short" and not _studio_meets_floor(candidate.get("renderer"), floor):
                        print("ASTRA_PRELOAD_OLD_STUDIO_SKIP=" + json.dumps({
                            "content_id": cid, "renderer": candidate.get("renderer") or "unknown",
                            "required": floor}))
                        continue
                    if not all(candidate.get(k) for k in ("title", "description", "content_id", "genre", "format")):
                        continue
                    # Reject non-Studio packages before extracting or probing MP4.
                    if (os.getenv("ASTRA_REQUIRE_STUDIO_PRELOAD", "0") == "1"
                            and not str(candidate.get("renderer") or "").startswith("studio-")):
                        print("ASTRA_PRELOAD_NON_STUDIO_SKIP=" + json.dumps({
                            "content_id": cid, "renderer": candidate.get("renderer") or "unknown"}))
                        continue
                    # Queue packages may have been created under older policy.
                    # Reject them here and keep scanning for approved artifacts,
                    # instead of returning the first stale package every run.
                    from astra_v2.publication_quality import publication_rejection
                    rejection = publication_rejection(candidate)
                    if rejection:
                        print("ASTRA_PRELOAD_POLICY_SKIP=" + json.dumps({
                            "content_id": cid, "reason": rejection,
                        }))
                        continue
                    if candidate["format"] == "short":
                        from astra_v2.shorts_novelty import is_near_duplicate
                        from astra_v2.creative import publisher_history_ids
                        journal = state_for_day(read_json(STATE_FILE))
                        if candidate.get("content_id") in publisher_history_ids(journal):
                            print("ASTRA_PRELOAD_DUPLICATE_ID_SKIP=" + cid)
                            continue
                        prior = [item for bucket in ("published", "pending", "reserved")
                                 for item in (journal.get(bucket) or {}).values()
                                 if isinstance(item, dict)]
                        if is_near_duplicate(candidate, prior):
                            print("ASTRA_PRELOAD_NOVELTY_SKIP=" + cid)
                            continue
                    video = z.read("video.mp4")
            except (ValueError, KeyError, zipfile.BadZipFile, json.JSONDecodeError):
                continue
            if hashlib.sha256(video).hexdigest() != candidate.get("sha256"):
                continue
            out = Path(output)
            out.write_bytes(video)
            try:
                media = inspect_video(out, candidate["format"])
            except Exception:
                out.unlink(missing_ok=True)
                continue
            # Recover optional covers for the publisher from trusted artifacts.
            for cover_name in ("cover.jpg", "cover_wide.jpg"):
                if cover_name in names:
                    try:
                        with zipfile.ZipFile(archive) as cover_zip:
                            cover_info = cover_zip.getinfo(cover_name)
                            if 0 < cover_info.file_size <= 5 * 1024 * 1024:
                                cover_path = out.with_name(out.stem + "_" + cover_name)
                                cover_path.write_bytes(cover_zip.read(cover_name))
                    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
                        pass
            candidate["media"] = media
            candidate["queue_artifact_id"] = entry["id"]
            if not isinstance(candidate.get("renderer"), str) or not candidate["renderer"].strip():
                print("ASTRA_PRELOAD_RENDERER_UNVERIFIED=" + json.dumps({
                    "content_id": cid, "artifact_id": entry["id"],
                    "workflow_run_id": run_id,
                }))
            return candidate
    return None
