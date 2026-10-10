"""Opt-in YouTube uploader for a verified ASTRA handoff.

Default mode is dry-run. Requires an existing authorized OAuth token JSON and
Google API Python dependencies for --execute. Never starts uploads implicitly.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
try:
    from integrations.meta_verify_handoff import verify
except ModuleNotFoundError:
    from meta_verify_handoff import verify

def upload(handoff: Path, token: Path | None = None, execute: bool = False, privacy: str = "private") -> dict:
    if privacy not in {"private", "unlisted", "public"}:
        raise ValueError("Invalid privacy setting")
    checked = verify(handoff)
    if not checked["verified"]:
        return {"uploaded": False, "ready": False, "error": checked["error"]}
    payload = json.loads(handoff.read_text(encoding="utf-8"))
    if not execute:
        return {"uploaded": False, "ready": True, "mode": "dry-run", "video": checked["video"], "title": checked["title"], "privacy": privacy}
    if token is None or not token.is_file():
        raise ValueError("Existing OAuth token JSON required for --execute")
    # Import only on explicit execution: local validation works without packages.
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    credentials = Credentials.from_authorized_user_file(str(token), ["https://www.googleapis.com/auth/youtube.upload"])
    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            raise ValueError("OAuth token invalid; reauthorization required")
    # Recheck the file immediately before starting the upload.
    checked = verify(handoff)
    if not checked["verified"]:
        raise ValueError("Handoff changed before upload")
    service = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    request = service.videos().insert(
        part="snippet,status",
        body={"snippet": {"title": payload["title"], "description": payload.get("description", "")},
              "status": {"privacyStatus": privacy}},
        media_body=MediaFileUpload(checked["video"], mimetype="video/mp4", resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response.get("id")
    if not video_id:
        raise RuntimeError("YouTube did not return a video ID")
    return {"uploaded": True, "video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}", "privacy": privacy}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--token", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
    args = parser.parse_args()
    print(json.dumps(upload(args.handoff, args.token, args.execute, args.privacy), indent=2))

if __name__ == "__main__":
    main()
