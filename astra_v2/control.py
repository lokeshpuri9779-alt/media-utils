"""Pure policy and durable state for the ASTRA V2 publisher."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
PACIFIC = ZoneInfo("America/Los_Angeles")
STATE_FILE = Path("astra_v2_state.json")
REPORT_FILE = Path("runtime-health/astra-v2-report.json")
QUOTA_REASONS = {"quotaExceeded", "uploadLimitExceeded", "dailyLimitExceeded", "userRateLimitExceeded"}


def utcnow():
    return datetime.now(timezone.utc)


def parse_time(raw):
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc) if raw else None
    except (ValueError, TypeError):
        return None


def read_json(path, fallback=None):
    try:
        result = json.loads(Path(path).read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else (fallback or {})
    except (OSError, ValueError):
        return fallback or {}


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def state_for_day(data=None, now=None):
    now = now or utcnow()
    day = now.astimezone(IST).date().isoformat()
    baseline = {
        "version": 2, "day": day, "created_at": now.isoformat(),
        "attempts": 0, "confirmed_today": 0, "last_attempt_at": "", "blocked_until": "",
        "quota_reason": "", "published": {}, "pending": {},
        "last_outcome": "new", "last_error": "",
    }
    if not isinstance(data, dict) or data.get("version") != 2:
        return baseline
    result = {**baseline, **data}
    if result["day"] != day:
        result.update(day=day, attempts=0, confirmed_today=0)
    for field in ("published", "pending"):
        if not isinstance(result.get(field), dict):
            result[field] = {}
    return result


def due(state, now=None, limit=48, spacing_minutes=25):
    now = now or utcnow()
    cooldown = parse_time(state.get("blocked_until"))
    if cooldown and now < cooldown:
        return False, "quota_cooldown"
    if int(state.get("attempts", 0)) >= limit:
        return False, "daily_cap"
    previous = parse_time(state.get("last_attempt_at"))
    if previous and now - previous < timedelta(minutes=spacing_minutes):
        return False, "min_interval"
    return True, "ready"


def quota_resume(now=None, reason="quotaExceeded"):
    now = now or utcnow()
    local = now.astimezone(PACIFIC)
    next_day = local.date() + timedelta(days=1)
    next_reset = datetime(next_day.year, next_day.month, next_day.day, 0, 20,
                          tzinfo=PACIFIC).astimezone(timezone.utc)
    if reason == "uploadLimitExceeded":
        return max(next_reset, now + timedelta(hours=24))
    return next_reset
