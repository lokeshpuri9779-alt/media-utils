from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import studio_renderer as studio


def _challenge_bank(seed: str, count: int = 20) -> list[dict]:
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16))
    riddles = [
        ("What has hands but cannot clap?", "A CLOCK"),
        ("What has a neck but no head?", "A BOTTLE"),
        ("What gets wetter the more it dries?", "A TOWEL"),
        ("What goes up but never comes down?", "YOUR AGE"),
        ("What has many keys but opens no locks?", "A PIANO"),
        ("What can travel around the world while staying in one corner?", "A STAMP"),
        ("What has one eye but cannot see?", "A NEEDLE"),
        ("What has words but never speaks?", "A BOOK"),
    ]
    out = []
    for i in range(count):
        mode = i % 4
        if mode == 0:
            a, b, c = rng.randint(3, 15), rng.randint(2, 9), rng.randint(2, 8)
            question = f"{a} + {b} × {c} = ?"
            answer = str(a + b * c)
            hint = "Multiplication first."
        elif mode == 1:
            start, step = rng.randint(1, 9), rng.randint(2, 8)
            vals = [start + step * k for k in range(4)]
            question = "  →  ".join(map(str, vals)) + "  →  ?"
            answer = str(vals[-1] + step)
            hint = "Find the repeating jump."
        elif mode == 2:
            start = rng.randint(2, 5)
            vals = [start * (2 ** k) for k in range(4)]
            question = "  →  ".join(map(str, vals)) + "  →  ?"
            answer = str(vals[-1] * 2)
            hint = "Each term changes the same way."
        else:
            question, answer = riddles[rng.randrange(len(riddles))]
            hint = "Think literally."
        out.append({"number": i + 1, "question": question, "answer": answer, "hint": hint})
    return out


def _plan(episode_id: str) -> tuple[list[dict], list[dict]]:
    challenges = _challenge_bank(episode_id)
    plan = [
        studio.scene(
            "20 BRAIN CHALLENGES",
            "Twenty quick brain challenges. Keep your score and see how many you can solve before the answer appears.",
            "challenge", "HOW MANY CAN YOU GET?", "NO CALCULATOR", duration=6,
            challenge_no=0,
        )
    ]
    for ch in challenges:
        n = ch["number"]
        plan.append(studio.scene(
            f"CHALLENGE {n}",
            f"Challenge {n}. {ch['question']}",
            "challenge", ch["question"], ch["hint"], duration=8,
            challenge_no=n, countdown=True,
        ))
        plan.append(studio.scene(
            "ANSWER",
            f"The answer is {ch['answer']}.",
            "challenge", ch["answer"], "ADD ONE POINT IF YOU GOT IT", duration=4,
            challenge_no=n, answer=True,
        ))
    plan.append(studio.scene(
        "FINAL SCORE",
        "How many did you get out of twenty? Post your score in the comments and subscribe for the next challenge set.",
        "challenge", "YOUR SCORE / 20", "NEW SET EVERY WEEK", duration=7,
        challenge_no=21,
    ))
    return plan, challenges


@studio.lru_cache(maxsize=1)
def _background():
    y, x = np.mgrid[0:1080, 0:1920]
    glow = np.exp(-(((x - 960) / 1000) ** 2 + ((y - 450) / 650) ** 2) * 2.4)
    arr = np.stack([
        12 + glow * 24,
        13 + glow * 18,
        31 + glow * 42,
    ], axis=2).astype(np.uint8)
    return Image.fromarray(arr)


