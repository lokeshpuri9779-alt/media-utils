from __future__ import annotations

import json, math, os, random, struct, subprocess, tempfile, wave, sys, re
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
SCHEDULE_SLOT_MINUTES = max(1, int(os.environ.get("ASTRA_SCHEDULE_SLOT_MINUTES", "30")))
CHANNELS_PATH = Path("channels.json")

def channel_profile() -> dict:
    key = (os.environ.get("ASTRA_CHANNEL") or "rayvan").strip().lower()
    data = json.loads(CHANNELS_PATH.read_text(encoding="utf-8"))
    profile = (data.get("channels") or {}).get(key)
    if not profile:
        raise RuntimeError(f"Unknown ASTRA_CHANNEL profile: {key}")
    if not profile.get("publish_enabled", False):
        raise RuntimeError(f"Publishing disabled for channel profile: {key}")
    return profile

def expected_channel_id() -> str:
    return str(channel_profile()["expected_channel_id"])
LAST_API_ERROR: dict | None = None


def api_error(response, stage: str) -> dict:
    """Capture API error details without credentials, headers or upload URLs."""
    global LAST_API_ERROR
    try:
        body = response.json().get("error", {})
    except (ValueError, AttributeError):
        body = {"message": "Non-JSON error response; body omitted."}
    if not isinstance(body, dict):
        body = {"message": str(body)}
    payload = {"stage": stage, "http_status": response.status_code,
               "code": body.get("code"), "status": body.get("status"),
               "message": body.get("message", ""),
               "errors": [{k: entry[k] for k in ("reason", "domain", "message", "locationType", "location") if k in entry}
                          for entry in body.get("errors", []) if isinstance(entry, dict)]}
    encoded = json.dumps(payload, ensure_ascii=False)
    for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"):
        value = os.environ.get(name)
        if value: encoded = encoded.replace(value, "[REDACTED]")
    encoded = re.sub(r"Bearer\s+[^\s\"\\]+", "Bearer [REDACTED]", encoded, flags=re.IGNORECASE)
    LAST_API_ERROR = json.loads(encoded)
    print("YouTube API diagnostic:", json.dumps(LAST_API_ERROR, ensure_ascii=False))
    return LAST_API_ERROR


