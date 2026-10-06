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


def packaging_plan(data: dict, genre: str, fmt: str) -> dict:
    """Choose conservative packaging/routing hints from measured distribution."""
    state = distribution_state(data)
    top = best_internal_sources(data, limit=3)
    upper = " ".join(top).upper()
    hints = []
    if "YT_SEARCH" in upper:
        hints.append("search_clear_title")
    if "RELATED_VIDEO" in upper or "BROWSE" in upper:
        hints.append("curiosity_title")
    if "SHORTS" in upper:
        hints.append("first_second_hook")
    if not hints:
        hints = ["clear_title", "strong_hook"]
    return {
        "mode": state["mode"],
        "genre": genre,
        "format": fmt,
        "top_internal_sources": top,
        "packaging_hints": hints,
        "brand": "RAYVAN",
        "tagline": "Stories Beyond the Ordinary.",
    }


def related_video(data: dict, *, genre: str, target_format: str) -> str | None:
    """Return the newest public, non-excluded same-genre video in target format."""
    candidates = []
    for vid, entry in data.get("videos", {}).items():
        if entry.get("learning_excluded") or entry.get("visibility") != "public":
            continue
        if entry.get("genre") != genre or entry.get("format") != target_format:
            continue
        candidates.append((str(entry.get("published_at") or ""), vid))
    return max(candidates)[1] if candidates else None


def branded_description(description: str, data: dict, *, genre: str, fmt: str) -> tuple[str, dict]:
    """Add RAYVAN identity and measured internal routing to a fresh upload."""
    plan = packaging_plan(data, genre, fmt)
    target = "long" if fmt == "short" else "short"
    related = related_video(data, genre=genre, target_format=target)
    text = description.rstrip()
    if related and ("youtube.com/watch?v=" + related) not in text:
        label = "Watch the full RAYVAN story" if fmt == "short" else "Watch the related RAYVAN Short"
        text += "\n" + label + ": https://www.youtube.com/watch?v=" + related
        # Internal pathways are deliberate: every eligible Short can feed a
        # relevant long story and vice versa without external spam.
        plan["pathway"]={"from":fmt,"to":target,"video_id":related,"mode":"youtube-internal"}
    if "RAYVAN" not in text:
        text += "\n\nRAYVAN — Stories Beyond the Ordinary."
    plan["related_video_id"] = related
    plan["external_distribution"]="disabled-unless-explicitly-authorized"
    plan["engagement_manipulation"]=False
    return text, plan


def optimize_title(title: str, plan: dict, meta: dict) -> str:
    """Apply measured packaging hints without clickbait or unsupported claims."""
    text=" ".join(str(title or "").split()).strip()
    hints=set(plan.get("packaging_hints") or [])
    hook=" ".join(str(meta.get("hook") or "").split()).strip(" ?!.-")
    if "curiosity_title" in hints and hook and hook.lower() not in text.lower():
        base=text.replace("#Shorts","").strip()
        candidate=f"{hook}: {base}"
        text=candidate if len(candidate)<=92 else text
    if "search_clear_title" in hints:
        # Preserve the descriptive title; search packaging values clarity over mutation.
        text=text
    if str(meta.get("format") or plan.get("format"))=="short" and "#Shorts" not in text:
        text=(text+" #Shorts").strip()
    return text[:100]
