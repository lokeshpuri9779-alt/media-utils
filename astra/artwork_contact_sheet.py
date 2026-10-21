"""Build a labelled contact sheet from a generated artwork preview manifest.

Preview only: this does not approve artwork or modify the live asset library.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def make_contact_sheet(manifest_path, output_path, *, columns=4, thumb_size=(216, 384)):
    path = Path(manifest_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("assets")
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty_preview_manifest")
    if not 1 <= columns <= 8:
        raise ValueError("invalid_columns")
    w, h = thumb_size
    gap, label_height = 16, 38
    count_rows = (len(rows) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * (w + gap) + gap,
                              count_rows * (h + label_height + gap) + gap), (20, 26, 39))
    draw = ImageDraw.Draw(sheet)
    root = path.parent.parent.resolve()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("status") != "pending_review":
            raise ValueError("preview_contains_nonpending_asset")
        rel = row.get("path")
        if not isinstance(rel, str):
            raise ValueError("invalid_preview_path")
        image_path = (root / rel).resolve()
        if root not in image_path.parents or not image_path.is_file():
            raise ValueError("preview_path_outside_root_or_missing")
        x = gap + (index % columns) * (w + gap)
        y = gap + (index // columns) * (h + label_height + gap)
        with Image.open(image_path) as opened:
            if opened.width < 540 or opened.height < 960:
                raise ValueError("preview_image_too_small")
            image = ImageOps.fit(opened.convert("RGB"), (w, h), method=Image.Resampling.LANCZOS)
        sheet.paste(image, (x, y))
        label = str(row.get("id") or "")[:28]
        draw.text((x + 4, y + h + 9), label, fill=(235, 239, 245), font=ImageFont.load_default())
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(make_contact_sheet(args.manifest, args.output))


if __name__ == "__main__":
    main()
