"""Opt-in backdrop composition for ASTRA Studio's existing Pillow renderer.

Preserves full-frame size and leaves captions/foreground actor compositing intact.
Uses original SVG library's scene/palette identities, drawn natively by Pillow
so no new runtime rasterization dependency is required.
"""
from __future__ import annotations
import hashlib
import re
from PIL import Image, ImageDraw
from astra_v2.visual_artifact_library import SCENES, PALETTES

SCENE_TERMS = {
    "observatory": ("observatory", "telescope"),
    "forest": ("forest", "woods"),
    "harbor": ("harbor", "dock", "port"),
    "library": ("library", "bookshelf"),
    "railway": ("railway", "train", "station"),
    "village": ("village",),
    "mountain": ("mountain", "summit"),
    "desert": ("desert", "dune"),
    "underwater": ("underwater", "ocean", "coral"),
    "space": ("space", "orbital", "planet"),
    "laboratory": ("laboratory", "lab"),
    "garden": ("garden", "greenhouse"),
    "lighthouse": ("lighthouse",),
    "cave": ("cave", "cavern"),
    "city": ("city", "street"),
    "workshop": ("workshop", "mechanic"),
    "castle": ("castle",),
    "snowfield": ("snowfield", "snow", "ice"),
    "island": ("island",),
    "museum": ("museum",),
}

def choose_scene(shot):
    # Authored setting wins over incidental location words in narration.
    for key in ("story_environment", "visual_prompt", "speech", "headline"):
        text = str(shot.get(key) or "").lower()
        for scene in SCENES:
            if any(re.search(r"\b"+re.escape(term)+r"\b",text) for term in SCENE_TERMS[scene]):
                return scene
    return None

