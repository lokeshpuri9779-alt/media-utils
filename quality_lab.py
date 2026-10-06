from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def assess_render(report: dict) -> dict:
    failures = []
    duration = float(report.get("duration") or 0)
    scenes = report.get("scenes") or []
    cq = report.get("creative_quality") or {}
    assets = cq.get("asset_resolution") or {}
    if not (8.0 <= duration <= 28.0):
        failures.append(f"duration outside premium-short window: {duration:.2f}s")
    if len(scenes) < 3:
        failures.append("too few scenes")
    if cq.get("score", 100) < 76:
        failures.append("creative quality score below gate")
    required = int(assets.get("required_subject_media") or 0)
    verified = int(assets.get("verified_subject_media") or 0)
    if required and verified != required:
        failures.append(f"verified editorial media {verified}/{required}")
    return {"pass": not failures, "failures": failures, "duration": duration}


def contact_sheet(stills_dir: Path, output: Path, title: str = "RAYVAN review") -> None:
    paths = sorted(stills_dir.glob("*.jpg"))
    if not paths:
        return
    thumbs = []
    for path in paths:
        im = Image.open(path).convert("RGB")
        im.thumbnail((360, 640))
        thumbs.append((path.name, im.copy()))
    width = max(760, len(thumbs) * 380)
    sheet = Image.new("RGB", (width, 760), (10, 12, 18))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        font = small = None
    draw.text((24, 20), title, fill="white", font=font)
    x = 24
    for name, im in thumbs:
        y = 72
        sheet.paste(im, (x, y))
        draw.text((x, y + im.height + 10), name, fill=(220, 225, 235), font=small)
        x += 380
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def write_report(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
