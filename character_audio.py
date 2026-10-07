from __future__ import annotations

"""Dialogue-aware audio timing for Astra character stories.

Speaker labels are control metadata only and are never spoken aloud.
Each scene receives its own timed dialogue track so visual scene duration
is derived from the real synthesized speech instead of guessed first.
"""

import math
import re
import wave
from pathlib import Path

import numpy as np

from studio_renderer import RATE, voice_engine

_SPEAKER_RE=re.compile(r"(?:(?<=^)|(?<=\s))([A-Za-z][A-Za-z0-9 _'-]{0,24}):\s*")


def _segments(text: str) -> list[tuple[str|None,str]]:
    text=" ".join(str(text or "").split())
    matches=list(_SPEAKER_RE.finditer(text))
    if not matches:
        return [(None,text)] if text else []
    out=[]
    prefix=text[:matches[0].start()].strip()
    if prefix:
        out.append((None,prefix))
    for i,m in enumerate(matches):
        start=m.end()
        end=matches[i+1].start() if i+1<len(matches) else len(text)
        spoken=text[start:end].strip()
        if spoken:
            out.append((m.group(1).strip(),spoken))
    return out


def _voice_for(story: dict, scene: dict, speaker: str|None) -> tuple[str,float]:
    cast=story.get("voice_cast") or {}
    cfg=cast.get(speaker or "") if isinstance(cast,dict) else None
    if isinstance(cfg,dict):
        return str(cfg.get("voice") or scene.get("voice_name") or story.get("voice_profile") or "af_heart"), float(cfg.get("speed") or scene.get("voice_speed") or story.get("voice_speed") or 1.03)
    if isinstance(cfg,str):
        return cfg,float(scene.get("voice_speed") or story.get("voice_speed") or 1.03)
    return str(scene.get("voice_name") or story.get("voice_profile") or "af_heart"),float(scene.get("voice_speed") or story.get("voice_speed") or 1.03)


