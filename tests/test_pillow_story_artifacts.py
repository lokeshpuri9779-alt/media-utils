from PIL import Image, ImageDraw
from astra_v2.pillow_story_artifacts import draw_story_prop

def test_all_story_props_have_distinct_dedicated_renderings():
    names=("key","bell","compass","shield","rocket","heart","wrench","clock")
    frames=[]
    for name in names:
        image=Image.new("RGB",(300,300),(235,238,232))
        draw_story_prop(ImageDraw.Draw(image),name,150,145,.4)
        frames.append(image.tobytes())
    assert len(set(frames))==len(names)

def test_damaged_and_repaired_states_are_visible():
    for name in ("key","bell","compass","shield","rocket","heart","wrench","clock"):
        damaged=Image.new("RGB",(300,300),(235,238,232))
        repaired=Image.new("RGB",(300,300),(235,238,232))
        draw_story_prop(ImageDraw.Draw(damaged),name,150,145,.4,condition="damaged")
        draw_story_prop(ImageDraw.Draw(repaired),name,150,145,.4,condition="repaired")
        assert damaged.tobytes()!=repaired.tobytes()
