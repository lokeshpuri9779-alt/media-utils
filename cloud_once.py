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

def _ease_out_back(x: float) -> float:
    x = max(0.0, min(1.0, x))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

def _wrap(text: str, limit: int = 22) -> str:
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            if len(line) + 1 + len(word) <= limit:
                line += " " + word
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return "\n".join(lines)

def _challenge() -> dict:
    makers = []

    def arithmetic():
        a = random.randint(3, 9)
        b = random.randint(2, 6)
        c = random.randint(2, 5)
        ans = a + b * c
        return {
            "kind": "math",
            "hook": random.choice(["ONLY 10% GET THIS", "DON'T USE A CALCULATOR", "BEAT THIS IN 5 SEC"]),
            "question": f"{a} + {b} × {c} = ?",
            "prompt": "Order matters 👀",
            "answer": str(ans),
            "title": f"Can You Solve {a} + {b} × {c} in 5 Seconds? 🧠 #Shorts",
        }

    def memory():
        nums = [random.randint(1, 9) for _ in range(5)]
        pos = random.randint(1, 5)
        return {
            "kind": "memory",
            "hook": "MEMORIZE THIS",
            "question": "   ".join(map(str, nums)),
            "prompt": f"What was number #{pos}?",
            "answer": str(nums[pos-1]),
            "title": "5-Second Memory Test 🧠 Can You Pass? #Shorts",
        }

    def sequence():
        start = random.randint(1, 5)
        step = random.randint(2, 5)
        vals = [start + step * i for i in range(4)]
        answer = vals[-1] + step
        return {
            "kind": "sequence",
            "hook": "SPOT THE PATTERN",
            "question": "  →  ".join(map(str, vals)) + "  →  ?",
            "prompt": "You have 5 seconds",
            "answer": str(answer),
            "title": "What Comes Next? ⚡ Quick Pattern Test #Shorts",
        }

    def doubling():
        start = random.randint(2, 5)
        vals = [start * (2 ** i) for i in range(4)]
        answer = vals[-1] * 2
        return {
            "kind": "sequence",
            "hook": "TOO EASY... OR IS IT?",
            "question": "  →  ".join(map(str, vals)) + "  →  ?",
            "prompt": "Don't overthink it",
            "answer": str(answer),
            "title": "Most People Overthink This Number Pattern 😈 #Shorts",
        }

    def duplicate():
        pool = random.sample(range(1, 10), 5)
        dup = random.choice(pool)
        nums = pool + [dup]
        random.shuffle(nums)
        return {
            "kind": "duplicate",
            "hook": "FIND IT FAST",
            "question": "   ".join(map(str, nums)),
            "prompt": "Which number appears twice?",
            "answer": str(dup),
            "title": "Find the Duplicate Before Time Runs Out 👀 #Shorts",
        }

    def odd_grid():
        normal = random.choice(["8", "6", "9"])
        odd = {"8":"3", "6":"8", "9":"6"}[normal]
        row, col = random.randint(1, 4), random.randint(1, 4)
        rows = []
        for r in range(1, 5):
            cells = []
            for c in range(1, 5):
                cells.append(odd if (r == row and c == col) else normal)
            rows.append("   ".join(cells))
        return {
            "kind": "visual",
            "hook": "FIND THE ODD ONE",
            "question": "\n".join(rows),
            "prompt": "Where is it?",
            "answer": f"ROW {row} · COL {col}",
            "title": "Find the Odd Number in 5 Seconds 👀 #Shorts",
        }

    def trick_weight():
        return {
            "kind": "trick",
            "hook": "DON'T FALL FOR IT",
            "question": "Which is heavier?\n1 kg IRON\nor\n1 kg COTTON",
            "prompt": "Lock your answer",
            "answer": "THEY'RE THE SAME",
            "title": "Most People Answer This Too Fast 😈 #Shorts",
        }

    def riddle():
        bank = [
            ("I get wetter\nthe more I dry.\nWhat am I?", "A TOWEL"),
            ("What has hands\nbut cannot clap?", "A CLOCK"),
            ("What has a neck\nbut no head?", "A BOTTLE"),
            ("What goes up\nbut never comes down?", "YOUR AGE"),
        ]
        q, ans = random.choice(bank)
        return {
            "kind": "riddle",
            "hook": "QUICK RIDDLE",
            "question": q,
            "prompt": "5 seconds...",
            "answer": ans,
            "title": "Can You Solve This Riddle Before the Reveal? 🤯 #Shorts",
        }

    def missing():
        step = random.randint(3, 7)
        vals = [step * i for i in range(1, 6)]
        idx = random.randint(1, 3)
        ans = vals[idx]
        shown = vals[:]
        shown[idx] = "?"
        return {
            "kind": "missing",
            "hook": "WHAT'S MISSING?",
            "question": "   ".join(map(str, shown)),
            "prompt": "No calculator",
            "answer": str(ans),
            "title": "Find the Missing Number in 5 Seconds ⚡ #Shorts",
        }

    makers.extend([arithmetic, memory, sequence, doubling, duplicate, odd_grid, trick_weight, riddle, missing])
    return random.choice(makers)()

