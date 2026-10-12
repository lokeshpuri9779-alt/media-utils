"""Durable, conservative long-form upload-spacing guard; no YouTube writes."""
from datetime import timedelta
from astra_v2.control import parse_time


def long_upload_due(state, now, spacing_hours=24, performance=None):
    """Require 24h since the most recent confirmed long video by default.

    An unresolved long-form reservation or pending transfer blocks the lane
    regardless of age. This never affects Shorts. Pass the astra-state
    performance ledger explicitly in production; missing history fails closed.
    """
    if not isinstance(performance, dict) or not isinstance(performance.get("videos"), dict):
        return False
    latest = []
    published = state.get("published") or {}
    for entry in published.values():
        if isinstance(entry, dict) and entry.get("format") == "long":
            instant = parse_time(entry.get("confirmed_at") or entry.get("uploaded_at"))
            if instant is None:
                return False
            latest.append(instant)
    for entry in performance["videos"].values():
        if not isinstance(entry, dict) or entry.get("format") != "long":
            continue
        if entry.get("visibility") not in (None, "public"):
            continue
        instant = parse_time(entry.get("published_at"))
        if instant is None:
            return False
        latest.append(instant)
    for entry in (state.get("pending") or {}).values():
        if isinstance(entry, dict) and entry.get("format") == "long":
            return False
    for content_id, entry in (state.get("reserved") or {}).items():
        if isinstance(entry, dict) and entry.get("format") == "long" and content_id not in published:
            return False
    return not latest or now - max(latest) >= timedelta(hours=spacing_hours)
