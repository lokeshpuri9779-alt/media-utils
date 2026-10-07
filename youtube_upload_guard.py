from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Callable, Any


TRANSIENT_MARKERS = (
    "backenderror","internalerror","temporarily unavailable","timeout",
    "connection reset","rate limit","ratelimit","500","502","503","504"
)
QUOTA_MARKERS = (
    "quotaexceeded","dailylimitexceeded","uploadlimitexceeded","quota",
)
AUTH_MARKERS = (
    "invalid_grant","unauthorized","forbidden","invalid credentials","401","403"
)


@dataclass(frozen=True)
class UploadPolicy:
    max_attempts: int = 3
    daily_upload_limit: int = 9
    privacy_status: str = "private"


def classify_upload_error(exc: Exception | str) -> str:
    msg=str(exc).lower()
    if any(x in msg for x in QUOTA_MARKERS):
        return "quota"
    if any(x in msg for x in AUTH_MARKERS):
        return "auth"
    if any(x in msg for x in TRANSIENT_MARKERS):
        return "transient"
    return "fatal"


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_upload_state(path: str | Path) -> dict:
    p=Path(path)
    if not p.is_file():
        return {"day":_utc_day(),"uploaded":0,"attempted":0}
    try:
        data=json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        data={}
    if data.get("day") != _utc_day():
        return {"day":_utc_day(),"uploaded":0,"attempted":0}
    return {
        "day":data.get("day") or _utc_day(),
        "uploaded":int(data.get("uploaded") or 0),
        "attempted":int(data.get("attempted") or 0),
    }


def save_upload_state(path: str | Path, state: dict) -> None:
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(state,indent=2),encoding="utf-8")


def can_upload(state: dict, policy: UploadPolicy) -> tuple[bool,str]:
    if int(state.get("uploaded") or 0) >= policy.daily_upload_limit:
        return False,"daily-upload-limit-reached"
    return True,"ok"


def upload_with_guard(
    upload_fn: Callable[[dict], Any],
    payload: dict,
    state_path: str | Path,
    policy: UploadPolicy | None = None,
) -> dict:
    policy=policy or UploadPolicy()
    state=load_upload_state(state_path)
    ok,reason=can_upload(state,policy)
    if not ok:
        return {"status":"blocked","reason":reason,"state":state}

    guarded=dict(payload)
    guarded["privacy_status"]=policy.privacy_status

    last_error=None
    for attempt in range(1,policy.max_attempts+1):
        state["attempted"]=int(state.get("attempted") or 0)+1
        save_upload_state(state_path,state)
        try:
            result=upload_fn(guarded)
            state["uploaded"]=int(state.get("uploaded") or 0)+1
            save_upload_state(state_path,state)
            return {
                "status":"uploaded",
                "attempt":attempt,
                "result":result,
                "privacy_status":policy.privacy_status,
                "state":state,
            }
        except Exception as exc:
            kind=classify_upload_error(exc)
            last_error=str(exc)[:500]
            if kind in {"quota","auth","fatal"}:
                return {
                    "status":"failed",
                    "error_type":kind,
                    "error":last_error,
                    "attempt":attempt,
                    "state":state,
                }
            if attempt>=policy.max_attempts:
                break

    return {
        "status":"failed",
        "error_type":"transient",
        "error":last_error,
        "attempt":policy.max_attempts,
        "state":state,
    }


def verify_upload(video_record: dict, expected_privacy: str = "private") -> dict:
    video_id=str(video_record.get("id") or video_record.get("video_id") or "").strip()
    privacy=str(
        video_record.get("privacyStatus")
        or video_record.get("privacy_status")
        or (video_record.get("status") or {}).get("privacyStatus")
        or ""
    ).strip()
    failures=[]
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,}",video_id):
        failures.append("missing-or-invalid-video-id")
    if privacy and privacy != expected_privacy:
        failures.append(f"privacy-mismatch:{privacy}")
    if not privacy:
        failures.append("privacy-status-unverified")
    return {
        "pass":not failures,
        "video_id":video_id,
        "privacy_status":privacy,
        "expected_privacy":expected_privacy,
        "failures":failures,
    }
