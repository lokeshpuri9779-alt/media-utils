# ASTRA image-to-motion worker (optional, zero-cost)
# Usage: python tools/image_motion.py --input scene.png --output scene.mp4 --seconds 5
# Requires FFmpeg with zoompan and libx264. No network calls or credentials.
import argparse
import shutil
import subprocess
from pathlib import Path


def render(image: Path, output: Path, seconds: int, width: int, height: int, fps: int) -> None:
    if not image.is_file() or image.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}:
        raise ValueError('A local PNG/JPEG/WebP image is required')
    if not shutil.which('ffmpeg'):
        raise RuntimeError('ffmpeg not found')
    if not 1 <= seconds <= 30 or not 12 <= fps <= 60:
        raise ValueError('Invalid duration or frame rate')
    if (width, height) not in {(1080, 1920), (1920, 1080), (720, 1280), (1280, 720)}:
        raise ValueError('Unsupported output dimensions')
    output.parent.mkdir(parents=True, exist_ok=True)
    frames = seconds * fps
    vf = (f'scale={width*2}:{height*2}:force_original_aspect_ratio=increase,'
          f'crop={width*2}:{height*2},'
          f'zoompan=z=min(zoom+0.0007' + chr(92) + ',1.15):x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):'
          + f'd={frames}:s={width}x{height}:fps={fps},format=yuv420p')
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-loop', '1', '-i', str(image),
           '-vf', vf, '-frames:v', str(frames), '-an', '-c:v', 'libx264', '-preset', 'veryfast',
           '-crf', '21', '-movflags', '+faststart', str(output)]
    subprocess.run(cmd, check=True, timeout=240)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError('Render produced no output')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--seconds', type=int, default=5)
    p.add_argument('--width', type=int, default=720)
    p.add_argument('--height', type=int, default=1280)
    p.add_argument('--fps', type=int, default=24)
    a = p.parse_args()
    render(a.input, a.output, a.seconds, a.width, a.height, a.fps)

if __name__ == '__main__':
    main()
