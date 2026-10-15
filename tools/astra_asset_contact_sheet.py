"""Small inspectable contact sheets of real procedural icons and on-screen actors."""
from pathlib import Path
from PIL import Image, ImageDraw
from astra_v2.procedural_visual_library import draw_icon, MOTIFS
from astra_v2.pillow_duo_scene import draw_duo

def create_sheets(folder="preview"):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    icon_sheet=Image.new("RGB",(1600,760),(32,45,63))
    art=ImageDraw.Draw(icon_sheet)
    for j,motif in enumerate(MOTIFS):
        for palette in range(2):
            col=j%10
            row=(j//10)*2+palette
            x=col*160+80
            y=row*183+76
            idx=j*100+palette*10+palette*3
            draw_icon(art,idx,x,y,106)
            art.text((x-54,y+65),motif[:17],fill=(239,234,217))
    icon_sheet.save(folder/"icon-motif-gallery.png",optimize=True)

    sheet=Image.new("RGB",(1080,480),(24,35,60))
    for i,seed in enumerate(("pilot-forest","pilot-harbor","pilot-mountain","pilot-garden")):
        frame=Image.new("RGB",(1080,1920),(24,35,60))
        shot={"speech":"The fox and rabbit carry a gift box.",
              "story_cast":("fox","rabbit"),"story_action":"carry",
              "story_visual_seed":seed}
        assert draw_duo(frame,shot,1.3)
        small=frame.resize((270,480),Image.Resampling.BILINEAR)
        sheet.paste(small,(i*270,0))
    sheet.save(folder/"character-wardrobe-gallery.png",optimize=True)
    print("ASTRA_CONTACT_SHEETS="+str(folder))
if __name__=="__main__":
    create_sheets()
