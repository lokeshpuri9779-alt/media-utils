"""Validate subtitle time ranges before burning them into ASTRA video."""
from __future__ import annotations
import re
from pathlib import Path

TIMESTAMP = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$")

def seconds(value: str) -> float:
    match = TIMESTAMP.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Invalid SRT timestamp: {value}")
    hours, minutes, secs, millis = map(int, match.groups())
    if minutes >= 60 or secs >= 60:
        raise ValueError(f"Invalid SRT time: {value}")
    return hours * 3600 + minutes * 60 + secs + millis / 1000

def validate_srt(path: Path, duration: float | None = None) -> dict:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError("SRT is empty")
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    previous_end = 0.0
    for index, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if len(lines) < 3 or lines[0].strip() != str(index):
            raise ValueError(f"Subtitle block {index} must have sequential index and text")
        if " --> " not in lines[1]:
            raise ValueError(f"Subtitle block {index} missing timing")
        start_text, end_text = lines[1].split(" --> ", 1)
        start, end = seconds(start_text), seconds(end_text)
        if start < previous_end or end <= start:
            raise ValueError(f"Subtitle block {index} overlaps or has invalid duration")
        if duration is not None and end > duration + 0.1:
            raise ValueError(f"Subtitle block {index} extends past video")
        if not any(line.strip() for line in lines[2:]):
            raise ValueError(f"Subtitle block {index} has no text")
        previous_end = end
    return {"cues": len(blocks), "last_end_seconds": previous_end}

