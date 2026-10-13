"""Deterministic, offline parallel asset audit. No credentials, publishing or paid APIs."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops
from astra_v2.character_object_catalog import (
    CHARACTER_COUNT, OBJECT_COUNT, character, prop, draw_character, draw_prop
)

def audit(kind, start, stop, output):
    total = CHARACTER_COUNT if kind == "character" else OBJECT_COUNT
    if not 0 <= start < stop <= total:
        raise ValueError("Invalid catalog range")
    output.mkdir(parents=True, exist_ok=True)
    fingerprints = set()
    blank = []
    static = []
    errors = []
    examples = []
    for index in range(start, stop):
        try:
            images = []
            for t in (0.0, 1.15):
                im = Image.new("RGB", (420, 580), (20, 29, 43))
                if kind == "character":
                    draw_character(im, index, t, 210, 245)
                else:
                    draw_prop(im, index, t, 210, 245)
                images.append(im)
            a, z = images
            if ImageChops.difference(a, Image.new("RGB", a.size, (20, 29, 43))).getbbox() is None:
                blank.append(index)
            if ImageChops.difference(a, z).getbbox() is None:
                static.append(index)
            small = a.resize((84, 116))
            fingerprints.add(hashlib.sha256(small.tobytes()).hexdigest())
            if (index - start) % max(1, (stop - start) // 12) == 0:
                examples.append((index, a.resize((210, 290))))
        except Exception as exc:
            errors.append({"index": index, "error": str(exc)})
    columns = 4
    rows = (len(examples) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 210, rows * 290), (20, 29, 43))
    for j, (_, sample) in enumerate(examples):
        sheet.paste(sample, ((j % columns) * 210, (j // columns) * 290))
    sheet.save(output / (kind + "-contact-sheet.png"))
    report = {
        "kind": kind, "start": start, "stop": stop, "tested": stop - start,
        "unique_frame_fingerprints": len(fingerprints),
        "unique_fraction": round(len(fingerprints) / (stop - start), 4),
        "blank_indices": blank, "static_indices": static, "errors": errors,
        "quality_approved": False,
        "note": "Technical rendering audit only. Fingerprints do not establish artistic uniqueness."
    }
    (output / (kind + "-audit.json")).write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ("blank_indices", "static_indices", "errors")}, indent=2))
    if errors or blank or static:
        raise SystemExit("Technical audit failed: inspect JSON report")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=("character", "object"), required=True)
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--stop", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    audit(args.kind, args.start, args.stop, args.output)