def prepare_character_audio(story: dict, plan: list[dict], output: Path) -> tuple[float,dict]:
    engine=voice_engine()
    cursor=0.0
    scene_reports=[]
    rendered=[]

    for idx,scene in enumerate(plan):
        pieces=[]
        segment_report=[]
        segment_cursor = .14
        for speaker,spoken in _segments(scene.get("speech","")):
            speaker = speaker or scene.get("speaker") or None
            voice,speed=_voice_for(story,scene,speaker)
            samples,rate=engine.create(spoken,voice=voice,speed=speed,lang="en-us")
            samples=np.asarray(samples,dtype=np.float32)
            if rate!=RATE or len(samples)==0 or not np.isfinite(samples).all():
                raise RuntimeError(f"Invalid character dialogue audio in scene {idx+1}.")
            peak=float(np.max(np.abs(samples)))
            if peak>0:
                samples=samples*(0.70/peak)
            pieces.append(samples)
            segment_report.append({
                "speaker":speaker or "narrator",
                "text":spoken,
                "voice":voice,
                "speed":speed,
                "seconds":round(len(samples)/RATE,3),
                "start":round(segment_cursor, 6),
                "end":round(segment_cursor + len(samples)/RATE, 6),
            })
            pieces.append(np.zeros(int(0.14*RATE),dtype=np.float32))
            segment_cursor += len(samples)/RATE + .14

        spoken_audio=np.concatenate(pieces) if pieces else np.zeros(int(.25*RATE),dtype=np.float32)
        # Dialogue starts shortly after the visual cut and gets a reaction hold.
        lead=np.zeros(int(.14*RATE),dtype=np.float32)
        tail=np.zeros(int(.34*RATE),dtype=np.float32)
        scene_audio=np.concatenate([lead,spoken_audio,tail])

        min_duration=max(1.0,float(scene.get("min_duration") or scene.get("duration") or 0))
        duration=max(min_duration,len(scene_audio)/RATE)
        if len(scene_audio)<int(duration*RATE):
            scene_audio=np.pad(scene_audio,(0,int(duration*RATE)-len(scene_audio)))
        else:
            scene_audio=scene_audio[:int(duration*RATE)]

        scene["start"]=cursor
        scene["voice_start"]=cursor+.14
        scene["duration"]=duration
        scene["end"]=cursor+duration
        scene["dialogue_segments"]=segment_report
        cursor+=duration
        rendered.append(scene_audio)
        scene_reports.append({
            "scene":idx+1,
            "duration":round(duration,3),
            "dialogue":segment_report,
        })

    target_min=float(story.get("target_duration_min",20))
    target_max=float(story.get("target_duration_max",40))
    if cursor>target_max:
        raise RuntimeError(f"Dialogue-first duration {cursor:.2f}s exceeds story maximum {target_max:.2f}s.")
    if cursor<target_min and rendered:
        pad=target_min-cursor
        rendered[-1]=np.pad(rendered[-1],(0,int(pad*RATE)))
        plan[-1]["duration"]+=pad
        plan[-1]["end"]+=pad
        scene_reports[-1]["duration"]=round(plan[-1]["duration"],3)
        cursor=target_min

    mono=np.concatenate(rendered) if rendered else np.zeros(int(cursor*RATE),dtype=np.float32)
    n=len(mono)
    t=np.arange(n,dtype=np.float32)/RATE

    # Quiet cinematic bed with strong automatic ducking around speech.
    root=130.813
    bed=(np.sin(2*np.pi*root*.5*t)+.35*np.sin(2*np.pi*root*.75*t))*.012
    duck=np.ones(n,dtype=np.float32)
    fx=np.zeros(n,dtype=np.float32)

    for i,scene in enumerate(plan):
        a=int(scene["start"]*RATE); b=min(n,int(scene["end"]*RATE))
        va=int(scene["voice_start"]*RATE)
        voice_end=max((float(x["end"]) for x in scene.get("dialogue_segments",[])), default=.14)
        vb=min(n,int((scene["start"]+voice_end+.2)*RATE))
        if vb>va:
            attack=max(1,int(.07*RATE)); release=max(1,int(.14*RATE))
            duck[va:vb]=np.minimum(duck[va:vb],.20)
            for k in range(max(0,va-attack),va):
                x=(k-(va-attack))/attack
                duck[k]=min(duck[k],1-.8*x)
            for k in range(vb,min(n,vb+release)):
                x=(k-vb)/release
                duck[k]=min(duck[k],.2+.8*x)

        # Story-beat SFX occur at the visual action, not arbitrarily at every cut.
        beat=str(scene.get("story_beat") or "")
        pos=a+int(.20*RATE)
        size=min(int(.28*RATE),n-pos)
        if size>0:
            u=np.arange(size,dtype=np.float32)/RATE
            if beat in {"escalation","payoff"}:
                fx[pos:pos+size]+=np.sin(2*np.pi*(180+520*u)*u)*np.exp(-u*13)*.055
            elif beat in {"reveal","button"}:
                fx[pos:pos+size]+=np.sin(2*np.pi*520*u)*np.exp(-u*18)*.032

    mixed=mono+bed*duck+fx
    fade=np.minimum(np.clip(t/.08,0,1),np.clip((cursor-t)/.16,0,1))
    mixed*=fade
    peak=float(np.max(np.abs(mixed))) if len(mixed) else 0
    if peak>.94:
        mixed*=.94/peak

    stereo=np.stack([mixed,mixed],axis=1)
    output.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(output),"wb") as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(RATE)
        f.writeframes((stereo*32767).astype("<i2").tobytes())

    return cursor,{
        "renderer":"character-dialogue-audio-1",
        "duration":round(cursor,3),
        "scene_reports":scene_reports,
        "peak_dbfs":round(20*math.log10(max(float(np.max(np.abs(stereo))),1e-9)),2),
        "speaker_labels_spoken":False,
        "music_ducking":True,
        "scene_timed_sfx":True,
    }
