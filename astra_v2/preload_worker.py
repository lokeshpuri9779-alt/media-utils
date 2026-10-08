"""Render one approved original video ahead of publishing, no YouTube writes."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path

from astra_v2.control import STATE_FILE, read_json, state_for_day
from astra_v2.creative import CreativeSkip, make_candidate
from astra_v2.preload_queue import artifacts, candidate_ids, prepare


def main():
    state = state_for_day(read_json(STATE_FILE))
    queue = artifacts()
    target = max(1, min(24, int(os.getenv("ASTRA_PRELOAD_BUFFER", "6"))))
    if len(queue) >= target:
        print("ASTRA_PRELOAD="+json.dumps({"outcome":"buffer_full","count":len(queue)}))
        return
    excluded = set(state.get("published", {})) | set(state.get("reserved", {}))
    excluded.update(x.get("content_id", "") for x in state.get("pending", {}).values())
    excluded.update(candidate_ids())
    # The renderer's own creative director and independent media QA must pass.
    with tempfile.TemporaryDirectory(prefix="astra-preload-") as tmp:
        video = Path(tmp) / "render.mp4"
        try:
            candidate = make_candidate(video, excluded, set())
        except CreativeSkip as exc:
            print("ASTRA_PRELOAD="+json.dumps({"outcome":"no_approved_candidate","reason":str(exc)[:100]}))
            return
        if candidate["content_id"] in excluded:
            raise RuntimeError("Duplicate preloaded content ID")
        package = prepare(video, candidate)
        destination = Path("preload-package")
        destination.mkdir(exist_ok=True)
        for name in ("candidate.json", "video.mp4"):
            (destination / name).write_bytes((package / name).read_bytes())
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write("content_id="+candidate["content_id"]+"\n")
        print("ASTRA_PRELOAD="+json.dumps({"outcome":"ready","content_id":candidate["content_id"],
                                            "buffer_before":len(queue)}))


if __name__ == "__main__":
    main()
