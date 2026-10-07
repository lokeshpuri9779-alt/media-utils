from __future__ import annotations

import asyncio
import json
import math
import re
import subprocess
import tempfile
import wave

import numpy as np
from pathlib import Path

import edge_tts
from imageio_ffmpeg import get_ffmpeg_exe

VOICE_BY_SPEAKER={
    "pip":"en-US-AnaNeural",
    "ember":"en-US-AriaNeural",
    "grandma":"en-US-JennyNeural",
    "milo":"en-US-AnaNeural",
    "papa":"en-US-GuyNeural",
    "nico":"en-US-AnaNeural",
    "tala":"en-US-AriaNeural",
    "kito":"en-US-AnaNeural",
    "mom":"en-US-JennyNeural",
    "mother":"en-US-JennyNeural",
}
DEFAULT_VOICE="en-US-AnaNeural"

_SPEAKER_RE=re.compile(r"(?:(?<=^)|(?<=[.!?]))\s*([A-Za-z][A-Za-z ]{0,20}):\s*")


def _rate_from_speed(speed: float) -> str:
    pct=round((float(speed)-1.0)*100)
    pct=max(-20,min(20,pct))
    return f"{pct:+d}%"


def split_speakers(text: str) -> list[tuple[str,str]]:
    text=" ".join(str(text or "").split())
    matches=list(_SPEAKER_RE.finditer(text))
    if not matches:
        return [("narrator",text)] if text else []
    parts=[]
    for i,m in enumerate(matches):
        start=m.end()
        end=matches[i+1].start() if i+1<len(matches) else len(text)
        spoken=text[start:end].strip(" .")
        if spoken:
            parts.append((m.group(1).strip().lower(),spoken))
    return parts


async def _synth(text: str, voice: str, rate: str, output: Path) -> list[dict]:
    output.parent.mkdir(parents=True,exist_ok=True)
    comm=edge_tts.Communicate(text,voice=voice,rate=rate)
    words=[]
    with output.open("wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"]=="audio":
                fh.write(chunk["data"])
            elif chunk["type"]=="WordBoundary":
                words.append({
                    "text":str(chunk.get("text") or ""),
                    "offset":float(chunk.get("offset",0))/10_000_000,
                    "duration":float(chunk.get("duration",0))/10_000_000,
                })
    return words


def _duration(path: Path) -> float:
    ffmpeg=get_ffmpeg_exe()
    # imageio-ffmpeg points to ffmpeg; ffprobe usually sits beside it.
    probe=Path(ffmpeg).with_name("ffprobe")
    cmd=[str(probe if probe.exists() else "ffprobe"),"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)]
    return float(subprocess.check_output(cmd,text=True).strip())


def _concat_audio(parts: list[Path], output: Path, gap: float=.08) -> None:
    ffmpeg=get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="astra_dialogue_concat_") as td:
        root=Path(td)
        normalized=[]
        for i,p in enumerate(parts):
            dst=root/f"p{i:02d}.wav"
            subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-y","-i",str(p),"-ar","48000","-ac","2",str(dst)],check=True)
            normalized.append(dst)
            if gap>0 and i<len(parts)-1:
                g=root/f"g{i:02d}.wav"
                subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-y","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t",f"{gap:.3f}",str(g)],check=True)
                normalized.append(g)
        manifest=root/"concat.txt"
        manifest.write_text("\n".join(f"file '{p.as_posix()}'" for p in normalized)+"\n",encoding="utf-8")
        subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(manifest),"-c:a","pcm_s16le",str(output)],check=True)


