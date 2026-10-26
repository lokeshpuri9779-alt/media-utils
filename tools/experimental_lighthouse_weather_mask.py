"""Cheap, deterministic weather variation baseline; reference-specific masks only.

This benchmark protects the red lighthouse and rock formations in the known
512x768 sunset anchor. It does not claim general object segmentation.
Never publishes or approves assets.
"""
import json
import math
import os
import random
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageStat

ANCHOR = Path("artifacts/anchor-input/01_sunset.png")
OUT = Path("artifacts/experimental-openvino/weather-masking")
WIDTH, HEIGHT = 512, 768

def protected_mask():
    mask = Image.new("L", (WIDTH, HEIGHT), 0)
    d = ImageDraw.Draw(mask)
    # Hand-authored geometry for this ONE verified anchor; no general segmenter.
    d.polygon([(245,470),(264,483),(276,502),(275,539),(287,551),
               (297,671),(317,704),(185,704),(195,665),(198,559),
               (212,542),(225,541),(227,503)], fill=255)
    # Identifiable rocky island behind the structure and foreground rocks.
    d.polygon([(97,602),(121,588),(165,581),(198,590),(203,612),
               (298,607),(293,589),(318,576),(352,583),(409,611),
               (420,636),(96,635)], fill=255)
    d.polygon([(187,675),(228,662),(283,670),(334,674),(384,682),
               (428,705),(400,729),(193,725)], fill=255)
    return mask

def paint_weather(anchor, mode):
    raw = np.asarray(anchor.convert("RGB"), dtype=np.float32)
    y = np.arange(HEIGHT, dtype=np.float32)[:, None, None]
    if mode == "storm":
        # Darken and cool the original sea and clouds without changing layout.
        tint = np.array([43, 68, 96], dtype=np.float32)
        mix = np.where(y < 594, 0.52, 0.33)
        array = raw * (1.0 - mix) + tint * mix
        array = array * np.where(y < 594, 0.72, 0.87)
    else:
        # Lift sunset away from orange toward daylight; soften cloud contrast.
        sky = np.array([126, 185, 226], dtype=np.float32)
        ocean = np.array([74, 151, 200], dtype=np.float32)
        target = np.where(y < 594, sky, ocean)
        mix = np.where(y < 594, 0.76, 0.36)
        array = raw * (1.0 - mix) + target * mix
        array = array * np.where(y < 594, 1.12, 1.03)
    backdrop = Image.fromarray(np.uint8(np.clip(array, 0, 255)), "RGB")
    if mode == "storm":
        # Sparse diagonal rain, deterministic and drawn UNDER original subject.
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
        d = ImageDraw.Draw(overlay)
        rng = random.Random(4107)
        for _ in range(350):
            x = rng.randint(0, WIDTH-1)
            yy = rng.randint(20, HEIGHT-1)
            length = rng.randint(9, 21)
            d.line((x, yy, x-5, yy+length),
                   fill=(187, 211, 230, rng.randint(48, 115)), width=1)
        backdrop = Image.alpha_composite(backdrop.convert("RGBA"), overlay).convert("RGB")
    hard = protected_mask()
    soft = hard.filter(ImageFilter.GaussianBlur(3))
    result = Image.composite(anchor, backdrop, soft)
    # Exact-pixel preservation for safe inner portions of tower and rocks.
    core = hard.filter(ImageFilter.MinFilter(13))
    result.paste(anchor, mask=core)
    return result, core

def mean_diff(a, b):
    return round(sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3, 2)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"engine": "PIL/NumPy deterministic weather masking",
              "anchor_run": 40371027354, "published": False,
              "approved": False, "production_ready": False,
              "general_object_segmentation": False,
              "subject_geometry": "hand_authored_for_one_anchor",
              "storytelling_quality": "manual_review_required", "scenes": []}
    start = time.monotonic()
    try:
        anchor = Image.open(ANCHOR).convert("RGB")
        if anchor.size != (WIDTH, HEIGHT):
            raise ValueError("Expected 512x768 reference anchor")
        anchor.save(OUT / "01_anchor_sunset.png")
        frames = [anchor]
        outputs = {}
        for slug, mode in (("02_storm", "storm"), ("03_after", "after")):
            img, core = paint_weather(anchor, mode)
            path = OUT / (slug + ".png")
            img.save(path)
            from astra_v2.omniroute_image_assets import image_quality_report
            q = image_quality_report(path.read_bytes(), "scene")
            protected_diff = ImageChops.difference(img, anchor)
            # Every core pixel should be unchanged from the actual reference.
            core_diff = ImageStat.Stat(Image.composite(protected_diff,
                                   Image.new("RGB", anchor.size), core)).extrema
            preserved = all(mx == 0 for _, mx in core_diff)
            scene = {"id":slug, "pixel_quality":q, "protected_core_exact": preserved,
                     "mean_absolute_change_from_anchor":mean_diff(anchor,img),
                     "path":str(path)}
            report["scenes"].append(scene)
            outputs[slug] = img
            frames.append(img)
            print("ASTRA_MASK_SCENE: " + json.dumps(scene), flush=True)
        report["storm_after_mean_absolute_difference"] = mean_diff(
            outputs["02_storm"], outputs["03_after"])
        report["technical_pass"] = (
            all(s["pixel_quality"]["passed"] and s["protected_core_exact"]
                for s in report["scenes"])
            and report["storm_after_mean_absolute_difference"] >= 18.0)
        sheet = Image.new("RGB",(WIDTH*3, HEIGHT+48),"white")
        draw = ImageDraw.Draw(sheet)
        for i, frame in enumerate(frames):
            sheet.paste(frame, (i*WIDTH,48))
            draw.text((i*WIDTH+12,14),
                ("Anchor: sunset", "Storm: blue-gray rain", "After: blue daylight")[i],
                fill="black")
        sheet.save(OUT / "contact_sheet.png")
    except Exception as exc:
        report["failed_stage"] = "weather_generation"
        report["error_type"] = type(exc).__name__
        report["technical_pass"] = False
    report["elapsed_seconds"] = round(time.monotonic()-start,2)
    (OUT / "report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("ASTRA_MASK_REPORT: " + json.dumps(report), flush=True)
    if not report["technical_pass"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
