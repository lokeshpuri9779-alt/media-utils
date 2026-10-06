from __future__ import annotations

import math
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import os
import random
import re
from datetime import datetime, timedelta

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"
ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3/"
IST_NAME = "Asia/Kolkata"


POLICY_PATH = Path(__file__).with_name("learning_policy.json")
ANALYTICS_SCHEMA = 2
def expected_channel_id() -> str:
    from channel_state import profile
    return str(profile()["expected_channel_id"])
# Backward-compatible module attribute for existing collectors; refreshed per process.
EXPECTED_CHANNEL_ID = expected_channel_id()
REPORT_TZ = ZoneInfo("America/Los_Angeles")


def learning_exclusions() -> set[str]:
    # Fail closed: missing/malformed policy must not reactivate contaminated data.
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return set(policy["excluded_video_ids"])


def _report_rows(report: dict) -> list[dict]:
    headers = [h.get("name") for h in report.get("columnHeaders", [])]
    return [dict(zip(headers, row)) for row in report.get("rows") or []]


def _report_error(exc: Exception) -> dict:
    # Never persist exception strings, request URLs, headers or tokens.
    result = {"status": "error", "error_type": type(exc).__name__}
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        result["http_status"] = code
        result["status"] = "permission_error" if code in (401, 403) else "error"
    return result


def _access_token(refresh_token: str, client_id: str | None = None,
                  client_secret: str | None = None) -> str:
    client_id = (client_id or os.environ.get("YOUTUBE_CLIENT_ID") or "").strip()
    client_secret = (client_secret or os.environ.get("YOUTUBE_CLIENT_SECRET") or "").strip()
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


def _token_scopes(access_token: str) -> set[str]:
    """Return granted OAuth scopes without logging token or account identity."""
    with httpx.Client(timeout=30) as client:
        r = client.get("https://oauth2.googleapis.com/tokeninfo",
                       params={"access_token": access_token})
    r.raise_for_status()
    value = r.json().get("scope") or ""
    return {s for s in str(value).split() if s}


def _credential(required_any: set[str], candidates) -> tuple[str, str, set[str]] | None:
    """Use the first stored OAuth credential whose access token has a required scope.

    Candidate items may be (source, refresh_token) or
    (source, refresh_token, client_id, client_secret). This lets Astra keep a
    separate browser-created Web OAuth client for community replies without
    touching the working upload client.
    """
    seen = set()
    for candidate in candidates:
        source, refresh_token = candidate[:2]
        client_id = candidate[2] if len(candidate) > 2 else None
        client_secret = candidate[3] if len(candidate) > 3 else None
        refresh_token = (refresh_token or "").strip()
        fingerprint = (refresh_token, client_id or "", client_secret or "")
        if not refresh_token or fingerprint in seen:
            continue
        seen.add(fingerprint)
        try:
            token = _access_token(refresh_token, client_id, client_secret)
            scopes = _token_scopes(token)
        except (httpx.HTTPError, RuntimeError):
            continue
        if scopes.intersection(required_any):
            return token, source, scopes
    return None


def _query_analytics(token: str, *, start_date: str, end_date: str,
                     metrics: str, filters: str | None = None,
                     dimensions: str | None = None) -> dict:
    params = {
        "ids": "channel==" + expected_channel_id(),
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
    excluded = learning_exclusions()
    for vid, entry in data.get("videos", {}).items():
        if vid in excluded or entry.get("format") == "long":
            continue
        a = entry.get("analytics") or {}
        reports = entry.get("analytics_reports") or {}
        traffic = reports.get("traffic_sources") or {}
        if (reports.get("basic", {}).get("status") != "available"
                or traffic.get("status") != "available"):
            continue
        try:
            if now - datetime.fromisoformat(a["refreshed_at"]) > timedelta(days=2):
                continue
        except (KeyError, ValueError, TypeError):
            continue
        # Attribution is not viewer identity; it does not identify owner views.
        attributed = sum(float(r.get("views") or 0) for r in traffic.get("rows", []))
        if attributed < 25:
            continue
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
        # Monetization objective: reward videos that turn qualified viewers into
        # subscribers, while keeping retention dominant and sample-size bounded.
        sub_rate = subs / max(views, 1)
        quality += min(18.0, sub_rate * 1200.0)
        quality *= min(1.0, math.log10(views + 10) / 3.0 + .25)
        genre = entry.get("genre", "challenge")
        grouped.setdefault(genre, []).append(quality)

    scores = {}
    for genre, values in grouped.items():
        if len(values) < 3:
            continue
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
            "excluded_video_count": len(excluded),
            "reason": "Waiting for fresh retention and traffic-source data on three non-excluded videos per genre.",
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
        "excluded_video_count": len(excluded),
        "reason": "Retention, subscriber conversion and traffic-source evidence; owner-reported test videos excluded. Viewer identity is unknown.",
    }


