"""No-credential watchdog for stalled ASTRA V2 publication."""
from __future__ import annotations

import json
import os
from datetime import timedelta

from astra_v2.control import STATE_FILE, parse_time, read_json, utcnow


def assess(state, now=None):
    now = now or utcnow()
    if not isinstance(state, dict):
        return "unhealthy", "publisher_journal_invalid"
    if state.get("version") != 2:
        return "unhealthy", "publisher_journal_missing_or_wrong_version"

    pending = state.get("pending", {})
    if not isinstance(pending, dict):
        return "unhealthy", "pending_journal_invalid"
    for item in pending.values():
        # Journal corruption must produce a controlled unhealthy result, not
        # an AttributeError that prevents the watchdog from emitting a report.
        if not isinstance(item, dict):
            return "unhealthy", "pending_journal_invalid"
        age = parse_time(item.get("uploaded_at"))
        if age and now - age > timedelta(hours=4):
            return "unhealthy", "upload_unconfirmed_more_than_four_hours"

    last_outcome = str(state.get("last_outcome") or "")
    if last_outcome == "failure":
        return "unhealthy", "last_runtime_error"

    published = state.get("published", {})
    if not isinstance(published, dict):
        return "unhealthy", "published_journal_invalid"
    confirmed = [
        parse_time(item.get("confirmed_at"))
        for item in published.values()
        if isinstance(item, dict)
    ]
    confirmed = [timestamp for timestamp in confirmed if timestamp]
    reference = max(confirmed) if confirmed else parse_time(state.get("created_at"))
    if reference is None:
        return "grace", "awaiting_first_publisher_timestamp"
    cooldown = parse_time(state.get("blocked_until"))
    if cooldown and now < cooldown:
        return "paused", "youtube_quota_cooldown"
    if now - reference > timedelta(hours=24):
        return "unhealthy", "no_verified_public_video_in_twenty_four_hours"
    return "healthy", "confirmed_public_video_or_first_day_grace"


def main():
    result = read_json(STATE_FILE)
    status, reason = assess(result)
    published = result.get("published") if isinstance(result.get("published"), dict) else {}
    pending = result.get("pending") if isinstance(result.get("pending"), dict) else {}
    report = {
        "status": status,
        "reason": reason,
        "last_outcome": result.get("last_outcome") if isinstance(result, dict) else None,
        "confirmed_total": len(published),
        "pending": len(pending),
        "quota_reason": result.get("quota_reason") if isinstance(result, dict) else None,
        "checked_at": utcnow().isoformat(),
    }
    print("ASTRA_V2_HEALTH=" + json.dumps(report))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("## ASTRA V2 unattended publishing health\n\n")
            for key, value in report.items():
                fh.write(f"- {key}: {value}\n")
    if status == "unhealthy":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
