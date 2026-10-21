#!/usr/bin/env python3
"""Monitor GitHub scheduled publisher executions without dispatching or publishing."""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
OWNER_REPO = os.environ["GITHUB_REPOSITORY"]
WORKFLOW = os.environ.get("ASTRA_PUBLISHER_WORKFLOW", "astra-v2-publish.yml")
MAX_GAP_MINUTES = int(os.environ.get("ASTRA_WATCHDOG_MAX_GAP_MINUTES", "45"))
NOW = dt.datetime.now(dt.timezone.utc)

def get_json(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + os.environ["GH_TOKEN"],
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "astra-schedule-watchdog",
    })
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)

def parse_time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

def main():
    if MAX_GAP_MINUTES < 10:
        raise ValueError("Watchdog threshold must be at least 10 minutes")
    params = urllib.parse.urlencode({"event": "schedule", "per_page": 100})
    url = f"{API}/repos/{OWNER_REPO}/actions/workflows/{urllib.parse.quote(WORKFLOW)}/runs?{params}"
    runs = get_json(url).get("workflow_runs", [])
    scheduled = sorted((r for r in runs if r.get("event") == "schedule"), key=lambda r: r.get("created_at", ""), reverse=True)
    latest = scheduled[0] if scheduled else None
    age = round((NOW - parse_time(latest["created_at"])).total_seconds() / 60, 1) if latest else None
    # Runs API uses created_at (run record creation), not exact cron delivery time.
    alert = age is None or age > MAX_GAP_MINUTES
    result = {
        "checked_at": NOW.isoformat(),
        "workflow": WORKFLOW,
        "scheduled_runs_sampled": len(scheduled),
        "latest_scheduled_run": latest.get("html_url") if latest else None,
        "latest_scheduled_created_at": latest.get("created_at") if latest else None,
        "latest_scheduled_conclusion": latest.get("conclusion") if latest else None,
        "minutes_since_latest_scheduled_run": age,
        "threshold_minutes": MAX_GAP_MINUTES,
        "alert": alert,
        "monitor_only": True,
    }
    print(json.dumps(result, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("## ASTRA publisher schedule watchdog\\n\\n")
            out.write(f"- Status: {'ALERT' if alert else 'OK'}\\n")
            out.write(f"- Latest scheduled run: {result['latest_scheduled_run']}\\n")
            out.write(f"- Minutes since last scheduled run: {age}\\n")
            out.write("- Monitor only: no workflow dispatch, upload, or production state changes.\\n")
    if alert:
        print("::warning::ASTRA publisher scheduled execution is overdue or unavailable")
    return 0  # Alert through logs/summary, not a failing workflow.

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (urllib.error.URLError, ValueError, KeyError) as exc:
        print(f"::warning::ASTRA watchdog could not assess scheduling: {exc}")
        sys.exit(0)  # Fail open for monitoring; never block publisher.
