from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from channel_state import migrate_legacy
OPS_PATH = migrate_legacy("ops_state.json")

TRANSIENT_REASONS = {"backendError", "internalError", "rateLimitExceeded"}
QUOTA_REASONS = {"uploadLimitExceeded", "quotaExceeded", "dailyLimitExceeded"}
AUTH_HTTP = {401}
HUMAN_AUTH_REASONS = {"authError", "invalidCredentials", "insufficientPermissions", "youtubeSignupRequired"}


def classify(api_error: dict | None = None, exc_type: str = "") -> str:
    error = api_error or {}
    reasons = {str(x.get("reason") or "") for x in error.get("errors", []) if isinstance(x, dict)}
    status = int(error.get("http_status") or 0)
    if reasons & QUOTA_REASONS:
        return "quota_pause"
    if status in AUTH_HTTP or reasons & HUMAN_AUTH_REASONS:
        return "human_auth"
    if status >= 500 or reasons & TRANSIENT_REASONS or exc_type in {"ConnectError", "ReadTimeout", "ConnectTimeout"}:
        return "retry"
    if status == 403:
        return "human_account_check"
    return "investigate"


def recovery_plan(kind: str, attempts: int = 0) -> dict:
    attempts = max(0, int(attempts))
    if kind == "retry":
        delay = min(3600, 60 * (2 ** min(attempts, 5)))
        return {"action": "retry_later", "delay_seconds": delay, "human_required": False}
    if kind == "quota_pause":
        return {"action": "pause_until_next_controller_day", "human_required": False}
    if kind == "human_auth":
        return {"action": "reauthorize_youtube", "human_required": True}
    if kind == "human_account_check":
        return {"action": "check_youtube_account_or_scope", "human_required": True}
    return {"action": "preserve_state_and_investigate", "human_required": True}


def record_event(kind: str, detail: dict | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    try:
        state = json.loads(OPS_PATH.read_text(encoding="utf-8")) if OPS_PATH.exists() else {}
    except (ValueError, OSError):
        state = {}
    count = int(state.get("consecutive_failures", 0)) + (0 if kind == "healthy" else 1)
    if kind == "healthy":
        count = 0
    plan = recovery_plan(kind, count - 1)
    event = {
        "at": now.isoformat(),
        "kind": kind,
        "plan": plan,
        "detail": detail or {},
    }
    state.update({
        "status": "healthy" if kind == "healthy" else ("waiting_for_human" if plan["human_required"] else "self_recovering"),
        "consecutive_failures": count,
        "last_event": event,
        "human_action_required": plan["action"] if plan["human_required"] else None,
    })
    if plan.get("delay_seconds"):
        state["retry_after"] = (now + timedelta(seconds=plan["delay_seconds"])).isoformat()
    else:
        state.pop("retry_after", None)
    OPS_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def healthy() -> dict:
    return record_event("healthy")
