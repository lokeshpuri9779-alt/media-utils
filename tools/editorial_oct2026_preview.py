"""Offline visual contact-sheet QA. Never uploads or approves a story."""
from pathlib import Path
import json
from PIL import Image
from astra_v2.editorial_batch_oct2026 import PLOTS
from astra_v2.pillow_duo_scene import draw_duo, scene_pair
from astra_v2.story_action_motion import choose_action

def run():
    output=Path("preview/editorial-oct2026-scenes.png")
    output.parent.mkdir(parents=True,exist_ok=True)
    cells=[]
    distinct=set()
    for key,title,genre,beats in PLOTS:
        cast=scene_pair({"speech":title})
        for i,(headline,speech,visual,label) in enumerate(beats):
            shot={"speech":speech,"headline":headline,"visual":visual,
                  "story_action":choose_action({"speech":speech}),
                  "story_cast":cast,"story_visual_seed":key,
                  "story_beat":("reveal","build","twist","payoff")[i]}
            frame=Image.new("RGB",(1080,1920),(24,35,60))
            if not draw_duo(frame,shot,.7):
                raise RuntimeError("Missing pair in "+title)
            tile=frame.resize((162,288),Image.Resampling.BILINEAR)
            cells.append(tile)
            distinct.add(tile.tobytes())
    if len(cells)!=80 or len(distinct)<60:
        raise RuntimeError("Insufficient frame diversity")
    sheet=Image.new("RGB",(1620,2304),(24,35,60))
    for i,tile in enumerate(cells):
        sheet.paste(tile,((i%10)*162,(i//10)*288))
    sheet.save(output)
    report={"stories":len(PLOTS),"scenes":len(cells),
            "visually_distinct_scene_samples":len(distinct),
            "production_approved":False,"youtube_upload":False}
    Path("preview/editorial-oct2026-qa.json").write_text(
        json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report))

if __name__=="__main__":
    run()
