from __future__ import annotations

from collections import defaultdict

MIN_ATTRIBUTED_VIEWS = 25
MIN_SOURCE_VIEWS = 10

# YouTube Analytics traffic-source values are intentionally treated as opaque
# labels. Astra learns measured quality; it does not manufacture traffic.
INTERNAL_HINTS = ("RELATED_VIDEO", "YT_SEARCH", "BROWSE", "SHORTS", "PLAYLIST", "CHANNEL")


def _num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def source_quality(row: dict) -> float | None:
    """Retention-aware quality for a measured traffic-source row.

    estimatedMinutesWatched / views is minutes watched per attributed view.
    Tiny samples are deliberately ignored.
    """
    views = _num(row.get("views"))
    if views < MIN_SOURCE_VIEWS:
        return None
    minutes = _num(row.get("estimatedMinutesWatched"))
    return round(minutes / max(views, 1.0), 4)


def distribution_state(data: dict) -> dict:
    """Build a conservative distribution-learning snapshot from measured data."""
    sources: dict[str, dict[str, float]] = defaultdict(lambda: {"views": 0.0, "minutes": 0.0})
    genres: dict[str, dict[str, float]] = defaultdict(lambda: {"views": 0.0, "minutes": 0.0})
    eligible_videos = 0

    for _, entry in data.get("videos", {}).items():
        if entry.get("learning_excluded"):
            continue
        reports = entry.get("analytics_reports") or {}
        traffic = reports.get("traffic_sources") or {}
        if traffic.get("status") != "available":
            continue
        rows = traffic.get("rows") or []
        attributed = sum(_num(row.get("views")) for row in rows)
        if attributed < MIN_ATTRIBUTED_VIEWS:
            continue
        eligible_videos += 1
        genre = str(entry.get("genre") or "unknown")
        for row in rows:
            name = str(row.get("insightTrafficSourceType") or "UNKNOWN")
            views = _num(row.get("views"))
            minutes = _num(row.get("estimatedMinutesWatched"))
            sources[name]["views"] += views
            sources[name]["minutes"] += minutes
            genres[genre]["views"] += views
            genres[genre]["minutes"] += minutes

    ranked = []
    for name, agg in sources.items():
        if agg["views"] < MIN_SOURCE_VIEWS:
            continue
        quality = agg["minutes"] / max(agg["views"], 1.0)
        # Confidence rises gradually; a tiny high-retention source cannot dominate.
        confidence = min(1.0, agg["views"] / 100.0)
        ranked.append({
            "source": name,
            "views": int(agg["views"]),
            "minutes_per_view": round(quality, 4),
            "confidence": round(confidence, 3),
            "quality_score": round(quality * (0.5 + 0.5 * confidence), 4),
            "youtube_internal": any(h in name.upper() for h in INTERNAL_HINTS),
        })
    ranked.sort(key=lambda x: (x["quality_score"], x["views"]), reverse=True)

    genre_quality = {}
    for genre, agg in genres.items():
        if agg["views"] >= MIN_ATTRIBUTED_VIEWS:
            genre_quality[genre] = {
                "views": int(agg["views"]),
                "minutes_per_view": round(agg["minutes"] / max(agg["views"], 1.0), 4),
            }

    mode = "learn" if eligible_videos else "explore"
    return {
        "mode": mode,
        "eligible_videos": eligible_videos,
        "ranked_sources": ranked[:10],
        "genre_quality": genre_quality,
        "objective": "qualified watch time and subscriber value, not raw clicks",
        "guardrails": {
            "fake_engagement": False,
            "bot_traffic": False,
            "spam_distribution": False,
            "unauthorized_external_posting": False,
        },
        "routing": {
            "short_to_long": True,
            "long_to_short": True,
            "youtube_internal_first": True,
            "external_requires_authorized_account": True,
        },
    }


def best_internal_sources(data: dict, limit: int = 3) -> list[str]:
    state = distribution_state(data)
    return [x["source"] for x in state["ranked_sources"] if x["youtube_internal"]][:limit]