def refresh_analytics(data: dict, now: datetime, force: bool = False) -> bool:
    """Collect measured reports; never equate token presence or empty rows with data."""
    state = data.setdefault("analytics_state", {})
    try:
        last = datetime.fromisoformat(state.get("checked_at", ""))
        interval = 12 if state.get("status") == "active" else 4
        if (state.get("schema_version") == ANALYTICS_SCHEMA and not force
                and now - last < timedelta(hours=interval)):
            return False
    except (ValueError, TypeError):
        pass

    # A new evaluation invalidates any cached winner before attempting network I/O.
    data["strategy"] = _strategy(data, now)
    excluded = learning_exclusions()
    state.clear()
    state.update({
        "schema_version": ANALYTICS_SCHEMA,
        "status": "awaiting_data",
        "checked_at": now.isoformat(),
        "videos_updated": 0,
        "eligible_videos": 0,
        "queries_attempted": 0,
        "queries_succeeded": 0,
        "failures": [],
        "excluded_video_count": len(excluded),
        "owner_views_identifiable": False,
        "impressions": {
            "status": "separate_collector",
            "state_key": "reach_state",
            "value": None, "ctr": None,
            "reason": "Collected separately by reach_reports.py using channel_reach_basic_a1. See reach_state; never substitute ad/card impressions.",
        },
    })

    # YouTube report dates use Pacific time; exclude its still-incomplete current day.
    end = now.astimezone(REPORT_TZ).date() - timedelta(days=1)
    eligible = []
    for vid, entry in data.get("videos", {}).items():
        try:
            published = datetime.fromisoformat(entry["published_at"]).astimezone(REPORT_TZ)
        except (KeyError, TypeError, ValueError):
            continue
        if published.date() <= end:
            eligible.append((published, vid, entry))
    # Rotate older videos too; a high daily upload rate must not starve their reports.
    eligible.sort(key=lambda row: row[2].get("analytics_reports", {}).get("checked_at", ""))
    eligible = eligible[:12]
    state["eligible_videos"] = len(eligible)
    state["report_timezone"] = "America/Los_Angeles"
    state["window_end"] = end.isoformat()
    if not eligible:
        state["status"] = "awaiting_eligible_videos"
        state["message"] = "No tracked video belongs to a completed YouTube reporting day."
        print("Private analytics:", state["status"], "| no report requested")
        return True

    credential = _credential(
        {"https://www.googleapis.com/auth/youtube.readonly",
         "https://www.googleapis.com/auth/yt-analytics.readonly"},
        [
            ("full", os.environ.get("YOUTUBE_FULL_REFRESH_TOKEN") or ""),
            ("analytics", os.environ.get("YOUTUBE_ANALYTICS_REFRESH_TOKEN") or ""),
            ("existing-cloud-token", os.environ.get("YOUTUBE_REFRESH_TOKEN") or ""),
        ],
    )
    if not credential:
        state["status"] = "awaiting_scope"
        state["message"] = "No stored credential with a candidate read scope; no Analytics report was validated."
        return True
    token, source, scopes = credential
    state["credential_source"] = source
    state["granted_scope_classes"] = sorted({
        "analytics" if "analytics" in x else
        "youtube-read" if x.endswith("/youtube.readonly") else "other"
        for x in scopes
    })
    metrics = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,likes,comments,shares"
    updated = 0
    failures = []
    for index, (published, vid, entry) in enumerate(eligible):
        start = max(published.date(), end - timedelta(days=28))
        window = {"window_start": start.isoformat(), "window_end": end.isoformat(),
                  "checked_at": now.isoformat()}
        reports = dict(window)
        entry["analytics_reports"] = reports
        entry["learning_excluded"] = vid in excluded
        geo_metrics = "views,estimatedMinutesWatched"
        if "https://www.googleapis.com/auth/yt-analytics-monetary.readonly" in scopes:
            geo_metrics += ",estimatedRevenue"
        requests = [
            ("basic", metrics, None),
            ("traffic_sources", "views,estimatedMinutesWatched", "insightTrafficSourceType"),
            ("geography", geo_metrics, "country"),
        ]
        if index < 3:
            requests.append(("retention", "audienceWatchRatio,relativeRetentionPerformance", "elapsedVideoTimeRatio"))
        else:
            reports["retention"] = {"status": "not_sampled"}
        for name, query_metrics, dimension in requests:
            state["queries_attempted"] += 1
            try:
                report = _query_analytics(
                    token, start_date=start.isoformat(), end_date=end.isoformat(),
                    metrics=query_metrics, dimensions=dimension, filters="video==" + vid,
                )
                rows = _report_rows(report)
                state["queries_succeeded"] += 1
                reports[name] = {**window, "status": "available" if rows else "awaiting_data"}
                if name == "basic":
                    if rows:
                        entry["analytics"] = {**rows[0], **window, "refreshed_at": now.isoformat()}
                        updated += 1
                    else:
                        entry.pop("analytics", None)
                elif name in {"traffic_sources", "geography"}:
                    reports[name]["rows"] = rows
                    reports[name]["owner_views_identifiable"] = False
                else:
                    reports[name]["summary"] = _retention_summary(report)
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                error = _report_error(exc)
                reports[name] = {**window, **error}
                failures.append({"video_id": vid, "report": name, **error})
                if name == "basic":
                    entry.pop("analytics", None)

    state["videos_updated"] = updated
    state["failures"] = failures
    all_reports = [r for _, _, entry in eligible
                   for name, r in entry["analytics_reports"].items()
                   if name in {"basic", "traffic_sources", "geography", "retention"} and r["status"] != "not_sampled"]
    if failures:
        state["status"] = "partial" if state["queries_succeeded"] else "error"
    elif all_reports and all(r["status"] == "available" for r in all_reports):
        state["status"] = "active"
    else:
        state["status"] = "awaiting_data"
    state["message"] = "Report data may lag; empty reports are unknown, not zero audience."
    data["strategy"] = _strategy(data, now)
    from evolution import evolution_state
    data["evolution"] = evolution_state(data)
    from distribution import distribution_state
    data["distribution"] = distribution_state(data)
    from revenue_geo import geography_state
    data["revenue_geography"] = geography_state(data)
    print("Evolution:", json.dumps(data["evolution"].get("diagnosis_counts", {}), ensure_ascii=False))
    print("Distribution:", json.dumps({
        "mode": data["distribution"].get("mode"),
        "eligible_videos": data["distribution"].get("eligible_videos"),
        "top_sources": [x.get("source") for x in data["distribution"].get("ranked_sources", [])[:3]],
    }, ensure_ascii=False))
    print("Private analytics:", state["status"], "| videos updated:", updated,
          "| report requests:", state["queries_attempted"], "| failures:", len(failures))
    print("Learning exclusions:", len(excluded), "| impressions/CTR: see separate reach_state")
    return True


