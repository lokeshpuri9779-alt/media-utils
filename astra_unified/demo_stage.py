#!/usr/bin/env python3
"""Offline smoke adapter; validates video transport, NOT AI image generation or TTS."""
import json, subprocess, sys, wave
from pathlib import Path
import cv2
import numpy as np

stage=sys.argv[1]
assets=Path(sys.argv[2]) if len(sys.argv)>2 else Path("scenes")
out=Path.cwd()
if stage=="story":
    (out/"story.json").write_text(json.dumps({"title":"Lighthouse pilot","source":"existing storyboard crops"}))
elif stage=="images":
    paths=sorted(assets.glob("scene_*.jpg"))[:8]
    if len(paths)!=8: raise RuntimeError("Eight existing scene JPGs required")
    (out/"scenes.txt").write_text("\n".join(str(p.resolve()) for p in paths))
elif stage=="consistency":
    paths=(out/"scenes.txt").read_text().splitlines()
    if any(cv2.imread(p) is None for p in paths): raise RuntimeError("Invalid scene")
    (out/"consistency.json").write_text(json.dumps({"technical_images_valid":8,"character_consistency_verified":False}))
elif stage=="animation":
    paths=(out/"scenes.txt").read_text().splitlines()
    proc=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pixel_format","bgr24","-video_size","360x640","-framerate","12","-i","-","-an","-c:v","libx264","-pix_fmt","yuv420p","silent.mp4"],stdin=subprocess.PIPE)
    for i in range(96):
        img=cv2.imread(paths[i//12]);h,w=img.shape[:2];scale=max(360/w,640/h)*1.06
        nw,nh=int(w*scale)+2,int(h*scale)+2
        img=cv2.resize(img,(nw,nh));x=(nw-360)//2;y=(nh-640)//2
        proc.stdin.write(img[y:y+640,x:x+360].tobytes())
    proc.stdin.close()
    if proc.wait(): raise RuntimeError("Video encoder failed")
elif stage=="narration":
    samples=np.zeros(16000*8,dtype="<i2")
    with wave.open("audio.wav","wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(samples.tobytes())
    (out/"audio_status.json").write_text(json.dumps({"narration":False,"audio":"silent placeholder"}))
elif stage=="edit":
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i","silent.mp4","-i","audio.wav","-c:v","copy","-c:a","aac","-shortest","pilot.mp4"],check=True)
elif stage=="quality":
    cap=cv2.VideoCapture("pilot.mp4");n=0
    while cap.read()[0]:n+=1
    cap.release()
    if n!=96:raise RuntimeError(f"Expected 96 frames, got {n}")
    (out/"qa.json").write_text(json.dumps({"decoded_frames":n,"passed":True,"ai_generation_verified":False,"tts_verified":False}))
else:raise ValueError(stage)
print("PASS",stage)
