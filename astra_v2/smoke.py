"""Render a real original premium Short without touching YouTube or OAuth."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from premium_stories import catalog as previous_catalog
from astra_v2.original_stories import catalog as original_catalog
from studio_renderer import render_short
from quality_lab import evaluate_studio_render
from astra_v2.creative import inspect_video

def main():
    print("ASTRA V2 offline smoke: real render, no YouTube credentials or upload")
    failures=[]
    with tempfile.TemporaryDirectory(prefix="astra-v2-smoke-") as tmp:
        target=Path(tmp)/"preview.mp4"
        for story in original_catalog() + previous_catalog():
            if not story.get("production_ready"):
                continue
            identity=story["content_id"]
            try:
                result=render_short(story,target)
                judgement=evaluate_studio_render(story,result,video_path=target)
                record={"id":identity,"quality_pass":bool(judgement.get("pass")),
                        "director":judgement.get("director",{}),
                        "media":inspect_video(target)}
                if not record["quality_pass"]:
                    failures.append({"id":identity,"error":"creative_gate", "score":record["director"].get("score")})
                    continue
                if failures:
                    print("V2_SMOKE_PRIOR_REJECTIONS="+json.dumps(failures,default=str))
                print("V2_SMOKE_PASS="+json.dumps(record,default=str))
                return
            except Exception as exc:
                failures.append({"id":identity,"error":type(exc).__name__, "message":str(exc)[:240]})
        print("V2_SMOKE_FAILURE="+json.dumps(failures))
        raise RuntimeError("No curated premium Short passed final offline video + creative QA.")

if __name__=="__main__":
    main()