def verify_channel(token: str) -> dict:
    with httpx.Client(timeout=60) as client:
        response = client.get("https://www.googleapis.com/youtube/v3/channels",
                              params={"part": "id,snippet", "mine": "true"},
                              headers={"Authorization": f"Bearer {token}"})
    if response.status_code >= 400:
        api_error(response, "channel_check")
        raise RuntimeError("Cannot verify the authorized channel; no upload attempted. See API diagnostic.")
    channels = response.json().get("items", [])
    ids = [c.get("id") for c in channels]
    print("Authorized channel IDs:", json.dumps(ids))
    print("Expected channel ID:", expected_channel_id())
    if ids != [expected_channel_id()]:
        raise RuntimeError("Authorized channel mismatch; no upload attempted. Reauthorize the intended YouTube channel.")
    print("Channel verified:", channels[0].get("snippet", {}).get("title", ""))
    return channels[0]

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
    # Spread attempts across the India-local day using the actual controller cadence.
    should_have_attempted = min(target, ((minutes + SCHEDULE_SLOT_MINUTES) * target) // 1440)
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
            "hook": random.choice(["CAN YOU SOLVE THIS?", "DON'T USE A CALCULATOR", "BEAT THIS IN 5 SEC"]),
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
            "title": "Can You Decode This Number Pattern? #Shorts",
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
            "title": "Iron or Cotton: Which Weighs More? #Shorts",
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

CONTENT_META = {}
MS_SOURCE = 'https://support.microsoft.com/en-us/accessibility/windows/keyboard-shortcuts-in-windows'
NASA_SOURCE = 'https://science.nasa.gov/venus/venus-facts/'
FOOT_SOURCE = 'https://www.theifab.com/laws/latest/offside/'

def content_catalog():
    # Original scripts; sources support facts, not copied article text.
    rows = [
        ('tech', 'clipboard', 'YOUR LAST COPY?', 'Copied something else?\nWindows can keep\na clipboard history.', 'Press Win + V.\nEnable history first.\nAvoid storing secrets.', 'Windows clipboard history in seconds', MS_SOURCE, ['windows', 'microsoft', 'computer']),
        ('tech', 'screenshot', 'CAPTURE JUST A BIT', 'Need one part\nof your screen?', 'Win + Shift + S\nopens screen snipping.\nSelect the area.', 'Capture part of your Windows screen', MS_SOURCE, ['windows', 'microsoft', 'computer']),
        ('tech', 'taskmanager', 'FIND THE BUSY APP', 'Which app is using\nyour computer resources?', 'Ctrl + Shift + Esc\nopens Task Manager.\nCheck the Processes tab.', 'Open Task Manager with one shortcut', MS_SOURCE, ['windows', 'microsoft', 'computer']),
        ('space', 'venus-spin', 'A VERY SLOW SPIN', 'Venus takes about\n243 Earth days\nto rotate once.', 'Its orbit takes\nabout 225 Earth days.\nOne spin outlasts a year.', 'Venus rotates slower than it orbits', NASA_SOURCE, ['venus', 'nasa', 'space', 'planet']),
        ('space', 'venus-heat', 'HOTTER THAN MERCURY', 'Venus is the hottest\nplanet in our\nsolar system.', 'Its thick atmosphere\ntraps heat through\nthe greenhouse effect.', 'Why Venus is the hottest planet', NASA_SOURCE, ['venus', 'nasa', 'space', 'planet']),
        ('football', 'offside-position', 'OFFSIDE? NOT YET', 'Standing in an\noffside position\nis not itself an offence.', 'The player must become\ninvolved in active play,\nas defined by Law 11.', 'Offside position is not an offence by itself', FOOT_SOURCE, ['football', 'barcelona', 'real madrid', 'arsenal', 'man city']),
        ('football', 'throw-offside', 'THE THROW-IN RULE', 'Can receiving a\nthrow-in directly\nmake you offside?', 'No offside offence\nfrom receiving a\nthrow-in directly.', 'The throw-in offside exception', FOOT_SOURCE, ['football', 'barcelona', 'real madrid', 'arsenal', 'man city']),
        ('football', 'added-time', 'WHY THE EXTRA TIME?', 'The board shows\na minimum amount\nof added time.', 'The referee can\nincrease it,\nbut cannot reduce it.', 'Added time is a minimum', 'https://www.theifab.com/laws/latest/the-duration-of-the-match/', ['football', 'barcelona', 'real madrid', 'arsenal', 'man city']),
        ('fiction', 'last-signal', 'THE LAST SIGNAL', 'The empty spaceship\nreceived a message:\n"Stop looking for us."', 'It came from Earth.\nEarth had vanished\na hundred years ago.', 'The last signal | Original microfiction', '', []),
        ('fiction', 'door', 'THE EXTRA DOOR', 'Every night, a new\ndoor appeared\nin her tiny flat.', 'Tonight she opened one.\nOn the other side,\nshe was knocking.', 'The extra door | Original microfiction', '', []),
        ('fiction', 'robot', 'ONE LAST ORDER', 'The old robot was\ntold to guard\na single seed.', 'A thousand years later,\nit finally rested\nin a forest.', 'One last order | Original microfiction', '', []),
    ]
    return [dict(genre=g, content_id=i, hook=h, question=q, answer=a,
                 title=t+' #Shorts', source=s, keywords=k, kind='explainer',
                 prompt='ORIGINAL FICTION' if g=='fiction' else 'THE SHORT EXPLANATION')
            for g,i,h,q,a,t,s,k in rows]

def fetch_trends(now=None):
    from email.utils import parsedate_to_datetime
    import xml.etree.ElementTree as ET
    now = now or datetime.now(IST)
    results = []
    # Search interest is a topic signal, never evidence for a factual claim.
    for region in __import__("revenue_geo").trend_regions(load_performance()):
        try:
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                response = client.get('https://trends.google.com/trending/rss', params={'geo': region})
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise ValueError('Oversized trend feed')
            root = ET.fromstring(response.content)
            for item in root.findall('./channel/item')[:30]:
                try:
                    date = parsedate_to_datetime(item.findtext('pubDate', ''))
                    age = (now-date).total_seconds()
                    title = item.findtext('title', '').strip()[:160]
                    if title and 0 <= age <= 48*3600:
                        results.append({'title': title, 'region': region, 'at': date.isoformat()})
                except (ValueError, TypeError, OverflowError):
                    continue
        except (httpx.HTTPError, ValueError, ET.ParseError):
            print('Trend feed unavailable:', region, '- using verified evergreen topics.')
    print('Fresh search-interest signals:', len(results))
    return results

def genre_scores(videos):
    """Raw public views cannot establish audience interest or exclude owner tests."""
    return {}

def choose_content(data, trends, now=None, excluded_ids=None, excluded_titles=None):
    import hashlib
    now = now or datetime.now(IST)
    videos = data.get('videos', {})
    recent = []
    for entry in videos.values():
        try:
            if (now-datetime.fromisoformat(entry['published_at'])).total_seconds() < 30*86400:
                recent.append(entry)
        except (KeyError, ValueError, TypeError):
            continue
    used = {v.get('content_id') for v in videos.values()}
    used.update(str(x) for x in (excluded_ids or set()) if x)
    used_titles = {normalize_content_text(t) for t in (excluded_titles or set()) if t}
    used_titles.update(normalize_content_text(v.get('title')) for v in videos.values() if v.get('title'))
    candidates = [c for c in content_catalog() if c['content_id'] not in used
                  and normalize_content_text(c['title']) not in used_titles]
    for _ in range(20):
        ch = _challenge()
        ch.update(genre='challenge', source='', keywords=[])
        ch['content_id'] = 'quiz-' + hashlib.sha256((ch['question']+ch['answer']).encode()).hexdigest()[:16]
        if ch['content_id'] not in used and normalize_content_text(ch['title']) not in used_titles:
            candidates.append(ch)
            break
    if not candidates:
        raise RuntimeError('No fresh content available; skipping rather than repeating.')
    # Diversity gate: RAYVAN is a broad discovery brand, not a repetitive
    # shortcut/quiz feed. Avoid recently used genres and content families.
    ordered_recent = sorted(recent, key=lambda x: x.get('published_at', ''), reverse=True)
    last_genres = [x.get('genre') for x in ordered_recent[:3] if x.get('genre')]
    if last_genres:
        # Never allow three consecutive uploads from one genre.
        if len(last_genres) >= 2 and last_genres[0] == last_genres[1]:
            diverse = [x for x in candidates if x.get('genre') != last_genres[0]]
            if diverse:
                candidates = diverse
        # Prefer a genre not used in the previous two uploads whenever possible.
        recent_genres = set(last_genres[:2])
        rotated = [x for x in candidates if x.get('genre') not in recent_genres]
        if rotated:
            candidates = rotated
    # Explicitly suppress Windows-shortcut fatigue: only one tech explainer
    # may appear inside the latest five tracked uploads.
    recent_five = ordered_recent[:5]
    if sum(x.get('genre') == 'tech' for x in recent_five) >= 1:
        nontech = [x for x in candidates if x.get('genre') != 'tech']
        if nontech:
            candidates = nontech
    for c in candidates:
        c['trend_matches'] = [t for t in trends if any(re.search(r'\b'+re.escape(k)+r'\b', t['title'], re.I) for k in c['keywords'])][:3]
    # Stage 0: rank concepts before rendering. With little clean channel evidence,
    # use structural priors + live demand; as analytics mature, genre evidence joins scoring.
    from viral_prior import rank_candidates
    strategy = data.get('strategy') or {}
    ranked = rank_candidates(candidates, strategy.get('genre_scores') or {}, data=data)
    # Winner evolution: boost fresh concepts that share only the abstract genre DNA
    # of measured healthy winners. Content IDs/scripts/assets are never cloned.
    blueprints = (data.get('evolution') or {}).get('winner_blueprints') or []
    winning_genres = {b.get('genre') for b in blueprints if b.get('genre')}
    for item in ranked:
        if item.get('genre') in winning_genres:
            item['prior_score']['total'] = round(min(100, item['prior_score']['total'] + 5), 2)
            item['winner_descendant'] = True
    ranked.sort(key=lambda x: x['prior_score']['total'], reverse=True)
    if not ranked:
        raise RuntimeError('Stage-0 scorer produced no candidates.')
    # Mostly exploit the best concepts, while preserving a small exploration lane.
    from viral_prior import adaptive_exploration
    explore_rate = adaptive_exploration(data)
    explore = random.random() < explore_rate and len(ranked) > 3
    if explore:
        counts = {g: sum(v.get('genre', 'challenge')==g for v in videos.values()) for g in {c['genre'] for c in ranked}}
        minimum = min(counts.values())
        pool = [c for c in ranked if counts[c['genre']] == minimum][:3] or ranked[:3]
        selected = dict(random.choice(pool))
        reason = 'stage0 exploration'
    else:
        selected = dict(random.choice(ranked[:min(3, len(ranked))]))
        reason = 'stage0 viral-prior ranking'
    selected['selection_reason'] = reason
    selected['stage0_rank'] = next((i+1 for i,c in enumerate(ranked) if c['content_id']==selected['content_id']), None)
    selected['stage0_score'] = selected.get('prior_score', {})
    selected['exploration_rate'] = explore_rate
    return selected

def select_content(excluded_ids=None, excluded_titles=None):
    global CONTENT_META
    from audience_research import research_signals
    data = load_performance()
    trends = fetch_trends() + research_signals(data, datetime.now(IST))
    ch = choose_content(data, trends, excluded_ids=excluded_ids, excluded_titles=excluded_titles)
    CONTENT_META = {k:ch.get(k) for k in ('genre','content_id','source','trend_matches','selection_reason','stage0_rank','stage0_score','winner_descendant','exploration_rate','hook','question','prompt','answer','script','realistic_synthetic','altered_real_event','synthetic_real_person','reused_third_party_media','transformative_commentary','copyright_unlicensed')}
    print('Content decision:', json.dumps(CONTENT_META, ensure_ascii=False))
    return ch


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

def make_short(out: Path, excluded_ids=None, excluded_titles=None) -> tuple[str, str]:
    from studio_renderer import render_short
    ch = select_content(excluded_ids=excluded_ids, excluded_titles=excluded_titles)
    report = render_short(ch, out)
    CONTENT_META.update(format="short", renderer=report["renderer"], duration=report["duration"],
                        voice=report["audio"]["voice"], scene_count=len(report["scenes"]))
    desc = " ".join(ch["question"].split()) + "\n" + " ".join(ch["answer"].split())
    if ch["genre"] == "fiction":
        desc += "\nAn original fictional short story."
    elif ch.get("source"):
        desc += "\nSource: " + ch["source"]
    desc += "\nOriginal motion graphics and music. AI-assisted script and synthetic narration."
    desc += "\n#Shorts #" + ch["genre"].title()
    related = [(vid, info) for vid, info in load_performance().get("videos", {}).items()
               if info.get("format") == "long" and info.get("genre") == ch["genre"]
               and info.get("visibility") == "public"]
    if related:
        vid, _ = max(related, key=lambda pair: pair[1].get("published_at", ""))
        desc += "\nFull explainer on our channel: https://www.youtube.com/watch?v=" + vid
    desc += "\nSubscribe: https://www.youtube.com/channel/" + expected_channel_id() + "?sub_confirmation=1"
    return ch["title"], desc

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

def upload(video: Path, title: str, description: str, token: str | None = None) -> tuple[str, str]:
    if token is None:
        token = access_token()
        verify_channel(token)
    privacy = (os.environ.get("YOUTUBE_PRIVACY") or "public").lower()
    if privacy not in {"private","unlisted","public"}:
        privacy = "public"
    size = video.stat().st_size
    metadata = {
        "snippet": {"title": title[:100], "description": description[:5000], "categoryId": "24"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": bool(CONTENT_META.get("ai_disclosure_required", False))},
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
        error = api_error(r, "upload_session")
        if any(e.get("reason") == "uploadLimitExceeded" for e in error["errors"]):
            return "limit", ""
        raise RuntimeError("YouTube session failed; see structured API diagnostic.")
    location = r.headers.get("location")
    if not location:
        raise RuntimeError("YouTube did not return an upload URL")
    with video.open("rb") as fh, httpx.Client(timeout=None) as client:
        r = client.put(location, headers={"Authorization":f"Bearer {token}","Content-Type":"video/mp4","Content-Length":str(size)}, content=fh)
    if r.status_code not in (200,201):
        error = api_error(r, "upload_transfer")
        if any(e.get("reason") == "uploadLimitExceeded" for e in error["errors"]):
            return "limit", ""
        raise RuntimeError("YouTube upload failed; see structured API diagnostic.")
    result = r.json()
    vid = result.get("id", "")
    CONTENT_META["visibility"] = result.get("status", {}).get("privacyStatus", "unknown")
    if not vid:
        raise RuntimeError("Upload response has no video ID; check Studio before retrying.")
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

def normalize_content_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

def live_channel_history(token: str) -> tuple[set[str], set[str]]:
    """Fetch recent authenticated upload identities once for pre-render dedupe."""
    with httpx.Client(timeout=60) as client:
        ch = client.get("https://www.googleapis.com/youtube/v3/channels",
            params={"part":"contentDetails","mine":"true"},
            headers={"Authorization":f"Bearer {token}"})
        if ch.status_code >= 400:
            api_error(ch, "dedupe_channel")
            raise RuntimeError("Cannot verify live upload history; refusing upload.")
        items = ch.json().get("items", [])
        uploads = (((items[0] if items else {}).get("contentDetails") or {})
                   .get("relatedPlaylists") or {}).get("uploads")
        if not uploads:
            raise RuntimeError("Cannot resolve live uploads playlist; refusing upload.")
        pl = client.get("https://www.googleapis.com/youtube/v3/playlistItems",
            params={"part":"snippet","playlistId":uploads,"maxResults":50},
            headers={"Authorization":f"Bearer {token}"})
        if pl.status_code >= 400:
            api_error(pl, "dedupe_playlist")
            raise RuntimeError("Cannot read live upload history; refusing upload.")
    titles, ids = set(), set()
    for item in pl.json().get("items", []):
        snippet = item.get("snippet") or {}
        title = normalize_content_text(snippet.get("title"))
        if title:
            titles.add(title)
        description = str(snippet.get("description") or "")
        ids.update(re.findall(r"ASTRA-ID:([^\s]+)", description))
    return titles, ids


def live_channel_duplicate(token: str, title: str, content_id: str) -> bool:
    """Use the authenticated channel as a second source of truth before publishing."""
    titles, ids = live_channel_history(token)
    cid = str(content_id or "").strip()
    return normalize_content_text(title) in titles or bool(cid and cid in ids)

def content_already_published(content_id: str) -> bool:
    """Fail closed when a generated concept is already in persistent channel history."""
    cid = str(content_id or "").strip()
    if not cid:
        return False
    return any(str(info.get("content_id") or "").strip() == cid
               for info in load_performance().get("videos", {}).values())

def record_video(video_id: str, title: str) -> None:
    if not video_id:
        return
    data = load_performance()
    videos = data.setdefault("videos", {})
    item = videos.setdefault(video_id, {})
    item.setdefault("title", title)
    item.setdefault("published_at", datetime.now(IST).isoformat())
    item.setdefault("history", [])
    item.update(CONTENT_META)
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
    body = "# RAYVAN Video Feed\n\nStories Beyond the Ordinary. Original videos generated by Astra.\n\n" + "\n".join(rows) + "\n"
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
        print(f"Highest raw view count (owner views may be included): {top[2]} | {top[0]} views | https://www.youtube.com/watch?v={top[1]}")

def refresh_research(token, force=False):
    from audience_research import collect
    from autonomy import manage_community, refresh_analytics
    from reach_reports import refresh_reach
    data=load_performance()
    now=datetime.now(IST)
    changed=collect(token,data,now,force=force)
    if refresh_analytics(data,now,force=force):
        changed=True
    if refresh_reach(data,now,force=force):
        changed=True
    if manage_community(data,now):
        changed=True
    if changed:
        save_performance(data)


def make_long(out, episode_id):
    global CONTENT_META
    from longform import render
    title,description,report=render(out, episode_id=episode_id)
    CONTENT_META={k:report[k] for k in ('renderer','format','genre','content_id','duration','scene_count')}
    from longform import SOURCES
    CONTENT_META['source']='; '.join(SOURCES)
    CONTENT_META['script']='original sourced long-form narration'
    CONTENT_META['voice']=report['audio']['voice']
    CONTENT_META['selection_reason']='weekly long-form slot; new sourced episode'
    return title,description


def set_thumbnail(video_id,path,token):
    if not path.exists():return False
    try:
        with httpx.Client(timeout=45) as client:
            r=client.post('https://www.googleapis.com/upload/youtube/v3/thumbnails/set',
                params={'videoId':video_id,'uploadType':'media'},
                headers={'Authorization':'Bearer '+token,'Content-Type':'image/jpeg'},content=path.read_bytes())
        if r.status_code>=400:
            print('Thumbnail not set; video upload remains successful. HTTP',r.status_code)
            return False
        print('Custom thumbnail set:',video_id)
        return True
    except httpx.HTTPError:
        print('Thumbnail network unavailable; video upload remains successful.')
        return False



def main() -> None:
    need("YOUTUBE_CLIENT_ID"); need("YOUTUBE_CLIENT_SECRET"); need("YOUTUBE_REFRESH_TOKEN")
    now = datetime.now(IST)
    state = load_state(now)
    token = access_token()
    verify_channel(token)
    if "--diagnose" in sys.argv:
        print("READ-ONLY DIAGNOSTIC COMPLETE: no video generated, no upload attempted, no state modified.")
        print("Saved upload state:", json.dumps(state))
        return
    if "--study" in sys.argv:
        refresh_performance()
        refresh_research(token)
        print("RESEARCH COMPLETE: no video upload attempted.")
        return
    probe_id = (os.environ.get("ASTRA_PROBE_ID") or "").strip()
    if probe_id:
        if state.get("last_probe_id") == probe_id:
            print("This controlled upload probe was already reserved; refusing a duplicate attempt.")
            return
        state["last_probe_id"] = probe_id
    save_state(state)

    force = (os.environ.get("ASTRA_FORCE_RUN") or "").strip() == "1"
    print(f"Adaptive daily target: {state['target']} | attempts: {state['attempts']} | successes: {state['successes']} | limit_hit: {state['limit_hit']}")

    # Cheap gates first: no analytics/research API work when publishing is already
    # paused, the daily attempt budget is exhausted, or this slot is not due.
    if state.get("limit_hit") and not force:
        print("Paused after an earlier API uploadLimitExceeded response. No fresh upload test occurred in this run.")
        print("The India-local day reset is Astra scheduling behavior, not a confirmed YouTube reset time.")
        return
    if int(state.get("attempts", 0)) >= int(state["target"]) and not force:
        print("Daily upload attempt target reached.")
        return
    if not force and not scheduled_attempt_due(now, state):
        print("No upload attempt due in this scheduled slot.")
        return

    # Refresh evidence only when this run can actually produce content.
    refresh_performance()
    refresh_research(token)
    from longform import choose_episode
    long_episode = choose_episode(load_performance(), now) if os.environ.get("ASTRA_LONG_ENABLED", "1") == "1" else None

    # Reconcile recent live channel identities before rendering so duplicate
    # concepts do not consume renderer/voice/FFmpeg time.
    live_titles, live_ids = live_channel_history(token)
    persisted_ids = {
        str(info.get("content_id") or "").strip()
        for info in load_performance().get("videos", {}).values()
        if str(info.get("content_id") or "").strip()
    }
    pre_render_excluded = persisted_ids | live_ids

    work = Path(tempfile.mkdtemp(prefix="media_utils_run_"))
    video = work / "clip.mp4"
    title, desc = make_long(video, long_episode) if long_episode else make_short(video, excluded_ids=pre_render_excluded, excluded_titles=live_titles)
    from distribution import branded_description
    perf = load_performance()
    desc, distribution_plan = branded_description(
        desc, perf,
        genre=str(CONTENT_META.get("genre") or "unknown"),
        fmt=str(CONTENT_META.get("format") or ("long" if long_episode else "short")),
    )
    from distribution import optimize_title
    title = optimize_title(title, distribution_plan, CONTENT_META)
    CONTENT_META["distribution_plan"] = distribution_plan
    from revenue_geo import geography_state
    CONTENT_META["revenue_geography"] = geography_state(perf)
    from ypp_safety import enforce
    ypp_report = enforce(title, desc, CONTENT_META, perf)
    CONTENT_META["ypp_safety"] = ypp_report
    CONTENT_META["ai_disclosure_required"] = bool(ypp_report.get("ai_disclosure_required"))
    print("Distribution plan:", json.dumps(distribution_plan, ensure_ascii=False))
    print("Revenue geography:", json.dumps(CONTENT_META["revenue_geography"], ensure_ascii=False))
    print("YPP safety:", json.dumps(ypp_report, ensure_ascii=False))
    print("Generated:", title)

    # Final transactional dedupe gate. Selection already avoids recent content,
    # but persistent state can change between selection/render and upload.
    content_id = str(CONTENT_META.get("content_id") or "").strip()
    if content_id and content_already_published(content_id):
        print("Duplicate content blocked before upload:", content_id)
        state["duplicate_blocks"] = int(state.get("duplicate_blocks", 0)) + 1
        save_state(state)
        return
    # Embed a machine-readable identity in every new description and reconcile
    # against YouTube itself. If the live history cannot be read, fail closed.
    if content_id:
        desc += "\nASTRA-ID:" + content_id
    excluded_live = set(pre_render_excluded)
    for retry in range(4):
        if not live_channel_duplicate(token, title, content_id):
            break
        print("Duplicate content blocked by live YouTube history:", content_id or title)
        state["duplicate_blocks"] = int(state.get("duplicate_blocks", 0)) + 1
        excluded_live.add(content_id)
        if long_episode:
            save_state(state)
            return
        if retry == 3:
            print("No fresh live-safe concept found after four selections; skipping this slot.")
            save_state(state)
            return
        print("Reselecting a fresh concept in the same scheduled run.")
        live_titles.add(normalize_content_text(title))
        title, desc = make_short(video, excluded_ids=excluded_live, excluded_titles=live_titles)
        perf = load_performance()
        desc, distribution_plan = branded_description(
            desc, perf, genre=str(CONTENT_META.get("genre") or "unknown"), fmt="short"
        )
        title = optimize_title(title, distribution_plan, CONTENT_META)
        CONTENT_META["distribution_plan"] = distribution_plan
        CONTENT_META["revenue_geography"] = geography_state(perf)
        ypp_report = enforce(title, desc, CONTENT_META, perf)
        CONTENT_META["ypp_safety"] = ypp_report
        CONTENT_META["ai_disclosure_required"] = bool(ypp_report.get("ai_disclosure_required"))
        content_id = str(CONTENT_META.get("content_id") or "").strip()
        if content_id and content_already_published(content_id):
            excluded_live.add(content_id)
            continue
        if content_id:
            desc += "\nASTRA-ID:" + content_id

    # Every exit from the retry loop must pass both sources of truth. In
    # particular, a final persisted-history collision cannot fall through.
    if content_already_published(content_id) or live_channel_duplicate(token, title, content_id):
        state["duplicate_blocks"] = int(state.get("duplicate_blocks", 0)) + 1
        save_state(state)
        raise RuntimeError("Fresh content selection exhausted; no upload attempted.")

    try:
        status, url = upload(video, title, desc, token=token)
        state["attempts"] = int(state.get("attempts", 0)) + 1
        if status == "success":
            state["limit_hit"] = False
            state["successes"] = int(state.get("successes", 0)) + 1
            print("Uploaded:", url, "| returned visibility:", CONTENT_META.get("visibility", "unknown"))
            video_id = url.rsplit("=", 1)[-1] if "=" in url else ""
            record_video(video_id, title)
            if CONTENT_META.get("format") == "long":
                set_thumbnail(video_id, video.with_suffix(".jpg"), token)
            from ops_guardian import healthy
            healthy()
        elif status == "limit":
            state["limit_hit"] = True
            state["last_api_error"] = LAST_API_ERROR
            from ops_guardian import record_event
            record_event("quota_pause", {"stage": "upload", "reason": "uploadLimitExceeded"})
            print("YouTube API upload limit reported. Guardian paused further scheduled probes for today.")
    except Exception as exc:
        state["attempts"] = int(state.get("attempts", 0)) + 1
        state["other_failures"] = int(state.get("other_failures", 0)) + 1
        if LAST_API_ERROR is not None: state["last_api_error"] = LAST_API_ERROR
        from ops_guardian import classify, record_event
        kind = classify(LAST_API_ERROR, type(exc).__name__)
        ops = record_event(kind, {"exception_type": type(exc).__name__, "api_stage": (LAST_API_ERROR or {}).get("stage")})
        state["ops_status"] = ops.get("status")
        state["human_action_required"] = ops.get("human_action_required")
        save_state(state)
        raise

    save_state(state)

if __name__ == "__main__":
    main()

# Owner-requested single upload retry: 2026-10-04 17:11 IST.

# Owner-requested single upload retry: 2026-10-04 22:51 IST.
