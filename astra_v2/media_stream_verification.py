"""Post-render stream evidence checks for ASTRA preview videos."""
from array import array
import math
from pathlib import Path
import subprocess
from imageio_ffmpeg import get_ffmpeg_exe


def pcm_rms_dbfs(pcm):
    if not pcm or len(pcm) % 2:
        raise ValueError("invalid PCM")
    samples = array("h")
    samples.frombytes(pcm)
    power = sum(int(x) ** 2 for x in samples) / len(samples)
    return 20 * math.log10(math.sqrt(power) / 32768) if power else float("-inf")


def verify_mp4_streams(video_path):
    video = Path(video_path)
    if not video.is_file() or not video.stat().st_size:
        raise ValueError("missing MP4")
    ffmpeg = get_ffmpeg_exe()
    result = subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-i", str(video),
                             "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
                            capture_output=True, timeout=120)
    result.check_returncode()
    audio = subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-i", str(video),
                            "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "8000",
                            "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1"],
                           capture_output=True, timeout=120)
    audio.check_returncode()
    rms = pcm_rms_dbfs(audio.stdout)
    if rms < -55:
        raise ValueError("final MP4 audio is silent or too quiet")
    return {"pass": True, "decoded_video_and_audio": True,
            "audio_rms_dbfs": round(rms, 2),
            "decoded_audio_samples": len(audio.stdout) // 2}
