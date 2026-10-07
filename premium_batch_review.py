from __future__ import annotations

import json
import sys
from pathlib import Path

from edit_spec import build_edit_spec, preflight
from premium_stories import catalog
from quality_lab import assess_render, contact_sheet, scene_change_report, write_report
from studio_renderer import render_short
from fast_premium_renderer import render_fast_premium
from renderer_router import select_validated_local


def main(root: Path) -> int:
    root.mkdir(parents=True, exist_ok=True)
    ready = [story for story in catalog() if story.get("production_ready")]
    if not ready:
        raise RuntimeError("No production-ready premium stories.")
    batch = []
    failed = False
    for story in ready:
        cid = str(story["content_id"])
        folder = root / cid
        stills = folder / "stills"
        folder.mkdir(parents=True, exist_ok=True)
        spec = build_edit_spec(story)
        gate = preflight(spec)
        write_report(folder / "edit-spec.json", spec)
        write_report(folder / "preflight.json", gate)
        entry = {"content_id": cid, "preflight": gate}
        if not gate["pass"]:
            entry["status"] = "rejected-before-render"
            failed = True
            batch.append(entry)
            continue
        video = folder / "preview.mp4"
        requirements = {
            "factual_media": bool(story.get("premium_story")),
            "motion_complexity": sum(1 for beat in (story.get("story_beats") or [])
                                     if str(beat.get("visual") or "") in {"tidal_lock","iss_orbit"}),
            "procedural_heavy": sum(1 for beat in (story.get("story_beats") or [])
                                    if str(beat.get("visual") or "") not in {"media"}) >= 2,
            "long_form": False,
        }
        selection = select_validated_local(requirements)
        renderer = str(selection.get("selected") or "studio")
        try:
            if renderer == "ffmpeg_native":
                report = render_fast_premium(video, story=story)
            else:
                # HyperFrames remains comparison-capable but Studio is the
                # deterministic in-process fallback until per-story execution
                # is wired into this batch runner.
                report = render_short(story, video, still_dir=stills)
                if renderer == "hyperframes":
                    report["selected_renderer"] = "hyperframes"
                    report["execution_renderer"] = "studio"
        except Exception as exc:
            # Preserve the proven Studio path as a zero-cost fallback while the
            # fast renderer matures. The batch report records the fallback.
            renderer = "studio-fallback"
            report = render_short(story, video, still_dir=stills)
            report["fast_renderer_error"] = str(exc)[:300]
        post = assess_render(report)
        post["pacing"] = scene_change_report(video)
        write_report(folder / "render.json", report)
        write_report(folder / "quality.json", post)
        contact_sheet(stills, folder / "contact-sheet.jpg", story.get("title") or cid)
        entry.update(status="passed" if post["pass"] else "rejected-after-render",
                     quality=post, video=str(video.name), renderer=renderer,
                     renderer_selection=selection)
        failed = failed or not post["pass"]
        batch.append(entry)
    (root / "batch.json").write_text(json.dumps(batch, indent=2), encoding="utf-8")
    print(json.dumps(batch, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else "premium-review")
    raise SystemExit(main(destination))
