#!/usr/bin/env python3
"""Offline espeak narration adapter; uses no remote API."""
import argparse, json, shutil, subprocess, wave
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--script", required=True)
    p.add_argument("--output", default="audio.wav")
    p.add_argument("--voice", default="en")
    p.add_argument("--speed", type=int, default=145)
    args=p.parse_args()
    if not 80 <= args.speed <= 300: p.error("speed must be between 80 and 300")
    engine=shutil.which("espeak-ng") or shutil.which("espeak")
    if not engine: p.error("espeak/espeak-ng missing; no silent fallback")
    text=Path(args.script).read_text(encoding="utf-8").strip()
    if not text: p.error("script is empty")
    output=Path(args.output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([engine,"-v",args.voice,"-s",str(args.speed),"-w",str(output),"--stdin"],
                   input=text,text=True,check=True,timeout=120)
    with wave.open(str(output),"rb") as wav:
        seconds=wav.getnframes()/wav.getframerate()
        if seconds < 0.5: raise RuntimeError("Narration unexpectedly short")
        result={"narration_generated":True,"engine":Path(engine).name,
                "duration_seconds":round(seconds,2),"sample_rate":wav.getframerate(),
                "output":str(output)}
    (output.parent/"narration_report.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
if __name__=="__main__": main()