def build_synced_dialogue(plan: list[dict], root: Path, default_speed: float=1.02) -> dict:
    root.mkdir(parents=True,exist_ok=True)
    scene_audio=[]
    cursor=0.0
    timeline=[]
    for i,scene in enumerate(plan):
        chunks=split_speakers(str(scene.get("speech") or ""))
        if not chunks:
            chunks=[("narrator","")]
        part_files=[]
        word_rows=[]
        local=0.0
        rate=_rate_from_speed(float(scene.get("voice_speed") or default_speed))
        for j,(speaker,text) in enumerate(chunks):
            if not text:
                continue
            p=root/f"scene_{i:02d}_part_{j:02d}.mp3"
            voice=VOICE_BY_SPEAKER.get(speaker,DEFAULT_VOICE)
            words=asyncio.run(_synth(text,voice,rate,p))
            d=_duration(p)
            for w in words:
                w.update({"speaker":speaker,"start":cursor+local+w["offset"],"end":cursor+local+w["offset"]+w["duration"]})
                word_rows.append(w)
            part_files.append(p)
            local+=d+.08
        if not part_files:
            raise RuntimeError(f"No dialogue audio produced for scene {i+1}.")
        scene_wav=root/f"scene_{i:02d}.wav"
        _concat_audio(part_files,scene_wav)
        spoken=_duration(scene_wav)
        hold=max(2.0,spoken+.28)
        scene["duration"]=hold
        scene["min_duration"]=hold
        scene["voice_start"]=cursor+.06
        scene["start"]=cursor
        scene["end"]=cursor+hold
        timeline.append({
            "scene":i+1,
            "start":cursor,
            "end":cursor+hold,
            "spoken_seconds":spoken,
            "hold_seconds":hold,
            "speakers":[x[0] for x in chunks],
            "words":word_rows,
        })
        scene_audio.append(scene_wav)
        cursor+=hold
    full=root/"dialogue.wav"
    _concat_audio(scene_audio,full,gap=0.0)
    return {"audio_path":str(full),"duration":cursor,"timeline":timeline}


def build_character_mix(dialogue_path: str | Path, timeline: list[dict], plan: list[dict], output: str | Path) -> dict:
    """Mix dialogue with restrained music and action-timed SFX on the same scene clock."""
    dialogue_path=Path(dialogue_path)
    output=Path(output)
    with wave.open(str(dialogue_path),"rb") as wf:
        rate=wf.getframerate()
        channels=wf.getnchannels()
        raw=wf.readframes(wf.getnframes())
    audio=np.frombuffer(raw,dtype="<i2").astype(np.float32)/32768.0
    if channels==1:
        audio=np.repeat(audio[:,None],2,axis=1)
    else:
        audio=audio.reshape(-1,channels)[:,:2]
    n=len(audio)
    t=np.arange(n,dtype=np.float32)/rate
    # Gentle cinematic bed; dialogue remains dominant.
    root=146.83
    music=(np.sin(2*np.pi*root*.5*t)+.35*np.sin(2*np.pi*root*.75*t))*.012
    fx=np.zeros(n,dtype=np.float32)
    duck=np.ones(n,dtype=np.float32)
    for row,scene in zip(timeline,plan):
        start=float(row["start"])
        spoken=float(row["spoken_seconds"])
        a=max(0,int((start+.02)*rate)); b=min(n,int((start+spoken+.18)*rate))
        if b>a:
            duck[a:b]=np.minimum(duck[a:b],.28)
        beat=str(scene.get("story_beat") or "").lower()
        pos=min(n-1,max(0,int(start*rate)))
        dur=min(n-pos,int(.30*rate))
        if dur<=0:
            continue
        u=np.arange(dur,dtype=np.float32)/rate
        if beat in {"reveal","build","contrast"}:
            tone=np.sin(2*np.pi*(260+180*u)*u)*np.exp(-u*14)*.030
        elif beat=="escalation":
            tone=(np.sin(2*np.pi*(90+420*u)*u)+.25*np.sin(2*np.pi*620*u))*np.exp(-u*9)*.050
        elif beat=="payoff":
            tone=(np.sin(2*np.pi*523*u)+.5*np.sin(2*np.pi*659*u))*np.exp(-u*7)*.040
        else:
            tone=np.sin(2*np.pi*392*u)*np.exp(-u*11)*.026
        fx[pos:pos+dur]+=tone
    bed=music*duck
    out=audio.copy()
    out[:,0]+=bed+fx
    out[:,1]+=bed+fx
    peak=float(np.max(np.abs(out))) if len(out) else 0.0
    if peak>.95:
        out*=.95/peak
    output.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(output),"wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(rate)
        wf.writeframes((np.clip(out,-1,1)*32767).astype("<i2").tobytes())
    return {
        "path":str(output),
        "rate":rate,
        "peak":peak,
        "music":"ducked cinematic bed",
        "sfx":"story-beat aligned",
    }
