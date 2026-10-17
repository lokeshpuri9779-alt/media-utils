"""Generate original, deterministic SVG scene artifacts without external APIs.

Run: python -m astra_v2.visual_artifact_library --count 1200 --output runtime-artifacts/visuals
These are candidate assets; publishing/rendering integration requires separate QA.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
from xml.sax.saxutils import escape

SCENES = ("observatory","forest","harbor","library","railway","village","mountain","desert","underwater","space","laboratory","garden","lighthouse","cave","city","workshop","castle","snowfield","island","museum")
PALETTES = (
    ("#101b36","#384e8a","#f7c778","#b9dfff"),
    ("#22142e","#774c81","#ffad8d","#e8d7ff"),
    ("#082e33","#1b7778","#e7e69d","#a6f2dd"),
    ("#2c1830","#93444c","#ffd18a","#fce7d0"),
    ("#152b21","#3e7452","#e8d5a0","#c7f4bb"),
    ("#18213f","#4567a8","#f3a6c6","#c2d9ff"),
    ("#32221c","#9d6445","#f8dd9a","#ffe9cf"),
    ("#14282e","#48788c","#ffe6b0","#d5f4ff"),
)
def _shape(scene, accent, light, variant):
    shift=(variant % 7)*13
    sky=f'<circle cx="{105+shift}" cy="{100+variant%5*12}" r="{24+variant%3*6}" fill="{light}" opacity=".8"/>'
    motifs={
      "observatory":f'<path d="M90 370V230Q270 55 450 230V370Z" fill="{accent}"/><path d="M240 365V210h60v155" fill="{light}"/>',
      "forest":''.join(f'<path d="M{x} 420l55 -{180+(x+shift)%90} 55 {180+(x+shift)%90}Z" fill="{accent}"/>' for x in (20,180,340)),
      "harbor":f'<path d="M0 360Q135 330 270 360T540 360V720H0Z" fill="{accent}"/><path d="M170 360l90 -180 90 180Z" fill="{light}"/>',
      "library":''.join(f'<rect x="{x}" y="210" width="92" height="260" rx="8" fill="{accent}"/><path d="M{x+25} 240v190M{x+60} 240v190" stroke="{light}" stroke-width="12"/>' for x in (55,225,395)),
      "railway":f'<path d="M175 720L255 270h30l80 450" stroke="{light}" stroke-width="18" fill="none"/><rect x="155" y="220" width="230" height="190" rx="38" fill="{accent}"/>',
      "village":''.join(f'<rect x="{x}" y="{340-x//5}" width="115" height="150" fill="{accent}"/><path d="M{x-15} {340-x//5}l72 -75 73 75Z" fill="{light}"/>' for x in (35,210,385)),
      "mountain":f'<path d="M0 540L160 220l120 190 100 -260 160 390Z" fill="{accent}"/><path d="M115 310l45 -90 50 80M345 240l35 -90 45 110" fill="{light}"/>',
      "desert":f'<path d="M0 490Q130 320 270 450T540 420V720H0Z" fill="{accent}"/><path d="M360 460V240m0 110h-65v-80m65 130h60v-95" stroke="{light}" stroke-width="22" fill="none"/>',
      "underwater":f'<path d="M0 400Q135 360 270 400T540 400V720H0Z" fill="{accent}"/><path d="M150 330q90 -95 180 0q-90 95 -180 0l-60 -70v140Z" fill="{light}"/>',
      "space":f'<circle cx="270" cy="330" r="135" fill="{accent}"/><ellipse cx="270" cy="330" rx="230" ry="55" fill="none" stroke="{light}" stroke-width="20"/>',
      "laboratory":f'<path d="M210 175v210l-85 145h290l-85 -145V175" fill="{accent}" stroke="{light}" stroke-width="12"/><path d="M170 450h200" stroke="{light}" stroke-width="14"/>',
      "garden":''.join(f'<path d="M{x} 520V310" stroke="{light}" stroke-width="10"/><circle cx="{x}" cy="300" r="{40+(x%3)*10}" fill="{accent}"/>' for x in (110,270,430)),
      "lighthouse":f'<path d="M195 560l35 -350h80l35 350Z" fill="{accent}"/><rect x="205" y="170" width="130" height="55" fill="{light}"/><path d="M185 170l85 -75 85 75Z" fill="{accent}"/>',
      "cave":f'<path d="M0 0L150 180 60 350 190 470 270 310 390 470 480 310 540 120V0Z" fill="{accent}"/><circle cx="270" cy="500" r="75" fill="{light}"/>',
      "city":''.join(f'<rect x="{x}" y="{230+(x%4)*40}" width="90" height="400" fill="{accent}"/><path d="M{x+20} 300v260m30 -260v260" stroke="{light}" stroke-width="8" stroke-dasharray="15 20"/>' for x in (20,130,240,350,460)),
      "workshop":f'<circle cx="270" cy="350" r="130" fill="{accent}" stroke="{light}" stroke-width="28" stroke-dasharray="35 16"/><circle cx="270" cy="350" r="52" fill="{light}"/>',
      "castle":f'<path d="M80 550V240h100v80h80V190h100v130h80v-80h70v310Z" fill="{accent}"/><path d="M240 550V420q30 -65 60 0v130" fill="{light}"/>',
      "snowfield":f'<path d="M0 500l150 -240 120 175 95 -200 175 265Z" fill="{accent}"/><path d="M100 340l50 -80 55 80m120 -25 40 -80 55 80" fill="{light}"/>',
      "island":f'<path d="M50 520q220 -180 440 0Z" fill="{accent}"/><path d="M280 470V210m0 90q-150 -140 -190 0m190 0q160 -140 190 0" stroke="{light}" stroke-width="24" fill="none"/>',
      "museum":f'<path d="M50 260l220 -130 220 130Z" fill="{light}"/>'+''.join(f'<rect x="{x}" y="280" width="45" height="260" fill="{accent}"/>' for x in (100,200,300,400)),
    }
    return sky+motifs[scene]

def artifact(index):
    if not isinstance(index,int) or index<0:
        raise ValueError("index must be nonnegative")
    scene=SCENES[index%len(SCENES)]
    palette=PALETTES[(index//len(SCENES))%len(PALETTES)]
    variant=index//(len(SCENES)*len(PALETTES))
    bg,accent,light,star=palette
    seed=int(hashlib.sha256(str(index).encode()).hexdigest()[:8],16)
    stars=''.join(f'<circle cx="{(seed+i*97)%540}" cy="{(seed//(i+1)+i*71)%580}" r="{2+i%3}" fill="{star}" opacity=".65"/>' for i in range(18))
    foreground=f'<path d="M0 {590+variant%6*9}Q270 {550+variant%8*13} 540 {600+variant%5*11}V720H0Z" fill="{accent}" opacity=".65"/>'
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="540" height="720" viewBox="0 0 540 720"><title>{escape(scene)} scene {index}</title><rect width="540" height="720" fill="{bg}"/>{stars}{_shape(scene,accent,light,variant)}{foreground}</svg>'
    return scene,svg

def generate(count,output):
    if count<1 or count>100000:
        raise ValueError("count must be between 1 and 100000")
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    for i in range(count):
        scene,svg=artifact(i)
        (output/f"{i:06d}-{scene}.svg").write_text(svg,encoding="utf-8")
    return count

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--count",type=int,default=1200)
    parser.add_argument("--output",default="runtime-artifacts/visuals")
    args=parser.parse_args()
    print(f"Generated {generate(args.count,args.output)} original SVG scene artifacts")
