from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("ASTRA_STORAGE_DIR", str(Path(tempfile.gettempdir()) / "media_utils_state"))
os.environ.setdefault("ASTRA_RUNTIME_DIR", str(Path(tempfile.gettempdir()) / "media_utils_runtime"))

from app.core import (
    create_autopilot_job,
    db,
    init_storage,
    refresh_channel_metadata,
    save_oauth,
    save_token,
    update_settings,
    upload_job,
)

def need(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise RuntimeError(f"Missing required GitHub secret: {name}")
    return value

def main() -> int:
    client_id = need("YOUTUBE_CLIENT_ID")
    client_secret = need("YOUTUBE_CLIENT_SECRET")
    refresh_token = need("YOUTUBE_REFRESH_TOKEN")
    privacy = (os.environ.get("YOUTUBE_PRIVACY") or "public").strip().lower()
    if privacy not in {"private", "unlisted", "public"}:
        privacy = "public"

    init_storage()
    save_oauth(client_id, client_secret)
    save_token({
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
    })
    update_settings(privacy=privacy)

    meta = refresh_channel_metadata()
    if not meta.get("connected"):
        raise RuntimeError("YouTube OAuth refresh token is not usable")
    print(f"Connected channel: {meta.get('channel_title') or meta.get('channel_id') or 'YouTube'}")

    job_id = create_autopilot_job()
    upload_job(job_id)

    with db() as con:
        row = con.execute("SELECT status,detail,youtube_url,title FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise RuntimeError("Job disappeared unexpectedly")

    status = row["status"]
    title = row["title"]
    detail = row["detail"]
    url = row["youtube_url"] or ""
    print(f"Job status: {status}")
    print(f"Title: {title}")
    print(detail)
    if url:
        print(f"YouTube: {url}")

    if status == "published":
        return 0
    if status == "waiting_limit":
        print("YouTube API reported an upload limit. Ending this scheduled run cleanly.")
        return 0
    return 1

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
