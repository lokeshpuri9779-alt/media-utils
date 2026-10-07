from __future__ import annotations

import json
import sys
from pathlib import Path

from edit_spec import build_edit_spec, preflight
from premium_stories import catalog
from quality_lab import assess_render, scene_change_report, write_report
from fast_premium_renderer import render_fast_premium
from shorts_package import build_shorts_package, as_dict


def validate_candidate(story: dict, root: Path) -> dict:
    cid=str(story["content_id"])
    folder=root/cid
    folder.mkdir(parents=True,exist_ok=True)

    spec=build_edit_spec(story)
    pre=preflight(spec)
    write_report(folder/"edit-spec.json",spec)
    write_report(folder/"preflight.json",pre)
    result={"content_id":cid,"preflight":pre,"production_ready":bool(story.get("production_ready"))}
    if not pre["pass"]:
        result["status"]="rejected-before-render"
        return result

    video=folder/"preview.mp4"
    try:
        report=render_fast_premium(video,story=story)
    except Exception as exc:
        result["status"]="render-failed"
        result["error"]=str(exc)[:500]
        return result

    quality=assess_render(report)
    quality["pacing"]=scene_change_report(video)
    write_report(folder/"render.json",report)
    write_report(folder/"quality.json",quality)
    package=as_dict(build_shorts_package(story,report))
    write_report(folder/"shorts-package.json",package)
    result.update(status="passed" if quality["pass"] else "rejected-after-render",
                  quality=quality,video=video.name,shorts_package=package)
    return result


def main(root: Path) -> int:
    root.mkdir(parents=True,exist_ok=True)
    candidates=[s for s in catalog() if s.get("validation_candidate")]
    results=[validate_candidate(s,root) for s in candidates]
    (root/"candidate-batch.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    print(json.dumps(results,indent=2))
    return 0 if results and all(r.get("status")=="passed" for r in results) else 1


if __name__=="__main__":
    raise SystemExit(main(Path(sys.argv[1] if len(sys.argv)>1 else "candidate-review")))
