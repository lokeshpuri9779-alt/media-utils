from __future__ import annotations

import math
import os
import random
import re
from datetime import datetime, timedelta

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"
ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3/"
IST_NAME = "Asia/Kolkata"


def _access_token(refresh_token: str) -> str:
    client_id = (os.environ.get("YOUTUBE_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("YOUTUBE_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret or not refresh_token:
        raise RuntimeError("Missing OAuth credentials")
    with httpx.Client(timeout=30) as client:
        r = client.post(TOKEN_URL, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
    r.raise_for_status()
    return r.json()["access_token"]


def _query_analytics(token: str, *, start_date: str, end_date: str,
                     metrics: str, filters: str | None = None,
                     dimensions: str | None = None) -> dict:
    params = {
        "ids": "channel==MINE",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": metrics,
    }
    if filters:
        params["filters"] = filters
    if dimensions:
        params["dimensions"] = dimensions
    with httpx.Client(timeout=30) as client:
        r = client.get(ANALYTICS_URL, params=params,
                       headers={"Authorization": "Bearer " + token})
    r.raise_for_status()
    return r.json()


def _row_dict(report: dict) -> dict:
    headers = [h.get("name") for h in report.get("columnHeaders", [])]
    rows = report.get("rows") or []
    if not rows:
        return {}
    return dict(zip(headers, rows[0]))


def _retention_summary(report: dict) -> dict:
    headers = [h.get("name") for h in report.get("columnHeaders", [])]
    rows = report.get("rows") or []
    if not rows or "elapsedVideoTimeRatio" not in headers:
        return {}
    parsed = [dict(zip(headers, row)) for row in rows]
    parsed.sort(key=lambda x: float(x.get("elapsedVideoTimeRatio", 0)))

    def nearest(target: float):
        row = min(parsed, key=lambda x: abs(float(x.get("elapsedVideoTimeRatio", 0)) - target))
        return {
            "elapsed": round(float(row.get("elapsedVideoTimeRatio", 0)), 3),
            "audience_watch_ratio": round(float(row.get("audienceWatchRatio", 0)), 4),
            "relative_retention": round(float(row.get("relativeRetentionPerformance", 0)), 4),
        }

    return {"10pct": nearest(.10), "50pct": nearest(.50), "90pct": nearest(.90)}


def _strategy(data: dict, now: datetime) -> dict:
    grouped: dict[str, list[float]] = {}
    evidence: dict[str, int] = {}
    for entry in data.get("videos", {}).values():
        if entry.get("format") == "long":
            continue
        a = entry.get("analytics") or {}
        views = float(a.get("views") or 0)
        avg = float(a.get("averageViewPercentage") or 0)
        if views < 25 or avg <= 0:
            continue
        likes = float(a.get("likes") or 0)
        shares = float(a.get("shares") or 0)
        subs = float(a.get("subscribersGained") or 0)
        # Retention dominates. Engagement is capped so tiny samples cannot hijack strategy.
        quality = avg
        quality += min(12.0, (likes / max(views, 1)) * 240.0)
        quality += min(10.0, (shares / max(views, 1)) * 500.0)
        quality += min(8.0, (subs / max(views, 1)) * 800.0)
        quality *= min(1.0, math.log10(views + 10) / 3.0 + .25)
        genre = entry.get("genre", "challenge")
        grouped.setdefault(genre, []).append(quality)

    scores = {}
    for genre, values in grouped.items():
        values = sorted(values)
        mid = len(values) // 2
        median = values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2
        scores[genre] = round(median, 3)
        evidence[genre] = len(values)

    if not scores:
        return {
            "updated_at": now.isoformat(),
            "mode": "explore",
            "genre_scores": {},
            "genre_weights": {},
            "reason": "Waiting for enough YouTube Analytics evidence.",
        }

    floor = max(1.0, min(scores.values()) * .35)
    raw = {g: max(floor, s) for g, s in scores.items()}
    total = sum(raw.values())
    weights = {g: round(v / total, 4) for g, v in raw.items()}
    return {
        "updated_at": now.isoformat(),
        "mode": "learn",
        "genre_scores": scores,
        "genre_weights": weights,
        "evidence": evidence,
        "winner": max(scores, key=scores.get),
        "reason": "Retention-first score with bounded like/share/subscriber signals.",
    }


def refresh_analytics(data: dict, now: datetime, force: bool = False) -> bool:
    """Refresh private owner analytics when the separate analytics refresh token is installed.

    Missing permission is non-fatal: production/uploading continues.
    """
    state = data.setdefault("analytics_state", {})
    refresh_token = ((os.environ.get("YOUTUBE_FULL_REFRESH_TOKEN") or "").strip()
                     or (os.environ.get("YOUTUBE_ANALYTICS_REFRESH_TOKEN") or "").strip())
    if not refresh_token:
        state.update({
            "status": "awaiting_secret",
            "checked_at": now.isoformat(),
            "message": "Add YOUTUBE_ANALYTICS_REFRESH_TOKEN to enable retention/watch-time learning.",
        })
        return True

    try:
        last = datetime.fromisoformat(state.get("checked_at", ""))
        if not force and now - last < timedelta(hours=12):
            return False
    except (ValueError, TypeError):
        pass

    try:
        token = _access_token(refresh_token)
    except Exception as exc:
        state.update({"status": "oauth_error", "checked_at": now.isoformat(),
                      "message": type(exc).__name__})
        return True

    eligible = []
    for vid, entry in data.get("videos", {}).items():
        try:
            published = datetime.fromisoformat(entry["published_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if now - published >= timedelta(days=1):
            eligible.append((published, vid, entry))
    eligible.sort(reverse=True)
    eligible = eligible[:12]

    end = (now - timedelta(days=1)).date()
    updated = 0
    failures = []
    metrics = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,likes,comments,shares"
    for published, vid, entry in eligible:
        start = max(published.date(), end - timedelta(days=28))
        if start > end:
            continue
        try:
            report = _query_analytics(
                token, start_date=start.isoformat(), end_date=end.isoformat(),
                metrics=metrics, filters="video==" + vid,
            )
            row = _row_dict(report)
            if row:
                entry["analytics"] = {
                    **row,
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                    "refreshed_at": now.isoformat(),
                }
                updated += 1
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            failures.append(f"{vid}:{type(exc).__name__}")

    # Retention curves are more expensive/noisy, so sample only the three newest eligible videos.
    for _, vid, entry in eligible[:3]:
        try:
            published = datetime.fromisoformat(entry["published_at"]).date()
            start = max(published, end - timedelta(days=28))
            report = _query_analytics(
                token, start_date=start.isoformat(), end_date=end.isoformat(),
                metrics="audienceWatchRatio,relativeRetentionPerformance",
                dimensions="elapsedVideoTimeRatio", filters="video==" + vid,
            )
            summary = _retention_summary(report)
            if summary:
                entry.setdefault("analytics", {})["retention"] = summary
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            failures.append(f"retention:{vid}:{type(exc).__name__}")

    data["strategy"] = _strategy(data, now)
    state.update({
        "status": "active" if not failures else "partial",
        "checked_at": now.isoformat(),
        "videos_updated": updated,
        "failures": failures[-10:],
    })
    print("Private analytics:", state["status"], "| videos updated:", updated,
          "| strategy:", data["strategy"].get("winner", data["strategy"].get("mode")))
    return True


def strategy_genre(data: dict, available: set[str]) -> str | None:
    """Weighted autonomous exploitation while still allowing exploration elsewhere."""
    weights = (data.get("strategy") or {}).get("genre_weights") or {}
    choices = [(g, float(w)) for g, w in weights.items() if g in available and float(w) > 0]
    if not choices:
        return None
    total = sum(w for _, w in choices)
    pick = random.random() * total
    cursor = 0.0
    for genre, weight in choices:
        cursor += weight
        if pick <= cursor:
            return genre
    return choices[-1][0]


_POSITIVE = re.compile(r"\b(love|great|nice|amazing|awesome|helpful|cool|wow|thanks|thank you|good one|brilliant)\b", re.I)
_SENSITIVE = re.compile(
    r"\b(suicide|self harm|kill|murder|drug|cocaine|heroin|medical|doctor|diagnos|religion|politic|election|sex|nude|weapon|gun|bomb|hate|racist)\b",
    re.I,
)


def manage_community(data: dict, now: datetime) -> bool:
    """Reply only to clearly positive comments, with strict daily limits.

    This intentionally avoids automatic moderation, arguments, advice, or sensitive topics.
    """
    state = data.setdefault("community", {})
    refresh_token = ((os.environ.get("YOUTUBE_FULL_REFRESH_TOKEN") or "").strip()
                     or (os.environ.get("YOUTUBE_COMMUNITY_REFRESH_TOKEN") or "").strip())
    if not refresh_token:
        if state.get("status") != "awaiting_scope":
            state.update({
                "status": "awaiting_scope",
                "checked_at": now.isoformat(),
                "message": "A youtube.force-ssl refresh token is required for autonomous replies.",
            })
            return True
        return False

    try:
        last = datetime.fromisoformat(state.get("checked_at", ""))
        if now - last < timedelta(hours=4):
            return False
    except (ValueError, TypeError):
        pass

    day = now.date().isoformat()
    if state.get("reply_day") != day:
        state["reply_day"] = day
        state["replies_today"] = 0
    remaining = max(0, 3 - int(state.get("replies_today", 0)))
    if remaining <= 0:
        state["checked_at"] = now.isoformat()
        return True

    try:
        token = _access_token(refresh_token)
    except Exception as exc:
        state.update({"status": "oauth_error", "checked_at": now.isoformat(),
                      "message": type(exc).__name__})
        return True

    processed = list(state.get("processed_comment_ids", []))
    processed_set = set(processed)
    own = sorted(data.get("videos", {}).items(),
                 key=lambda x: x[1].get("published_at", ""), reverse=True)[:5]
    replies = 0
    failures = []

    with httpx.Client(timeout=30) as client:
        for video_id, _ in own:
            if replies >= remaining:
                break
            try:
                r = client.get(
                    YOUTUBE_API + "commentThreads",
                    params={"part": "snippet", "videoId": video_id, "maxResults": 30,
                            "order": "time", "textFormat": "plainText"},
                    headers={"Authorization": "Bearer " + token},
                )
                r.raise_for_status()
                for thread in r.json().get("items", []):
                    if replies >= remaining:
                        break
                    snippet = thread.get("snippet", {})
                    top = snippet.get("topLevelComment", {})
                    cid = top.get("id", "")
                    c = top.get("snippet", {})
                    text = (c.get("textOriginal") or c.get("textDisplay") or "")[:500]
                    if not cid or cid in processed_set:
                        continue
                    processed.append(cid)
                    processed_set.add(cid)
                    if snippet.get("totalReplyCount", 0):
                        continue
                    if _SENSITIVE.search(text) or not _POSITIVE.search(text):
                        continue
                    reply = random.choice([
                        "Glad you enjoyed it 🙌 More original videos are on the way.",
                        "Thank you 🙌 Glad this one landed.",
                        "Appreciate it 🙌 More challenges and explainers are coming.",
                    ])
                    rr = client.post(
                        YOUTUBE_API + "comments",
                        params={"part": "snippet"},
                        headers={"Authorization": "Bearer " + token,
                                 "Content-Type": "application/json"},
                        json={"snippet": {"parentId": cid, "textOriginal": reply}},
                    )
                    if rr.status_code < 300:
                        replies += 1
                    else:
                        failures.append(f"reply:{rr.status_code}")
            except httpx.HTTPError as exc:
                failures.append(type(exc).__name__)

    state.update({
        "status": "active" if not failures else "partial",
        "checked_at": now.isoformat(),
        "processed_comment_ids": processed[-1000:],
        "replies_today": int(state.get("replies_today", 0)) + replies,
        "failures": failures[-10:],
    })
    print("Community manager:", state["status"], "| replies:", replies)
    return True
