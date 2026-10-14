"""Create synchronized offline SRT captions from authored story beats."""
from pathlib import Path


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def write_srt(plan, destination, seconds_per_scene=2):
    if plan.get("publication_allowed") is not False:
        raise ValueError("offline non-publishing story required")
    if not 1 <= seconds_per_scene <= 10:
        raise ValueError("invalid scene duration")
    cues = []
    for index, scene in enumerate(plan["scenes"]):
        caption = str(scene.get("caption", "")).strip()
        if not caption or "\n" in caption or "\r" in caption:
            raise ValueError(f"missing or malformed caption in scene {index}")
        start = index * seconds_per_scene
        end = (index + 1) * seconds_per_scene
        cues.append(f"{index + 1}\n{timestamp(start)} --> {timestamp(end)}\n{caption}\n")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(cues), encoding="utf-8")
    return destination
