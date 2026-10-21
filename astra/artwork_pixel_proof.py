"""Verify actual decoded video frames contain the requested scene backgrounds.

Uses broad central-frame color agreement rather than trusting a manifest alone.
Review-only; never grants production approval.
"""
import json
import subprocess
from pathlib import Path
from PIL import Image
import io


def verify_pixels(video, storyboard, manifest, minimum_agreement=0.58):
    rows = json.loads(Path(storyboard).read_text())["scenes"]
    assets = json.loads(Path(manifest).read_text())["assets"]
    by_id = {x["id"]: x for x in assets}
    root = Path(manifest).resolve().parent.parent
    duration = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(video)], text=True).strip())
    results = []
    # Speech duration varies, so sample each scene's central temporal region.
    # Report conservative pixel similarity and do not claim a definitive visual match.
    for index, row in enumerate(rows):
        asset = by_id[row["background"]]
        if asset.get("status") != "approved":
            raise ValueError("pixel_proof_requires_approved_fixture")
        path = (root / asset["path"]).resolve()
        if root not in path.parents:
            raise ValueError("artwork_path_outside_fixture")
        timestamp = duration * (index + 0.5) / len(rows)
        frame_bytes = subprocess.check_output([
            "ffmpeg", "-v", "error", "-ss", str(timestamp), "-i", str(video),
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"])
        with Image.open(io.BytesIO(frame_bytes)) as img, Image.open(path) as art:
            frame = img.convert("RGB").resize((54, 96))
            expected = art.convert("RGB").resize((54, 96))
            # Compare only upper region, avoiding lower-third subtitles.
            samples = [(x, y) for y in range(6, 50, 3) for x in range(6, 48, 3)]
            error = sum(sum(abs(a-b) for a,b in zip(frame.getpixel((x,y)),expected.getpixel((x,y))))
                        for x,y in samples) / (len(samples) * 3 * 255)
            agreement = round(1-error, 4)
        results.append({"scene": index+1, "requested_background": row["background"],
                        "sample_time_seconds": round(timestamp, 3),
                        "pixel_color_agreement": agreement,
                        "passes_color_threshold": agreement >= minimum_agreement})
    return {"review_only": True, "method": "upper_frame_rgb_color_agreement",
            "threshold": minimum_agreement, "all_pass": all(x["passes_color_threshold"] for x in results),
            "scenes": results}


def save_pixel_proof(video, storyboard, manifest, output):
    result = verify_pixels(video, storyboard, manifest)
    Path(output).write_text(json.dumps(result, indent=2) + "\n")
    return result
