"""Produce actual visual evidence for collision-free original story renders.

No YouTube credentials or upload. This test renders 1080x1920 frames and
a preview MP4, runs measured Studio QA, and publishes a 4-frame contact sheet.
"""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image, ImageDraw

from astra_v2.original_stories import catalog
from astra_v2.creative import inspect_video
from studio_renderer import render_short
from quality_lab import evaluate_studio_render


def main():
    root=Path("layout-review")
    stills=root/"stills"
    root.mkdir(parents=True,exist_ok=True)
    story=catalog()[0]
    video=root/"collision-free-lightkeeper.mp4"
    report=render_short(story,video,still_dir=stills)
    qa=evaluate_studio_render(story,report,video_path=video)
    layers=report.get("layer_qa") or {}
    if not layers.get("pass"):
        raise RuntimeError("Animation-layer collision QA did not pass: "+str(layers.get("failures")))
    if not qa.get("pass") or not (qa.get("director") or {}).get("publish_allowed"):
        raise RuntimeError("Director did not approve corrected rendered video.")
    if any(row.get("competing_foreground_count")!=1 for row in layers["scenes"]):
        raise RuntimeError("Competing foreground animation detected.")
    media=inspect_video(video)
    images=sorted(stills.glob("scene_*.jpg"),key=lambda p:int(p.stem.split("_")[-1]))
    if len(images)!=len(report.get("scenes") or []):
        raise RuntimeError("Scene inspection stills incomplete.")
    thumb_width,thumb_height=270,480
    board=Image.new("RGB",(thumb_width*len(images),thumb_height+72),(8,12,23))
    dr=ImageDraw.Draw(board)
    for i,path in enumerate(images):
        with Image.open(path) as source:
            picture=source.convert("RGB").resize((thumb_width,thumb_height),Image.Resampling.LANCZOS)
            board.paste(picture,(thumb_width*i,72))
            dr.text((thumb_width*i+14,24),"SCENE "+str(i+1),fill="white")
    board.save(root/"story-contact-sheet.jpg",quality=92)
    result={
        "story_id":story["content_id"],"title":story["title"],
        "video":str(video),"contact_sheet":str(root/"story-contact-sheet.jpg"),
        "layer_qa":layers,"director_score":(qa.get("director") or {}).get("score"),
        "approved":bool(qa["pass"]),"media":media,
    }
    (root/"result.json").write_text(json.dumps(result,indent=2,default=str),encoding="utf-8")
    print("ASTRA_LAYOUT_SMOKE_PASS="+json.dumps({
        "story_id":result["story_id"],"approved":result["approved"],
        "director_score":result["director_score"],
        "foregrounds":[r["foreground"] for r in layers["scenes"]],
        "video_duration":media["seconds"],"collision_count":len(layers["failures"]),
    }))


if __name__=="__main__":
    main()
