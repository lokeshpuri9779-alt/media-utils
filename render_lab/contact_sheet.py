"""Make a side-by-side review sheet of generated story scenes."""
from pathlib import Path
from PIL import Image, ImageDraw

def make_sheet(folder, output):
    paths = sorted(Path(folder).glob("scene_*.png"))
    if len(paths) < 2:
        raise ValueError("At least two scene images required")
    width, height = 512, 512
    sheet = Image.new("RGB", (width * len(paths), height + 42), "#202020")
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        with Image.open(path) as src:
            frame = src.convert("RGB")
            frame.thumbnail((width, height))
            x = i * width + (width - frame.width) // 2
            y = 42 + (height - frame.height) // 2
            sheet.paste(frame, (x, y))
        draw.text((i * width + 12, 12), f"Scene {i}: {path.name}", fill="white")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return str(output)

if __name__ == "__main__":
    import sys
    print(make_sheet(sys.argv[1], sys.argv[2]))
