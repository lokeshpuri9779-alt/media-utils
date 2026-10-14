"""CI-only smoke test for clean cinematic video rendering.

Generated test images are synthetic and must never be published.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from experimental.clean_cinematic_render import render
from imageio_ffmpeg import get_ffmpeg_exe
import subprocess,json

def main():
    with TemporaryDirectory() as temp:
        root=Path(temp)
        images=[]
        for i in range(6):
            image=root/f"scene_{i:02}.png"
            Image.new("RGB",(360,640),(30+i*25,65+i*18,130+i*14)).save(image)
            images.append(image)
        output=root/"review.mp4"
        result=render(images,output,fps=30,seconds=1)
        subprocess.run([get_ffmpeg_exe(),"-v","error","-i",str(output),"-f","null","-"],check=True)
        if not output.is_file() or output.stat().st_size<1000:
            raise RuntimeError("No valid video output")
        print(json.dumps({"status":"pass","frames_expected":180,
                          "scenes":6,"render":result,"publish":False},indent=2))
if __name__=="__main__":main()