def _draw_centered(draw, xy, text, fnt, fill, max_width=920, spacing=18, shadow=True):
    text = _wrap(text, 23)
    while True:
        bb = draw.multiline_textbbox((0, 0), text, font=fnt, align="center", spacing=spacing)
        if bb[2] - bb[0] <= max_width or getattr(fnt, "size", 50) <= 42:
            break
        fnt = font(max(42, int(getattr(fnt, "size", 50) * 0.92)))
    x, y = xy
    if shadow:
        draw.multiline_text((x+6, y+8), text, font=fnt, fill=(0,0,0,145), anchor="mm",
                            align="center", spacing=spacing)
    draw.multiline_text((x, y), text, font=fnt, fill=fill, anchor="mm",
                        align="center", spacing=spacing)

def make_short(out: Path) -> tuple[str, str]:
    ch = _challenge()
    title = ch["title"]
    desc = (
        "Answer before the reveal — then comment if you got it right. "
        "#Shorts #BrainTeaser #Quiz #Challenge"
    )

    work = Path(tempfile.mkdtemp(prefix="media_utils_"))
    frames = work / "frames"
    frames.mkdir()

    width, height = 1080, 1920
    fps = 24
    total_seconds = 10
    total_frames = total_seconds * fps
    reveal_at = 7.4

    # Build a reusable high-resolution gradient once.
    base = Image.new("RGB", (width, height))
    bp = base.load()
    top = random.choice([(19,22,38), (15,25,42), (28,18,42), (17,31,36)])
    bottom = random.choice([(52,34,78), (26,64,88), (73,30,58), (28,80,69)])
    for y in range(height):
        t = y / max(1, height-1)
        c = tuple(int(top[i]*(1-t) + bottom[i]*t) for i in range(3))
        for x in range(width):
            bp[x, y] = c

    f_brand = font(46)
    f_hook = font(76)
    f_question = font(112 if ch["kind"] not in {"visual","riddle","trick"} else 78)
    f_prompt = font(58)
    f_answer = font(112)
    f_small = font(42)

    for i in range(total_frames):
        t = i / fps
        im = base.copy()
        overlay = Image.new("RGBA", (width, height), (0,0,0,0))
        d = ImageDraw.Draw(overlay)

        # Moving ambient shapes add motion without external assets.
        for k in range(7):
            phase = (t * (0.16 + 0.025*k) + k*0.17) % 1.0
            cx = int((0.08 + 0.84*phase) * width)
            cy = int((0.18 + ((k*0.19 + t*0.035) % 0.68)) * height)
            r = 70 + 22*(k % 3)
            d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(255,255,255,12))

        # Main card.
        card_y = 355
        card_h = 1160
        d.rounded_rectangle(
            (70, card_y, width-70, card_y+card_h),
            radius=72,
            fill=(10,12,20,188),
            outline=(255,255,255,28),
            width=3,
        )

        # Brand chip.
        d.rounded_rectangle((365, 92, 715, 172), radius=36, fill=(255,255,255,30))
        d.text((540, 132), "LOKI · QUICK TEST", font=f_brand, fill=(244,246,255,235), anchor="mm")

        # Hook pulse.
        hook_progress = min(1.0, t / 0.45)
        hook_y = 260 + int((1-_ease_out_back(hook_progress))*55)
        d.text((540+4, hook_y+6), ch["hook"], font=f_hook, fill=(0,0,0,150), anchor="mm")
        d.text((540, hook_y), ch["hook"], font=f_hook, fill=(255,229,92,255), anchor="mm")

        if t < reveal_at:
            # Question enters quickly and remains readable.
            q_in = min(1.0, max(0.0, (t-0.35)/0.45))
            q_y = 835 + int((1-_ease_out_back(q_in))*120)
            _draw_centered(d, (540, q_y), ch["question"], f_question, (250,250,253,255),
                           max_width=860, spacing=22)

            # Prompt.
            prompt_alpha = int(255 * min(1.0, max(0.0, (t-1.0)/0.5)))
            d.text((540, 1265), ch["prompt"], font=f_prompt,
                   fill=(190,205,235,prompt_alpha), anchor="mm")

            # Countdown in final 3 seconds before reveal.
            remaining = max(0.0, reveal_at - t)
            if remaining <= 3.2:
                n = max(1, int(math.ceil(remaining)))
                pulse = 1.0 + 0.10*math.sin((1-(remaining % 1))*math.pi)
                f_count = font(int(120*pulse))
                d.text((540, 1435), str(n), font=f_count, fill=(255,255,255,245), anchor="mm")
        else:
            # Reveal hit: flash + answer pop.
            reveal_t = t - reveal_at
            flash = max(0, int(135 * (1 - min(1.0, reveal_t/0.28))))
            if flash:
                d.rectangle((0,0,width,height), fill=(255,255,255,flash))
            pop = _ease_out_back(min(1.0, reveal_t/0.55))
            ay = 850 + int((1-pop)*110)
            d.text((540, 650), "ANSWER", font=f_prompt, fill=(255,229,92,255), anchor="mm")
            _draw_centered(d, (540, ay), ch["answer"], f_answer, (255,255,255,255),
                           max_width=850, spacing=18)
            d.text((540, 1160), "Did you get it? 👀", font=f_prompt,
                   fill=(192,224,255,255), anchor="mm")
            d.text((540, 1285), "COMMENT YOUR SCORE", font=f_small,
                   fill=(255,255,255,190), anchor="mm")

        # Progress bar creates urgency and gives constant motion.
        p = min(1.0, t / reveal_at) if t < reveal_at else 1.0
        x0, x1, yb = 140, 940, 1585
        d.rounded_rectangle((x0, yb, x1, yb+24), radius=12, fill=(255,255,255,35))
        d.rounded_rectangle((x0, yb, int(x0+(x1-x0)*p), yb+24), radius=12,
                            fill=(255,229,92,235))

        # Footer / replay cue.
        footer = "WAIT FOR THE REVEAL" if t < reveal_at else "NEXT ONE →"
        d.text((540, 1740), footer, font=f_small, fill=(240,242,250,175), anchor="mm")

        im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
        im.save(frames / f"{i:05d}.jpg", "JPEG", quality=90, subsampling=0)

    # Procedurally generated music + timing SFX: zero licensing cost.
    wav = work / "audio.wav"
    rate = 44100
    duration_samples = total_seconds * rate
    with wave.open(str(wav), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        for n in range(duration_samples):
            t = n / rate
            beat_phase = (t * 2.0) % 1.0
            kick_env = math.exp(-beat_phase * 18)
            kick = math.sin(2*math.pi*(68 - 20*beat_phase)*t) * kick_env

            arp_note = [220.0, 277.18, 329.63, 415.30][int(t*4) % 4]
            arp = math.sin(2*math.pi*arp_note*t) * 0.035
            bass = math.sin(2*math.pi*110*t) * 0.025

            tick = 0.0
            if 4.2 <= t < reveal_at:
                frac = abs((t*2) - round(t*2))
                if frac < 0.018:
                    tick = math.sin(2*math.pi*880*t) * math.exp(-frac*150) * 0.13

            reveal = 0.0
            rt = t - reveal_at
            if 0 <= rt < 0.65:
                reveal = (
                    math.sin(2*math.pi*(520 + 700*rt)*t) * math.exp(-rt*4.5) * 0.15
                    + math.sin(2*math.pi*1040*t) * math.exp(-rt*7) * 0.08
                )

            sample = 0.13*kick + arp + bass + tick + reveal
            sample = max(-0.92, min(0.92, sample))
            wf.writeframes(struct.pack("<h", int(sample * 32767)))

    ffmpeg = get_ffmpeg_exe()
    subprocess.run([
        ffmpeg, "-y",
        "-framerate", str(fps), "-i", str(frames / "%05d.jpg"),
        "-i", str(wav),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart",
        str(out)
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

    # Maintain a public, zero-cost backlink feed inside the GitHub repo.
    rows = []
    ordered = sorted(
        videos.items(),
        key=lambda pair: pair[1].get("published_at", ""),
        reverse=True,
    )
    for vid, info in ordered[:100]:
        safe_title = str(info.get("title") or "YouTube Short").replace("\n", " ").strip()
        published = str(info.get("published_at") or "")[:10]
        rows.append(f"- [{safe_title}](https://www.youtube.com/watch?v={vid}) · {published}")
    body = "# LOKI Quick Challenge Feed\n\nFresh YouTube Shorts generated by Astra.\n\n" + "\n".join(rows) + "\n"
    Path("SHORTS.md").write_text(body, encoding="utf-8")

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
