"""Durable, bounded pre-render queue using private Actions artifacts.

The queue is opportunistic: if GitHub artifact API/storage is unavailable,
the normal publisher may still render on demand. Only accept artifacts from
this repository's own successful, trusted main-branch preload workflow.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

PREFIX = "astra-preloaded-"
MAX_BYTES = 200 * 1024 * 1024


def _api(path):
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True,
                            timeout=30, check=True)
    return json.loads(result.stdout)


def artifacts():
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not repo or "/" not in repo:
        return []
    matched = []
    for page in range(1, 11):
        data = _api(f"repos/{repo}/actions/artifacts?per_page=100&page={page}")
        batch = data.get("artifacts") or []
        matched.extend(x for x in batch
                       if isinstance(x, dict)
                       and str(x.get("name") or "").startswith(PREFIX)
                       and not x.get("expired", True)
                       and (x.get("workflow_run") or {}).get("head_branch") == "main")
        if len(batch) < 100:
            break
    return matched


def candidate_ids():
    return {str(a["name"])[len(PREFIX):] for a in artifacts()}


def prepare(path, candidate):
    """Write a self-describing package; called only after full creative QA."""
    from astra_v2.creative import inspect_video
    video = Path(path)
    fmt = candidate.get("format", "short")
    media = inspect_video(video, fmt)
    payload = {k: candidate[k] for k in (
        "content_id", "title", "description", "synthetic", "genre", "format")}
    payload["sha256"] = hashlib.sha256(video.read_bytes()).hexdigest()
    payload["media"] = media
    package = video.parent / "preload-package"
    package.mkdir(exist_ok=True)
    (package / "candidate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (package / "video.mp4").write_bytes(video.read_bytes())
    return package


def take(excluded_ids, excluded_titles, output):
    """Get the oldest valid queued render. Return None for an empty queue.

    Corrupt/untrusted artifacts fail closed and are never published.
    """
    from astra_v2.creative import inspect_video
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    # Rendering can run in parallel; publication cannot skip story episodes.
    # Only confirmed published IDs unlock the following installment.
    from astra_v2.control import STATE_FILE, read_json, state_for_day
    published = set(state_for_day(read_json(STATE_FILE)).get("published", {}))
    for entry in sorted(artifacts(), key=lambda a: a.get("created_at", "")):
        cid = str(entry["name"])[len(PREFIX):]
        if os.getenv("ASTRA_SERIES_PUBLICATION", "0") == "1" and not cid.startswith("rayvan-season-01-episode-"):
            continue
        if cid in excluded_ids or "/" in cid or ".." in cid:
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
        run = _api(f"repos/{repo}/actions/runs/{run_id}")
        if (run.get("conclusion") != "success"
                or run.get("head_branch") != "main"
                or run.get("name") != "ASTRA V2 - Preload Approved Videos"):
            continue
        with tempfile.TemporaryDirectory(prefix="astra-queue-") as tmp:
            archive = Path(tmp) / "artifact.zip"
            with archive.open("wb") as dest:
                result = subprocess.run(
                    ["gh", "api", f"repos/{repo}/actions/artifacts/{entry['id']}/zip"],
                    stdout=dest, stderr=subprocess.PIPE, timeout=90, check=False)
            if result.returncode or archive.stat().st_size > MAX_BYTES:
                continue
            try:
                with zipfile.ZipFile(archive) as z:
                    if sorted(z.namelist()) != ["candidate.json", "video.mp4"]:
                        continue
                    if z.getinfo("video.mp4").file_size > MAX_BYTES:
                        continue
                    candidate = json.loads(z.read("candidate.json"))
                    if candidate.get("content_id") != cid:
                        continue
                    if candidate.get("title", "").casefold().strip() in excluded_titles:
                        continue
                    if not all(candidate.get(k) for k in ("title", "description", "content_id", "genre", "format")):
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
            candidate["media"] = media
            candidate["queue_artifact_id"] = entry["id"]
            return candidate
    return None
