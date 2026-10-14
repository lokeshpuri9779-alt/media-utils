"""Create upload-ready metadata without enabling or attempting publication."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path

def create_metadata(timeline, title="The Puppy and the Lost Kite"):
    scenes=timeline.get("scenes",[])
    if not scenes or not all(s.get("narration","").strip() for s in scenes):
        raise ValueError("Every scene needs narration")
    duration=timeline.get("duration_seconds",0)
    if not (0<duration<=180):raise ValueError("Invalid Shorts duration")
    clean_title=re.sub(r"\s+"," ",title).strip()
    if not clean_title or len(clean_title)>100:raise ValueError("Title must be 1-100 characters")
    story=" ".join(s["narration"].strip() for s in scenes)
    return {
        "title":clean_title,
        "description":f"{story}\n\n#Shorts #Animation #PuppyAdventure",
        "tags":["shorts","animation","puppy adventure","animated story"],
        "language":"en-US",
        "privacyStatus":"private",
        "madeForKids":None,
        "requiresAudienceClassification":True,
        "requiresHumanApproval":True,
        "autoPublish":False,
        "episodeDurationSeconds":duration
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("timeline");p.add_argument("--title",default="The Puppy and the Lost Kite")
    p.add_argument("--output",default="youtube_metadata.json")
    a=p.parse_args()
    metadata=create_metadata(json.loads(Path(a.timeline).read_text()),a.title)
    Path(a.output).write_text(json.dumps(metadata,indent=2)+"\n")
    print(a.output)