def strategy_genre(data: dict, available: set[str], now: datetime | None = None) -> str | None:
    """Weighted autonomous exploitation while still allowing exploration elsewhere."""
    from datetime import timezone
    weights = _strategy(data, now or datetime.now(timezone.utc)).get("genre_weights") or {}
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

    try:
        last = datetime.fromisoformat(state.get("checked_at", ""))
        if state.get("status") in {"active", "partial"} and now - last < timedelta(hours=4):
            return False
    except (ValueError, TypeError):
        pass

    credential = _credential(
        {"https://www.googleapis.com/auth/youtube.force-ssl"},
        [
            (
                "community-web-client",
                os.environ.get("YOUTUBE_COMMUNITY_REFRESH_TOKEN") or "",
                os.environ.get("YOUTUBE_COMMUNITY_CLIENT_ID") or "",
                os.environ.get("YOUTUBE_COMMUNITY_CLIENT_SECRET") or "",
            ),
            ("full", os.environ.get("YOUTUBE_FULL_REFRESH_TOKEN") or ""),
            ("community", os.environ.get("YOUTUBE_COMMUNITY_REFRESH_TOKEN") or ""),
            ("existing-cloud-token", os.environ.get("YOUTUBE_REFRESH_TOKEN") or ""),
        ],
    )
    if not credential:
        state.update({
            "status": "awaiting_scope",
            "checked_at": now.isoformat(),
            "message": "Stored GitHub OAuth tokens do not grant youtube.force-ssl; automatic replies remain disabled.",
        })
        return True
    token, credential_source, granted_scopes = credential
    state.pop("message", None)

    day = now.date().isoformat()
    if state.get("reply_day") != day:
        state["reply_day"] = day
        state["replies_today"] = 0
    remaining = max(0, 3 - int(state.get("replies_today", 0)))
    if remaining <= 0:
        state["checked_at"] = now.isoformat()
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
        "credential_source": credential_source,
        "processed_comment_ids": processed[-1000:],
        "replies_today": int(state.get("replies_today", 0)) + replies,
        "failures": failures[-10:],
    })
    print("Community manager:", state["status"], "| replies:", replies)
    return True
