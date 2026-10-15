"""On-demand Pillow visual variants: 2,000 character skins and 2,000 icons.

These are reproducible *visual variants*, NOT 2,000 biological species, hand-
drawn SVG files or individual images. No downloads, secrets or paid models.
The eight supported characters retain species-specific silhouettes.
"""
from __future__ import annotations
import hashlib
import math
from PIL import ImageDraw

SPECIES = ("fox", "rabbit", "cat", "dog", "owl", "mouse", "otter", "squirrel")
PALETTES = (
    ((228,120,64),(58,158,164)), ((208,105,76),(117,116,187)),
    ((180,137,95),(64,123,156)), ((232,159,87),(149,102,134)),
    ((200,144,111),(86,151,117)), ((154,126,143),(207,115,117)),
    ((217,184,118),(74,136,171)), ((192,158,139),(160,113,183)),
    ((172,129,108),(67,163,156)), ((211,153,110),(175,127,103)),
)
COSTUMES = ("waistcoat", "hoodie", "explorer", "mechanic", "storybook")
ACCESSORIES = ("none", "scarf", "hat", "bow", "satchel")
CHARACTERS_PER_SPECIES = len(PALETTES)*len(COSTUMES)*len(ACCESSORIES)
CHARACTER_VARIANTS = len(SPECIES)*CHARACTERS_PER_SPECIES

MOTIFS = (
    "star","heart","leaf","moon","sun","flower","diamond","shield",
    "key","book","bell","lantern","clock","cloud","mountain",
    "compass","wrench","rocket","anchor","feather",
)
ICON_VARIANTS = len(MOTIFS)*10*10

def character_recipe(index):
    """Return a full art recipe, with bijective index 0..1999."""
    if not isinstance(index,int) or not 0 <= index < CHARACTER_VARIANTS:
        raise ValueError("character design index out of range")
    species_id, local = divmod(index, CHARACTERS_PER_SPECIES)
    palette_id, local = divmod(local, len(COSTUMES)*len(ACCESSORIES))
    costume_id, accessory_id = divmod(local, len(ACCESSORIES))
    fur, fabric=PALETTES[palette_id]
    return {"id": f"character-{index:04d}", "species": SPECIES[species_id],
            "palette": palette_id, "fur": fur, "fabric": fabric,
            "costume": COSTUMES[costume_id],
            "accessory": ACCESSORIES[accessory_id]}

def visual_identity(story, name, slot=0):
    """Use a story-level seed, NOT beat narration; clothes never flicker."""
    if name not in SPECIES:
        raise ValueError("unsupported actor")
    stable=str(story or "astra-default")
    seed=hashlib.sha256(f"{stable}|{name}|{slot}".encode()).digest()
    local=int.from_bytes(seed[:8],"big") % CHARACTERS_PER_SPECIES
    return SPECIES.index(name)*CHARACTERS_PER_SPECIES + local

def icon_recipe(index):
    if not isinstance(index,int) or not 0 <= index < ICON_VARIANTS:
        raise ValueError("icon recipe index out of range")
    motif_id, tail=divmod(index,100)
    palette, decoration=divmod(tail,10)
    return {"id":f"icon-{index:04d}", "motif":MOTIFS[motif_id],
            "palette":palette,"decoration":decoration}

def icon_for_story(motif, story, salt=""):
    if motif not in MOTIFS:
        raise ValueError("unknown motif")
    digest=hashlib.sha256(f"{story}|{motif}|{salt}".encode()).digest()
    local=int.from_bytes(digest[:8],"big")%100
    return MOTIFS.index(motif)*100 + local

def draw_costume_detail(d, x, y, recipe):
    """Additional recognisable costume geometry; stays inside subject bounds."""
    style=recipe["costume"]
    fabric=recipe["fabric"]
    ink=(35,43,56)
    if style=="hoodie":
        d.arc((x-78,y+84,x+78,y+223),180,355,fill=ink,width=11)
        d.line((x-17,y+145,x-17,y+207),fill=(242,231,211),width=5)
        d.line((x+17,y+145,x+17,y+207),fill=(242,231,211),width=5)
    elif style=="explorer":
        d.line((x-80,y+138,x+81,y+270),fill=(223,198,146),width=15)
        d.rounded_rectangle((x+37,y+197,x+82,y+243),radius=8,
                            fill=(187,154,99),outline=ink,width=3)
    elif style=="mechanic":
        d.rounded_rectangle((x-65,y+202,x-11,y+249),radius=6,
                            fill=(214,187,137),outline=ink,width=3)
        d.line((x-28,y+213,x-28,y+243),fill=fabric,width=7)
    elif style=="storybook":
        d.arc((x-95,y+89,x+95,y+255),15,160,fill=(235,209,155),width=11)
        d.ellipse((x-12,y+205,x+12,y+229),fill=(246,198,85))
    else:
        for yy in (186,235):
            d.ellipse((x-6,y+yy-6,x+6,y+yy+6),fill=(245,221,119),outline=ink,width=2)

