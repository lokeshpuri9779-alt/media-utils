from pathlib import Path
import os
import json

import cloud_once
from character_pilot import render
from character_stories import pilot_story

OUT=Path("/tmp/astra-next-character-short.mp4")
story=pilot_story()

result=render(OUT)
REPORT=OUT.with_suffix(".json")
REPORT.write_text(json.dumps(result, indent=2), encoding="utf-8")
composition=result["composition"]
actual=float(composition["duration"])
target_min=float(story.get("target_duration_min",20))
target_max=float(story.get("target_duration_max",40))
if not (target_min <= actual <= target_max):
    raise SystemExit(f"Duration gate failed: {actual}s not in {target_min}-{target_max}s")

revision=(os.environ.get("ASTRA_UPLOAD_REVISION") or "").strip()
title=str(story["title"]).strip()+(f" — {revision}" if revision else "")+" #Shorts"
content_id=str(story["content_id"])+(f"-{revision.lower().replace(' ','-')}" if revision else "")
description=(
    str(story.get("question") or "").strip()+"\n\n"
    "An original RAYVAN animated micro-story.\n"
    "AI-assisted animation and synthetic narration.\n"
    f"ASTRA-ID:{content_id}\n"
    "#Shorts #Animation #RAYVAN"
)

token=cloud_once.access_token()
cloud_once.verify_channel(token)
if cloud_once.live_channel_duplicate(token,title,content_id):
    raise SystemExit("This story already exists on the authorized channel; refusing duplicate upload.")

cloud_once.CONTENT_META.update({
    "content_id":content_id,
    "genre":story.get("genre","fiction"),
    "format":"short",
    "renderer":"agnes-free-video",
    "ai_disclosure_required":True,
    "character_story":True,
    "duration":actual,
    "scene_count":composition.get("scene_count"),
})

status,url=cloud_once.upload(OUT,title,description,token=token)
result["upload"]={"status": status, "url": url, "content_id": content_id}
REPORT.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("STORY_ID="+content_id)
print("DURATION="+str(actual))
print("SCENES="+str(composition.get("scene_count")))
print("UPLOAD_STATUS="+status)
print("UPLOAD_URL="+url)
if status!="success":
    raise SystemExit("Private character-story upload did not succeed.")
