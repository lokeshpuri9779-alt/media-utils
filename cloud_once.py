from __future__ import annotations

import json, math, os, random, struct, subprocess, tempfile, wave
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw, ImageFont

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
PERFORMANCE_PATH = Path("performance.json")
STATE_PATH = Path("quota_state.json")
IST = ZoneInfo("Asia/Kolkata")
INITIAL_TARGET = int(os.environ.get("ASTRA_INITIAL_DAILY_TARGET", "9"))
MAX_TARGET = int(os.environ.get("ASTRA_MAX_DAILY_TARGET", "24"))

def need(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise RuntimeError(f"Missing required GitHub secret: {name}")
    return value

def font(size: int):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()

def fresh_state(today: str, target: int | None = None) -> dict:
    return {
        "date": today,
        "target": max(1, min(MAX_TARGET, target or INITIAL_TARGET)),
        "attempts": 0,
        "successes": 0,
        "limit_hit": False,
        "other_failures": 0,
        "previous_day": None,
    }

def load_state(now: datetime) -> dict:
    today = now.date().isoformat()
    if not STATE_PATH.exists():
        return fresh_state(today)
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return fresh_state(today)

    if state.get("date") == today:
        return state

    previous = dict(state)
    old_target = int(previous.get("target", INITIAL_TARGET))
    successes = int(previous.get("successes", 0))
    attempts = int(previous.get("attempts", 0))
    limit_hit = bool(previous.get("limit_hit", False))
    other_failures = int(previous.get("other_failures", 0))

    # Learn yesterday's practical ceiling, then probe exactly one step higher.
    # If the first API attempt was already blocked, no useful ceiling was learned,
    # so keep the prior target rather than collapsing to 1/day.
    if limit_hit and successes > 0:
        next_target = successes + 1
    elif not limit_hit and other_failures == 0 and attempts >= old_target and successes >= old_target:
        next_target = old_target + 1
    else:
        next_target = old_target

    new_state = fresh_state(today, next_target)
    new_state["previous_day"] = {
        "date": previous.get("date"),
        "target": old_target,
        "attempts": attempts,
        "successes": successes,
        "limit_hit": limit_hit,
    }
    return new_state

def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

def scheduled_attempt_due(now: datetime, state: dict) -> bool:
    if state.get("limit_hit"):
        return False
    target = max(1, min(MAX_TARGET, int(state.get("target", INITIAL_TARGET))))
    attempts = int(state.get("attempts", 0))
    minutes = now.hour * 60 + now.minute
    # Runs are hourly. This spreads the target across the full India-local day.
    should_have_attempted = min(target, ((minutes + 60) * target) // 1440)
    return attempts < should_have_attempted

def make_short(out: Path) -> tuple[str, str]:
    ideas = [
        ("Can You Beat This 10-Second Challenge? 🧠 #Shorts", ["MEMORIZE", "7  3  9  2", "NOW HIDE IT", "What was the 3rd number?", "ANSWER: 9"]),
        ("Most People Get This Wrong 😈 #Shorts", ["READY?", "Which is heavier?", "1 kg iron", "or 1 kg cotton?", "ANSWER: SAME"]),
        ("Quick Brain Test ⚡ #Shorts", ["FOCUS", "RED  BLUE  GREEN", "Say the COLOR", "not the word", "Did you get it?"]),
    ]
    title, cards = random.choice(ideas)
    desc = "Fast brain challenge. Comment your answer before the reveal. #Shorts #challenge #brain"

    work = Path(tempfile.mkdtemp(prefix="media_utils_"))
    frames = work / "frames"
    frames.mkdir()
    fps = 30
    seconds_per_card = 2
    total_seconds = len(cards) * seconds_per_card

    f_big = font(72)
    f_small = font(42)
    for i in range(total_seconds * fps):
        card_idx = min(len(cards)-1, i // (seconds_per_card * fps))
        im = Image.new("RGB", (720, 1280), (18, 20, 28))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((55, 160, 665, 1120), radius=48, fill=(35, 39, 55))
        text = cards[card_idx]
        bb = d.multiline_textbbox((0,0), text, font=f_big, align="center", spacing=16)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        d.multiline_text(((720-tw)/2, (1280-th)/2), text, font=f_big, fill=(245,245,245), align="center", spacing=16)
        d.text((360, 1030), "LOKI", font=f_small, fill=(175,175,185), anchor="mm")
        im.save(frames / f"{i:05d}.png", quality=90)

    wav = work / "tone.wav"
    rate = 44100
    with wave.open(str(wav), "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        for n in range(total_seconds * rate):
            t = n / rate
            amp = 0.08 if int(t*2) % 2 == 0 else 0.05
            val = int(32767 * amp * math.sin(2*math.pi*(220 + 40*math.sin(t))*t))
            wf.writeframes(struct.pack("<h", val))

    ffmpeg = get_ffmpeg_exe()
    subprocess.run([
        ffmpeg, "-y", "-framerate", str(fps), "-i", str(frames / "%05d.png"),
        "-i", str(wav), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return title, desc

def access_token() -> str:
    with httpx.Client(timeout=30) as client:
        r = client.post(TOKEN_URL, data={
            "client_id": need("YOUTUBE_CLIENT_ID"),
            "client_secret": need("YOUTUBE_CLIENT_SECRET"),
            "refresh_token": need("YOUTUBE_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        })
    if r.status_code >= 400:
        raise RuntimeError("OAuth refresh failed: " + r.text[:400])
    return r.json()["access_token"]

def upload(video: Path, title: str, description: str) -> tuple[str, str]:
    token = access_token()
    privacy = (os.environ.get("YOUTUBE_PRIVACY") or "public").lower()
    if privacy not in {"private","unlisted","public"}:
        privacy = "public"
    size = video.stat().st_size
    metadata = {
        "snippet": {"title": title[:100], "description": description[:5000], "categoryId": "24"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(size),
    }
    with httpx.Client(timeout=60) as client:
        r = client.post(UPLOAD_URL, params={"uploadType":"resumable","part":"snippet,status"}, headers=headers, json=metadata)
    if r.status_code >= 400:
        txt = r.text
        if "uploadLimitExceeded" in txt:
            return "limit", ""
        raise RuntimeError("YouTube session failed: " + txt[:500])
    location = r.headers.get("location")
    if not location:
        raise RuntimeError("YouTube did not return an upload URL")
    with video.open("rb") as fh, httpx.Client(timeout=None) as client:
        r = client.put(location, headers={"Authorization":f"Bearer {token}","Content-Type":"video/mp4","Content-Length":str(size)}, content=fh)
    if r.status_code not in (200,201):
        txt = r.text
        if "uploadLimitExceeded" in txt:
            return "limit", ""
        raise RuntimeError("YouTube upload failed: " + txt[:500])
    vid = r.json().get("id","")
    return "success", (f"https://www.youtube.com/watch?v={vid}" if vid else "")


def load_performance() -> dict:
    if not PERFORMANCE_PATH.exists():
        return {"videos": {}}
    try:
        data = json.loads(PERFORMANCE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "videos" not in data:
            return {"videos": {}}
        return data
    except Exception:
        return {"videos": {}}

def save_performance(data: dict) -> None:
    PERFORMANCE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def record_video(video_id: str, title: str) -> None:
    if not video_id:
        return
    data = load_performance()
    videos = data.setdefault("videos", {})
    item = videos.setdefault(video_id, {})
    item.setdefault("title", title)
    item.setdefault("published_at", datetime.now(IST).isoformat())
    item.setdefault("history", [])
    save_performance(data)

def refresh_performance() -> None:
    data = load_performance()
    videos = data.get("videos", {})
    ids = list(videos.keys())
    if not ids:
        return

    token = access_token()
    for i in range(0, len(ids), 50):
        batch = ids[i:i+50]
        with httpx.Client(timeout=30) as client:
            r = client.get(
                VIDEOS_URL,
                params={"part":"snippet,statistics","id":",".join(batch)},
                headers={"Authorization": f"Bearer {token}"},
            )
        if r.status_code >= 400:
            print("Performance refresh skipped:", r.text[:300])
            return

        now_iso = datetime.now(IST).isoformat()
        for item in r.json().get("items", []):
            vid = item.get("id", "")
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            if vid not in videos:
                continue
            entry = videos[vid]
            entry["title"] = snippet.get("title", entry.get("title", ""))
            snapshot = {
                "at": now_iso,
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)) if "likeCount" in stats else None,
                "comments": int(stats.get("commentCount", 0)) if "commentCount" in stats else None,
            }
            history = entry.setdefault("history", [])
            if not history or history[-1] != snapshot:
                history.append(snapshot)
                entry["latest"] = snapshot

    save_performance(data)
    ranked = []
    for vid, entry in videos.items():
        latest = entry.get("latest") or {}
        ranked.append((int(latest.get("views") or 0), vid, entry.get("title","")))
    ranked.sort(reverse=True)
    if ranked:
        top = ranked[0]
        print(f"Top tracked Short: {top[2]} | {top[0]} views | https://www.youtube.com/watch?v={top[1]}")

def main() -> None:
    need("YOUTUBE_CLIENT_ID"); need("YOUTUBE_CLIENT_SECRET"); need("YOUTUBE_REFRESH_TOKEN")
    now = datetime.now(IST)
    state = load_state(now)
    save_state(state)
    refresh_performance()

    force = (os.environ.get("ASTRA_FORCE_RUN") or "").strip() == "1"
    print(f"Adaptive daily target: {state['target']} | attempts: {state['attempts']} | successes: {state['successes']} | limit_hit: {state['limit_hit']}")

    if not force and not scheduled_attempt_due(now, state):
        print("No upload attempt due in this hourly slot.")
        return

    if state.get("limit_hit") and not force:
        print("Today's YouTube limit was already detected; next probe will be on the next India-local day.")
        return

    work = Path(tempfile.mkdtemp(prefix="media_utils_run_"))
    video = work / "clip.mp4"
    title, desc = make_short(video)
    print("Generated:", title)

    try:
        status, url = upload(video, title, desc)
        state["attempts"] = int(state.get("attempts", 0)) + 1
        if status == "success":
            state["successes"] = int(state.get("successes", 0)) + 1
            print("Published:", url)
            video_id = url.rsplit("=", 1)[-1] if "=" in url else ""
            record_video(video_id, title)
        elif status == "limit":
            state["limit_hit"] = True
            print("YouTube API upload limit reported. Recorded today's ceiling and stopped further scheduled probes for today.")
    except Exception:
        state["attempts"] = int(state.get("attempts", 0)) + 1
        state["other_failures"] = int(state.get("other_failures", 0)) + 1
        save_state(state)
        raise

    save_state(state)

if __name__ == "__main__":
    main()