def _frame(plan: list[dict], t: float, total: float):
    index = next((i for i, s in enumerate(plan) if t < s["end"]), len(plan) - 1)
    s = plan[index]
    u = t - s["start"]
    im = _background().copy()
    d = ImageDraw.Draw(im)
    accent = (255, 190, 92)

    d.rounded_rectangle((58, 46, 112, 100), radius=15, fill=accent)
    d.text((85, 73), "L", font=studio.font(34), anchor="mm", fill=(12, 16, 31))
    d.text((136, 58), "LOKI / BRAIN ARENA", font=studio.font(29), fill=(230, 235, 248))

    challenge_no = int(s.get("challenge_no", 0))
    right_label = "INTRO" if challenge_no == 0 else "RESULT" if challenge_no > 20 else f"{challenge_no:02d} / 20"
    d.text((1845, 72), right_label, font=studio.font(28), anchor="rm", fill=accent)

    studio.fit_text(d, s["headline"], (120, 175, 1800, 370), size=90, fill="white", max_lines=2)
    d.rounded_rectangle((170, 420, 1750, 760), radius=44, fill=(19, 23, 47), outline=(70, 65, 104), width=4)
    studio.fit_text(d, s.get("label", ""), (235, 455, 1685, 680), size=94,
                    fill=accent if s.get("answer") else (240, 243, 250), max_lines=3)
    studio.fit_text(d, s.get("sub", ""), (280, 688, 1640, 742), size=31,
                    fill=(171, 183, 211), max_lines=1)

    if s.get("countdown"):
        elapsed = max(0.0, u)
        remain = max(0, 7 - int(elapsed))
        d.rounded_rectangle((815, 795, 1105, 920), radius=32, fill=(35, 39, 67), outline=accent, width=3)
        d.text((960, 855), f"{remain}", font=studio.font(78), anchor="mm", fill=accent)
        d.text((960, 942), "LOCK YOUR ANSWER", font=studio.font(24), anchor="mm", fill=(177, 189, 216))
    elif s.get("answer"):
        d.rounded_rectangle((655, 805, 1265, 914), radius=30, fill=accent)
        d.text((960, 860), "ANSWER REVEALED", font=studio.font(33), anchor="mm", fill=(18, 19, 34))
    else:
        d.text((960, 854), "KEEP YOUR SCORE", font=studio.font(30), anchor="mm", fill=(177, 189, 216))

    d.line((70, 995, 1850, 995), fill=(53, 58, 87), width=4)
    d.line((70, 995, 70 + 1780 * min(1, t / total), 995), fill=accent, width=4)
    d.text((70, 1030), "ORIGINAL PROCEDURAL CHALLENGE SET", font=studio.font(20), fill=(134, 148, 177))
    d.text((1850, 1030), f"{int(t)//60}:{int(t)%60:02d} / {int(total)//60}:{int(total)%60:02d}",
           font=studio.font(21), anchor="rm", fill=(134, 148, 177))

    if index and u < .13:
        im = Image.blend(Image.new("RGB", im.size, (8, 11, 26)), im, .55 + .45 * u / .13)
    return im


def _thumbnail(path: Path, episode_id: str):
    im = _background().copy()
    d = ImageDraw.Draw(im)
    accent = (255, 190, 92)
    d.text((110, 100), "LOKI / BRAIN ARENA", font=studio.font(40), fill=(226, 234, 248))
    studio.fit_text(d, "20 BRAIN\nCHALLENGES", (100, 220, 1200, 760), size=155, fill=accent, max_lines=2)
    d.rounded_rectangle((1290, 235, 1770, 760), radius=65, fill=(23, 27, 54), outline=accent, width=5)
    d.text((1530, 430), "20", font=studio.font(200), anchor="mm", fill="white")
    d.text((1530, 620), "CAN YOU BEAT IT?", font=studio.font(34), anchor="mm", fill=accent)
    d.text((110, 930), "NO CALCULATOR • KEEP YOUR SCORE", font=studio.font(31), fill=(184, 196, 222))
    im.resize((1280, 720), Image.Resampling.LANCZOS).save(path, "JPEG", quality=92)


def render(out: Path, episode_id: str):
    out = Path(out)
    plan, challenges = _plan(episode_id)
    total = studio.voice_plan(plan, "challenge", max_duration=900)
    if total < 240:
        raise RuntimeError("Challenge compilation is too short for long-form.")
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="astra_long_challenge_") as td:
        td = Path(td)
        audio = td / "mix.wav"
        audio_info = studio.score_audio(plan, total, "challenge", audio)
        count = math.ceil(total * studio.FPS)
        cmd = [
            studio.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", str(studio.FPS),
            "-i", "pipe:0", "-i", str(audio), "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-threads", "2", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-shortest", "-movflags", "+faststart", str(out),
        ]
        with (td / "ffmpeg.log").open("wb") as log:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
            try:
                for i in range(count):
                    proc.stdin.write(_frame(plan, i / studio.FPS, total).tobytes())
                    if i and i % (studio.FPS * 30) == 0:
                        print("Challenge long-form rendered seconds:", i // studio.FPS, flush=True)
                proc.stdin.close()
                if proc.wait(timeout=120):
                    raise RuntimeError("Challenge long-form encoding failed")
            except Exception:
                proc.kill()
                proc.wait()
                raise

    thumb = out.with_suffix(".jpg")
    _thumbnail(thumb, episode_id)
    title = "20 Brain Challenges That Get Harder 🧠 Can You Score 15/20?"
    description = (
        "Twenty original brain challenges generated as a fresh weekly set. "
        "Keep your score and post it in the comments.\n\n"
        "Original animation, procedural questions, original music, and synthetic narration.\n"
        "Subscribe: https://www.youtube.com/channel/UCc9fHSuRnqq_C2C0DpLyRRg?sub_confirmation=1"
    )
    report = {
        "renderer": studio.VERSION,
        "format": "long",
        "genre": "challenge",
        "content_id": episode_id,
        "duration": round(total, 3),
        "resolution": [1920, 1080],
        "fps": studio.FPS,
        "scene_count": len(plan),
        "challenge_count": len(challenges),
        "audio": audio_info,
        "thumbnail": str(thumb),
    }
    out.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Challenge long-form complete:", json.dumps(report), flush=True)
    return title, description, report
