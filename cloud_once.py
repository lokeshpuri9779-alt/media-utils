from __future__ import annotations

import json, math, os, random, struct, subprocess, tempfile, wave
from pathlib import Path

import httpx
from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw, ImageFont

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"

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

def upload(video: Path, title: str, description: str) -> str:
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
            print("YouTube API upload limit reported; ending this run cleanly.")
            return ""
        raise RuntimeError("YouTube session failed: " + txt[:500])
    location = r.headers.get("location")
    if not location:
        raise RuntimeError("YouTube did not return an upload URL")
    with video.open("rb") as fh, httpx.Client(timeout=None) as client:
        r = client.put(location, headers={"Authorization":f"Bearer {token}","Content-Type":"video/mp4","Content-Length":str(size)}, content=fh)
    if r.status_code not in (200,201):
        txt = r.text
        if "uploadLimitExceeded" in txt:
            print("YouTube API upload limit reported; ending this run cleanly.")
            return ""
        raise RuntimeError("YouTube upload failed: " + txt[:500])
    vid = r.json().get("id","")
    return f"https://www.youtube.com/watch?v={vid}" if vid else ""

def main() -> None:
    need("YOUTUBE_CLIENT_ID"); need("YOUTUBE_CLIENT_SECRET"); need("YOUTUBE_REFRESH_TOKEN")
    work = Path(tempfile.mkdtemp(prefix="media_utils_run_"))
    video = work / "clip.mp4"
    title, desc = make_short(video)
    print("Generated:", title)
    url = upload(video, title, desc)
    if url:
        print("Published:", url)

if __name__ == "__main__":
    main()