def draw_accessory(d,x,y,recipe):
    a=recipe["accessory"]
    ink=(38,45,59)
    if a=="hat":
        d.polygon(((x-99,y-134),(x-77,y-199),(x+78,y-199),(x+100,y-134)),
                  fill=recipe["fabric"],outline=ink,width=5)
        d.rounded_rectangle((x-122,y-143,x+122,y-119),radius=9,
                            fill=recipe["fabric"],outline=ink,width=3)
    elif a=="scarf":
        d.arc((x-101,y+65,x+102,y+162),5,175,fill=(239,203,148),width=19)
        d.polygon(((x+74,y+118),(x+111,y+124),(x+97,y+249),(x+61,y+246)),
                  fill=(239,203,148))
    elif a=="bow":
        d.polygon(((x-8,y+114),(x-55,y+86),(x-55,y+143)),
                  fill=(241,206,134),outline=ink,width=3)
        d.polygon(((x+8,y+114),(x+55,y+86),(x+55,y+143)),
                  fill=(241,206,134),outline=ink,width=3)
        d.ellipse((x-13,y+105,x+13,y+126),fill=(207,137,98))
    elif a=="satchel":
        d.line((x-65,y+110,x+72,y+284),fill=(227,202,144),width=9)
        d.rounded_rectangle((x+48,y+240,x+106,y+294),radius=8,
                            fill=(159,113,78),outline=ink,width=4)

def _star(cx,cy,r,tips=5):
    return [(cx+int(r*(.47 if j%2 else 1)*math.cos(-math.pi/2+j*math.pi/tips)),
             cy+int(r*(.47 if j%2 else 1)*math.sin(-math.pi/2+j*math.pi/tips)))
            for j in range(tips*2)]

def draw_icon(d, index, x, y, size=48):
    """Draw the matching silhouette plus deterministic ornament; no substitutions."""
    v=icon_recipe(index)
    motif=v["motif"]
    palette=v["palette"]
    deco=v["decoration"]
    colors=((239,190,100),(113,181,173),(197,134,179),(225,143,103),
            (155,180,222),(194,183,113),(147,204,150),(217,154,141),
            (192,155,217),(131,183,202))
    color=colors[palette]
    ink=(35,45,62)
    r=max(9,int(size*.47))
    if motif in ("star","sun","flower","compass"):
        d.polygon(_star(x,y,r,5 if motif!="compass" else 4),fill=color,outline=ink,width=3)
    elif motif in ("moon","cloud"):
        d.ellipse((x-r,y-r,x+r,y+r),fill=color,outline=ink,width=3)
        if motif=="moon": d.ellipse((x-r//3,y-r-4,x+r+9,y+r-15),fill=(40,75,85))
        else:
            d.ellipse((x-r,y-r//2,x+r,y+r//2),fill=color)
    elif motif in ("heart","leaf","feather"):
        d.polygon(((x-r,y-r//2),(x-r//2,y-r),(x,y-r//2),(x+r//2,y-r),
                   (x+r,y-r//2),(x,y+r)),fill=color,outline=ink,width=3)
    elif motif in ("diamond","shield","mountain","rocket"):
        d.polygon(((x,y-r),(x+r,y-r//5),(x+r//2,y+r),(x-r//2,y+r),(x-r,y-r//5)),
                  fill=color,outline=ink,width=3)
    elif motif in ("book","lantern","clock","bell"):
        d.rounded_rectangle((x-r,y-r,x+r,y+r),radius=max(3,r//5),
                            fill=color,outline=ink,width=3)
        d.line((x,y-r+6,x,y+r-6),fill=ink,width=3)
    elif motif in ("key","wrench","anchor"):
        d.ellipse((x-r//2,y-r,x+r//2,y),outline=color,width=8)
        d.line((x,y,x,y+r),fill=color,width=8)
        d.line((x,y+r//2,x+r//2,y+r//2),fill=ink,width=4)
    else:
        d.ellipse((x-r,y-r,x+r,y+r),fill=color,outline=ink,width=3)
    # Ten distinct ornament geometries, not just a filename variation.
    if deco:
        for k in range(1+(deco-1)//3):
            ox=x-r+7+((k*13+deco*7)%(2*r-14))
            oy=y+r-8-(k*7%max(7,r))
            d.ellipse((ox-2-deco%3,oy-2,ox+2+deco%3,oy+2),
                      fill=(255,238,200))
    return v["id"]
