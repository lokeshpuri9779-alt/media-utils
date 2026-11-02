"""Isolated review-only deterministic geometry control, not AI fidelity."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path("artifacts/experimental-scene-control/keyframe.png")
BLUE, CREAM, RED = (22,80,211), (242,225,197), (190,35,35)

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (512,768), CREAM)
    d = ImageDraw.Draw(im)
    d.rectangle((0,375,511,767),fill=BLUE)
    d.polygon([(160,430),(250,389),(351,431),(259,475)],fill=(229,66,56))
    d.polygon([(160,430),(259,475),(259,635),(160,586)],fill=RED)
    d.polygon([(259,475),(351,431),(351,586),(259,635)],fill=(126,20,28))
    checks = {"cream_background":im.getpixel((30,100))==CREAM,
              "blue_table_left":im.getpixel((30,650))==BLUE,
              "blue_table_right":im.getpixel((480,650))==BLUE,
              "red_cube_face":im.getpixel((200,520))==RED,
              "blue_below_cube":im.getpixel((260,650))==BLUE}
    passed = all(checks.values())
    report = {"success":passed,"engine":"Pillow deterministic scene control",
              "checks":checks,"approved":False,"published":False,
              "production_ready":False,"semantic_quality":"manual_review_required",
              "character_continuity":"not_verified",
              "note":"Programmed pixel layout is not AI image fidelity."}
    if passed: im.save(OUT)
    else: OUT.unlink(missing_ok=True)
    OUT.with_suffix(".json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not passed: raise SystemExit(1)

if __name__=="__main__": main()
