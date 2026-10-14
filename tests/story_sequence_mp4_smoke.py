"""Produce and decode a short six-action storyboard MP4, offline and upload-free.

Synthetic audio is a test signal, NOT generated speech.
"""
import json
import math
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from PIL import Image
from astra_v2.story_action_motion import choose_action
from astra_v2.story_visuals import select_subject, draw_subject

BEATS=("The fox runs.","The fox jumps.","The fox dances.","The fox hides.","The fox walks.","The fox looks.")
FPS=6
SIZE=(360,640)

def command(args):
    return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)

def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe required")
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        raw=root/"video.mp4"
        final=root/"story.mp4"
        audio=root/"tone.wav"
        subs=root/"captions.srt"
        story={"title":"The fox's journey"}
        frames=[]
        lines=[]
        for i,speech in enumerate(BEATS):
            shot={"speech":speech,"visual":"story"}
            actor=select_subject(story,shot)
            action=choose_action(shot)
            assert actor=="fox" and action!="idle",(actor,action)
            lines.append(f"{i+1}\n00:00:{i:02d},000 --> 00:00:{i+1:02d},000\n{speech}\n")
            for f in range(FPS):
                frame=Image.new("RGB",(1080,1920),(12,14,19))
                assert draw_subject(frame,actor,i+f/FPS,(255,175,90),action)
                frames.append(frame.resize(SIZE,Image.Resampling.BILINEAR).tobytes())
        proc=subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s","360x640","-r",str(FPS),"-i","pipe:0","-an","-c:v","libx264","-pix_fmt","yuv420p",str(raw)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
        _,err=proc.communicate(b"".join(frames),timeout=120)
        if proc.returncode:
            raise RuntimeError(err.decode(errors="replace"))
        with wave.open(str(audio),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
            import struct
            w.writeframes(b"".join(struct.pack("<h",int(1300*math.sin(2*math.pi*440*n/16000))) for n in range(6*16000)))
        subs.write_text("\n".join(lines))
        command(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(raw),"-i",str(audio),"-i",str(subs),"-map","0:v:0","-map","1:a:0","-map","2:s:0","-c:v","copy","-c:a","aac","-c:s","mov_text","-shortest",str(final)])
        probe=json.loads(command(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,codec_name","-of","json",str(final)]).stdout)
        streams={s["codec_type"] for s in probe["streams"]}
        assert {"video","audio","subtitle"}<=streams,probe
        assert float(probe["format"]["duration"])>=5.5,probe
        command(["ffmpeg","-v","error","-i",str(final),"-f","null","-"])
        print(json.dumps({"status":"pass","scenes":6,"frames":len(frames),"streams":sorted(streams),"duration":probe["format"]["duration"]}))

if __name__=="__main__":
    main()
