"""Daily thumbnail impressions/CTR via YouTube Reporting API (not ad impressions)."""
from __future__ import annotations

import csv
import io
import math
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote

import httpx

BASE = "https://youtubereporting.googleapis.com/v1/"
REPORT_TYPE = "channel_reach_basic_a1"


def _list(client, path, key):
    rows, page = [], None
    for _ in range(20):
        r = client.get(BASE + path, params={"pageToken": page} if page else {})
        r.raise_for_status()
        body = r.json()
        rows.extend(body.get(key) or [])
        page = body.get("nextPageToken")
        if not page:
            return rows
    raise ValueError("Reporting pagination limit reached")


def ingest_csv(data, content, report, now):
    from autonomy import EXPECTED_CHANNEL_ID
    reader = csv.DictReader(io.StringIO(content))
    required = {"date", "channel_id", "video_id",
                "video_thumbnail_impressions", "video_thumbnail_impressions_ctr"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Reach CSV schema mismatch")
    staged = []
    for row in reader:
        if row["channel_id"] != EXPECTED_CHANNEL_ID:
            raise ValueError("Reach report channel mismatch")
        if row["video_id"] not in data.get("videos", {}):
            continue
        day = datetime.strptime(row["date"], "%Y%m%d").date() if "-" not in row["date"] else datetime.fromisoformat(row["date"]).date()
        impressions = int(row["video_thumbnail_impressions"])
        ctr = float(row["video_thumbnail_impressions_ctr"]) if row["video_thumbnail_impressions_ctr"] else None
        if impressions < 0 or (ctr is not None and (not math.isfinite(ctr) or ctr < 0)):
            raise ValueError("Invalid reach values")
        staged.append((row["video_id"], day.isoformat(), {
            "impressions": impressions, "ctr_reported": ctr,
            "report_created_at": report.get("createTime", ""),
            "report_id": report["id"],
        }))
    touched = set()
    for vid, day, row in staged:
        reach = data["videos"][vid].setdefault("reach", {"days": {}})
        previous = reach["days"].get(day, {})
        if previous.get("report_created_at", "") > row["report_created_at"]:
            continue
        # Re-downloads/backfills replace the same day; never add it twice.
        reach["days"][day] = row
        reach["days"] = dict(sorted(reach["days"].items())[-35:])
        reach["status"] = "available"
        reach["refreshed_at"] = now.isoformat()
        reach["source"] = REPORT_TYPE
        reach["ctr_units"] = "YouTube Reporting API value, preserved without rescaling"
        reach["owner_views_identifiable"] = False
        touched.add(vid)
    return len(touched)


def refresh_reach(data, now, force=False):
    from autonomy import _credential, _report_error, EXPECTED_CHANNEL_ID
    state = data.setdefault("reach_state", {})
    try:
        if not force and now - datetime.fromisoformat(state.get("checked_at", "")) < timedelta(hours=6):
            return False
    except (ValueError, TypeError):
        pass
    state.update(status="checking", checked_at=now.isoformat(), videos_updated=0)
    candidates = [
        ("full", os.environ.get("YOUTUBE_FULL_REFRESH_TOKEN", "")),
        ("analytics", os.environ.get("YOUTUBE_ANALYTICS_REFRESH_TOKEN", "")),
        ("existing-cloud-token", os.environ.get("YOUTUBE_REFRESH_TOKEN", "")),
        ("community-web-client", os.environ.get("YOUTUBE_COMMUNITY_REFRESH_TOKEN", ""),
         os.environ.get("YOUTUBE_COMMUNITY_CLIENT_ID", ""),
         os.environ.get("YOUTUBE_COMMUNITY_CLIENT_SECRET", "")),
    ]
    credential = _credential(
        {"https://www.googleapis.com/auth/yt-analytics.readonly",
         "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"}, candidates)
    if not credential:
        state.update(status="awaiting_scope",
                     message="Thumbnail impressions/CTR require yt-analytics.readonly on a stored refresh token.")
        print("Reach reporting: awaiting_scope (yt-analytics.readonly)")
        return True
    token, source, _ = credential
    state["credential_source"] = source
    stage = "verify_channel"
    try:
        with httpx.Client(timeout=45, headers={"Authorization": "Bearer " + token}) as client:
            r = client.get("https://www.googleapis.com/youtube/v3/channels",
                           params={"part": "id", "mine": "true"})
            r.raise_for_status()
            if [v.get("id") for v in r.json().get("items", [])] != [EXPECTED_CHANNEL_ID]:
                raise ValueError("Wrong authorized reporting channel")
            stage = "list_jobs"
            jobs = _list(client, "jobs", "jobs")
            job = next((j for j in jobs if j.get("reportTypeId") == REPORT_TYPE
                        and not j.get("expireTime")), None)
            if job is None:
                stage = "list_report_types"
                types = _list(client, "reportTypes", "reportTypes")
                if REPORT_TYPE not in {t.get("id") for t in types}:
                    state.update(status="unavailable", message="Reach report type is not available to this channel.")
                    return True
                stage = "create_job"
                r = client.post(BASE + "jobs", json={"reportTypeId": REPORT_TYPE,
                                                    "name": "Astra thumbnail reach"})
                if r.status_code == 409:
                    job = next(j for j in _list(client, "jobs", "jobs") if j.get("reportTypeId") == REPORT_TYPE)
                else:
                    r.raise_for_status()
                    job = r.json()
            state["job_id"] = job["id"]
            stage = "list_reports"
            reports = _list(client, "jobs/" + quote(job["id"], safe="") + "/reports", "reports")
            done = set(state.get("processed_report_ids", []))
            pending = sorted((r for r in reports if r["id"] not in done),
                             key=lambda r: r.get("createTime", ""))[:7]
            updated = 0
            for report in pending:
                stage = "download_report"
                url = report["downloadUrl"]
                parsed = urlparse(url)
                if parsed.scheme != "https" or parsed.hostname not in {
                    "youtubereporting.googleapis.com", "youtubeanalytics.googleapis.com",
                    "www.googleapis.com"
                }:
                    raise ValueError("Unexpected authenticated report host")
                # Bounded download, no credential forwarding to arbitrary redirects.
                chunks, size = [], 0
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 20_000_000:
                            raise ValueError("Reach report exceeds size limit")
                        chunks.append(chunk)
                updated += ingest_csv(data, b"".join(chunks).decode("utf-8-sig"), report, now)
                done.add(report["id"])
            state["processed_report_ids"] = sorted(done)[-200:]
            state["videos_updated"] = updated
            available = any(v.get("reach", {}).get("status") == "available" for v in data.get("videos", {}).values())
            state["status"] = "active" if available else "awaiting_report"
            state["message"] = "Daily bulk reports can lag. Missing rows are unknown; owner identity is not provided."
            state.pop("http_status", None)
            state.pop("error_type", None)
    except (httpx.HTTPError, ValueError, KeyError, StopIteration) as exc:
        state.update(_report_error(exc), stage=stage)
        state["message"] = "Reach collection failed; uploads can continue. See status and HTTP code."
    print("Reach reporting:", state["status"], "| videos updated:", state.get("videos_updated", 0))
    return True

