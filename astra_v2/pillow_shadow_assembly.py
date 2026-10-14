"""Add a supplied narration WAV and optional timed subtitle track to a Pillow shadow video.

No speech is synthesized here. Never marks output publishable.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
from imageio_ffmpeg import get_ffmpeg_exe

def assemble(video, narration_wav, output, captions_srt=None):
    video,narration_wav,output=map(Path,(video,narration_wav,output))
    if not video.is_file() or not narration_wav.is_file():
        raise FileNotFoundError("Rendered video and genuine narration WAV required")
    output.parent.mkdir(parents=True,exist_ok=True)
    command=[get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y",
             "-i",str(video),"-i",str(narration_wav)]
    if captions_srt is not None:
        captions_srt=Path(captions_srt)
        if not captions_srt.is_file():
            raise FileNotFoundError("Caption file missing")
        command.extend(["-i",str(captions_srt)])
    command.extend(["-map","0:v:0","-map","1:a:0"])
    if captions_srt is not None:
        command.extend(["-map","2:s:0","-c:s","mov_text"])
    command.extend(["-c:v","copy","-c:a","aac","-b:a","160k",
                    "-shortest","-movflags","+faststart",str(output)])
    subprocess.run(command,check=True,timeout=180)
    if not output.is_file() or output.stat().st_size<1000:
        raise RuntimeError("Assembled shadow video is missing")
    return {"output":str(output),"audio_source":"provided_wav",
            "caption_source":"provided_srt" if captions_srt else None,
            "publication_eligible":False}
