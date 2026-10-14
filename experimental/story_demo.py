"""Generate a standalone four-beat story demo and manifest.

Run: python -m experimental.story_demo
"""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image,ImageDraw
from experimental.story_director import generate,plan_for,batch
from experimental.scene_composer import compose
from experimental.animated_assets import animal_frame,item_state_frame

def make_demo(output: str="story-demo",seed: int=17) -> None:
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    story=generate(seed,plot="repair",location="village")
    frames=[]
    for i,beat in enumerate(story.beats):
        scene=compose(plan_for(story,i),i*.4)
        # Show species-specific animal prototype over generic category silhouette.
        animal=animal_frame(story.actor,i*.4,112)
        scene.paste(animal,(49,379),animal)
        # Visual condition stays repaired in final beat.
        condition="damaged" if i<2 else "repaired"
        obj=item_state_frame(story.prop,"products",condition,105)
        scene.paste(obj,(194,404),obj)
        d=ImageDraw.Draw(scene)
        d.rectangle((0,0,360,35),fill=(20,31,48))
        d.text((12,12),f"{i+1}/4  {story.plot.upper()}: {beat.upper()}",fill="white")
        scene.save(dest/f"beat-{i+1}.png")
        frames.append(scene)
    sheet=Image.new("RGB",(360*4,640))
    for i,frame in enumerate(frames): sheet.paste(frame,(i*360,0))
    sheet.save(dest/"story-contact-sheet.png")
    stories=batch(24,seed)
    manifest={"demo":story.__dict__,"sample_variety":[s.__dict__ for s in stories],
              "note":"2D procedural demo; semantic plot variety is not equivalent to fully unique scripted stories"}
    (dest/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")

if __name__=="__main__": make_demo()
