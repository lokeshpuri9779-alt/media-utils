"""Contact sheet of supported Studio frames and explicit blocked cross-genre scenes.

This tool is a NON-PUBLISHING preview. An unsupported scene is labelled as
BLOCKED, never silently substituted with an unrelated icon or fake render.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
from astra_errors import CreativeReject
from astra_v2.crossgenre_directed_24 import PLOTS
from astra_v2.story_forge import catalog
from studio_renderer import make_plan, render_frame, RATE


def _blocked_tile(reason: str) -> Image.Image:
    tile = Image.new("RGB", (160, 285), (60, 19, 26))
    draw = ImageDraw.Draw(tile)
    draw.rectangle((5, 5, 154, 280), outline=(236, 128, 108), width=3)
    draw.text((17, 18), "NOT RENDERED", fill=(255, 227, 210))
    draw.text((17, 40), "ART REQUIRED", fill=(255, 196, 160))
    words = reason.replace("_", " ").split()
    for index in range(0, min(21, len(words)), 3):
        draw.text((12, 83 + 17 * (index // 3)),
                  " ".join(words[index:index + 3])[:23],
                  fill=(255, 204, 204))
    return tile


def main():
    output = Path("preview/astra-crossgenre-directed24.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    authored = {x["title"]: x for x in catalog(limit=400)}
    sheet = Image.new("RGB", (160 * 8, 285 * 6), (18, 24, 37))
    manifest = []
    for idx, (_, title, genre, _) in enumerate(PLOTS):
        story = authored[title]
        plan = make_plan(story)
        if len(plan) != 4:
            raise RuntimeError("Missing story scenes: " + title)
        for n, beat in enumerate((plan[0], plan[3])):
            shot = dict(beat)
            shot.update(start=0.0, end=2.0, duration=2.0,
                        voice_start=.06, audio=np.zeros(RATE, dtype=np.float32),
                        director_camera="still")
            status, reason = "rendered", None
            try:
                img = render_frame([shot], .55, "fiction", 2.0)
                tile = img.resize((160, 285), Image.Resampling.BILINEAR)
            except CreativeReject as exc:
                # A known Studio capability rejection does NOT become a
                # production-ready frame. Preserve the reason for art review.
                status, reason = "blocked", str(exc)[:240]
                tile = _blocked_tile(reason)
            pos = idx * 2 + n
            sheet.paste(tile, ((pos % 8) * 160, (pos // 8) * 285))
            manifest.append({"title": title, "genre": genre, "scene": n,
                             "story_subject": shot.get("story_subject"),
                             "visual": shot.get("visual"),
                             "status": status, "reason": reason,
                             "publication_eligible": False})
    sheet.save(output)
    rendered = sum(x["status"] == "rendered" for x in manifest)
    blocked = len(manifest) - rendered
    payload = {"stories": len(PLOTS), "genre_count": len({x[2] for x in PLOTS}),
               "total_slots": len(manifest), "rendered_frames": rendered,
               "blocked_frames": blocked, "voice": "not_in_contact_sheet",
               "publication": False, "scenes": manifest}
    (output.parent / "astra-crossgenre-directed24.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    print("ASTRA_CROSSGENRE_CONTACT_REPORT=" +
          json.dumps({"rendered": rendered, "blocked": blocked,
                      "total": len(manifest)}), flush=True)
    if not rendered:
        raise RuntimeError("No supported cross-genre scenes were rendered")
    if len(manifest) != 48:
        raise RuntimeError("Missing cross-genre QA slots")
    print("ASTRA_CROSSGENRE_CONTACT_REPORT_WRITTEN", output.stat().st_size)


if __name__ == "__main__":
    main()
