from pathlib import Path

import cloud_once

VIDEO=Path("/tmp/agnes-pilot/astra-agnes-character-pilot.mp4")
TITLE="The Lion Cub and the Giant Mango #Shorts"
CONTENT_ID="lion-cub-mango-mishap-v1"
DESCRIPTION=(
    "A tiny lion cub chooses the biggest mango in the grove—and immediately regrets it. "
    "An original RAYVAN animated micro-story.\n\n"
    "AI-assisted animation and synthetic narration.\n"
    "ASTRA-ID:"+CONTENT_ID+"\n"
    "#Shorts #Animation #RAYVAN"
)

if not VIDEO.is_file() or VIDEO.stat().st_size <= 0:
    raise SystemExit("Finished Agnes pilot artifact is missing.")

token=cloud_once.access_token()
cloud_once.verify_channel(token)

if cloud_once.live_channel_duplicate(token,TITLE,CONTENT_ID):
    raise SystemExit("Pilot already exists on the authorized channel; refusing duplicate upload.")

cloud_once.CONTENT_META.update({
    "content_id": CONTENT_ID,
    "genre": "fiction",
    "format": "short",
    "renderer": "agnes-free-video",
    "ai_disclosure_required": True,
    "character_story": True,
})

status,url=cloud_once.upload(VIDEO,TITLE,DESCRIPTION,token=token)
print("UPLOAD_STATUS="+status)
print("UPLOAD_URL="+url)
if status!="success":
    raise SystemExit("Private YouTube upload did not succeed.")