def apply_backdrop(image, shot, identity):
    if image.mode != "RGB" or image.size != (1080,1920):
        raise ValueError("ASTRA artifact backdrop requires RGB 1080x1920")
    scene=choose_scene(shot)
    if scene is None:
        return image
    seed=int.from_bytes(hashlib.sha256((str(identity) + "|" + scene).encode()).digest()[:4],"big")
    palette=PALETTES[seed%len(PALETTES)]
    bg,accent,light,star=palette
    # Upper half environmental silhouette; actors and captions remain rendered
    # later by the existing Studio pipeline.
    overlay=Image.new("RGBA",image.size,(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    if scene in {"city","village","castle","library","museum","workshop","laboratory"}:
        for i in range(7):
            x=i*165-25
            h=200+(seed//(i+1))%230
            d.rectangle((x,940-h,x+130,940),fill=accent+"99")
            for yy in range(940-h+35,925,65):
                d.rectangle((x+30,yy,x+55,yy+22),fill=light+"88")
    elif scene in {"forest","garden","island","snowfield","mountain","desert"}:
        for i in range(7):
            x=i*190-80
            peak=380+(seed//(i+1))%260
            d.polygon(((x,950),(x+100,950-peak),(x+220,950)),fill=accent+"99")
    elif scene in {"observatory","lighthouse","railway","harbor","space"}:
        d.ellipse((240,380,840,980),outline=light+"99",width=22)
        d.polygon(((280,940),(360,530),(720,530),(800,940)),fill=accent+"88")
    else:
        for i in range(11):
            x=(seed+i*193)%1080
            y=300+(seed//(i+1))%600
            r=15+(i*11)%70
            d.ellipse((x-r,y-r,x+r,y+r),outline=light+"99",width=7)
    # Readable scene-specific motifs replace artificial identity barcodes.
    # The backdrop is still opt-in and remains behind foreground actors.
    if scene == "observatory":
        d.ellipse((390,370,690,670), fill=accent+"dd", outline=light, width=12)
        d.rectangle((510,650,570,950), fill=light+"bb")
        d.line((550,500,790,310), fill=light, width=32)
    elif scene == "forest":
        for x in (130,450,810):
            d.rectangle((x,590,x+40,950), fill=accent)
            d.ellipse((x-95,390,x+135,690), fill=light+"77")
    elif scene == "harbor":
        d.polygon(((280,860),(550,860),(480,920),(340,920)), fill=light+"bb")
        d.line((405,850,405,470),fill=light,width=12)
        d.polygon(((415,490),(415,810),(630,810)),fill=accent)
    elif scene == "library":
        for x in (130,430,730):
            d.rectangle((x,420,x+220,900),outline=light,width=18)
            for k in range(5):
                d.rectangle((x+20+k*38,490,x+45+k*38,750),fill=accent+"dd")
    elif scene == "railway":
        d.polygon(((450,950),(490,560),(590,560),(630,950)),fill=light+"99")
        d.rectangle((320,410,760,710),fill=accent,outline=light,width=14)
        d.rectangle((380,465,700,580),fill=light+"aa")
    elif scene == "village":
        for x in (110,440,760):
            d.rectangle((x,680,x+200,940),fill=accent)
            d.polygon(((x-20,680),(x+100,530),(x+220,680)),fill=light+"aa")
    elif scene == "mountain":
        d.polygon(((130,930),(460,320),(800,930)),fill=accent)
        d.polygon(((360,500),(460,320),(570,520),(460,480)),fill=light)
    elif scene == "desert":
        d.arc((50,620,1030,1130),180,350,fill=light,width=22)
        d.line((700,870,700,540),fill=light,width=26)
        d.arc((630,600,710,760),0,180,fill=light,width=23)
    elif scene == "underwater":
        d.ellipse((300,540,710,780),fill=accent,outline=light,width=10)
        d.polygon(((300,650),(190,540),(190,760)),fill=light+"aa")
        for x,y in ((180,390),(850,480),(780,300)):
            d.ellipse((x,y,x+65,y+65),outline=light,width=8)
    elif scene == "space":
        d.ellipse((340,410,750,820),fill=accent,outline=light,width=14)
        d.ellipse((180,530,900,710),outline=light,width=18)
    elif scene == "laboratory":
        d.polygon(((440,430),(580,430),(580,620),(710,900),(310,900),(440,620)),fill=accent,outline=light)
        d.line((370,770,650,770),fill=light,width=18)
    elif scene == "garden":
        for x in (230,530,830):
            d.line((x,950,x,590),fill=light,width=16)
            d.ellipse((x-75,490,x+75,640),fill=accent,outline=light,width=12)
    elif scene == "lighthouse":
        d.polygon(((420,930),(460,400),(610,400),(660,930)),fill=accent,outline=light)
        d.rectangle((440,370,625,455),fill=light+"dd")
        d.polygon(((420,370),(535,290),(645,370)),fill=accent)
    elif scene == "cave":
        d.polygon(((0,200),(240,420),(390,210),(560,470),(800,190),(1080,390),(1080,0),(0,0)),fill=accent)
        d.ellipse((380,660,700,1050),fill=light+"77")
    elif scene == "city":
        for x in (100,370,660):
            d.rectangle((x,380,x+230,940),fill=accent,outline=light,width=8)
            for y in (480,600,720):
                d.rectangle((x+50,y,x+100,y+55),fill=light+"aa")
    elif scene == "workshop":
        d.ellipse((330,470,750,890),outline=light,width=45)
        d.ellipse((455,595,625,765),fill=accent)
        d.line((230,450,420,640),fill=light,width=30)
    elif scene == "castle":
        d.rectangle((230,540,850,940),fill=accent)
        for x in (220,690):
            d.rectangle((x,370,x+180,940),fill=accent,outline=light,width=10)
        d.arc((455,720,625,1050),180,360,fill=light,width=22)
    elif scene == "snowfield":
        d.polygon(((70,940),(420,400),(710,940)),fill=light+"aa")
        d.polygon(((300,580),(420,400),(540,590)),fill=light)
        for x,y in ((190,380),(740,480),(850,310)):
            d.line((x-20,y,x+20,y),fill=light,width=7)
            d.line((x,y-20,x,y+20),fill=light,width=7)
    elif scene == "island":
        d.arc((90,750,990,1130),180,360,fill=light,width=26)
        d.line((530,870,560,470),fill=accent,width=28)
        for end in ((330,420),(760,430),(520,280)):
            d.arc((min(530,end[0]),min(450,end[1]),max(570,end[0]+50),570),190,350,fill=light,width=20)
    elif scene == "museum":
        d.polygon(((180,460),(540,270),(900,460)),fill=light+"aa")
        for x in (260,430,600,770):
            d.rectangle((x,480,x+65,900),fill=accent,outline=light,width=8)
        d.rectangle((180,900,900,950),fill=light+"aa")
    # Confine environmental art to the upper scene region. Existing subject,
    # headline, and caption drawing retain ownership of their own layers.
    overlay.paste((0, 0, 0, 0), (0, 1100, 1080, 1920))
    image.paste(Image.alpha_composite(image.convert("RGBA"),overlay).convert("RGB"))
    return image
