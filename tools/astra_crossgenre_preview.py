"""48-frame Studio-composited contact sheet across 12 different story genres."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from astra_v2.crossgenre_directed_24 import PLOTS
from astra_v2.story_forge import catalog
from studio_renderer import make_plan, render_frame, RATE

def main():
    output=Path("preview/astra-crossgenre-directed24.png")
    output.parent.mkdir(parents=True,exist_ok=True)
    authored={x["title"]:x for x in catalog(limit=400)}
    sheet=Image.new("RGB",(160*8,285*6),(18,24,37))
    manifest=[]
    for idx,(_,title,genre,_) in enumerate(PLOTS):
        story=authored[title]
        plan=make_plan(story)
        if len(plan)!=4: raise RuntimeError("Missing story scenes: "+title)
        for n,beat in enumerate((plan[0],plan[3])):
            shot=dict(beat)
            shot.update(start=0.0,end=2.0,duration=2.0,voice_start=.06,
                audio=np.zeros(RATE,dtype=np.float32),director_camera="still")
            img=render_frame([shot],.55,"fiction",2.0)
            tile=img.resize((160,285),Image.Resampling.BILINEAR)
            pos=idx*2+n
            sheet.paste(tile,((pos%8)*160,(pos//8)*285))
            manifest.append({"title":title,"genre":genre,"scene":n,
                            "story_subject":shot.get("story_subject"),
                            "visual":shot.get("visual")})
    sheet.save(output)
    (output.parent/"astra-crossgenre-directed24.json").write_text(
        json.dumps({"stories":24,"genre_count":12,
                    "frames":len(manifest),"voice":"not_in_contact_sheet",
                    "publication":False,"scenes":manifest},indent=2),
        encoding="utf-8")
    print("ASTRA_CROSSGENRE_CONTACT_PASS",output.stat().st_size)

if __name__=="__main__":
    main()
