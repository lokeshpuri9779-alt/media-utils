"""Generate scene-aligned SRT captions from the episode master timeline."""
from __future__ import annotations
import argparse,json
from pathlib import Path

def timestamp(seconds):
    millis=round(seconds*1000)
    h,millis=divmod(millis,3600000)
    m,millis=divmod(millis,60000)
    s,ms=divmod(millis,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def captions(timeline):
    lines=[]
    for index,scene in enumerate(timeline["scenes"],1):
        start=scene["start_frame"]/timeline["fps"]
        end=scene["end_frame"]/timeline["fps"]
        if end<=start:raise ValueError("Invalid caption interval")
        text=scene["caption"].strip()
        if not text:raise ValueError("Empty caption")
        lines.append(f"{index}\n{timestamp(start)} --> {timestamp(end)}\n{text}\n")
    return "\n".join(lines)+"\n"

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("timeline")
    parser.add_argument("--output",default="episode.srt")
    args=parser.parse_args()
    data=json.loads(Path(args.timeline).read_text())
    Path(args.output).write_text(captions(data))
if __name__=="__main__":main()
