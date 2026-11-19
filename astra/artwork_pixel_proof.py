"""Verify actual decoded video frames contain the requested scene backgrounds.

Uses broad central-frame color agreement rather than trusting a manifest alone.
Review-only; never grants production approval.
"""
import json
from pathlib import Path
import av
from PIL import Image
import io


def _video_duration(container, stream):
    if stream.duration is not None and stream.time_base is not None:
        return float(stream.duration * stream.time_base)
    if container.duration is not None:
        return float(container.duration / av.time_base)
    raise ValueError("video_duration_unavailable")


def _frame_png_at(video, timestamp):
    with av.open(str(video)) as container:
        stream = next((item for item in container.streams if item.type == "video"), None)
        if stream is None or stream.time_base is None:
            raise ValueError("video_stream_unavailable")
        target_pts = int(timestamp / float(stream.time_base))
        container.seek(max(0, target_pts), stream=stream, backward=True, any_frame=False)
        fallback = None
        for frame in container.decode(stream):
            fallback = frame
            if frame.pts is not None and frame.pts * stream.time_base >= timestamp:
                return frame.to_image().convert("RGB")
        if fallback is None:
            raise ValueError("video_frame_unavailable")
        return fallback.to_image().convert("RGB")


def verify_pixels(video, storyboard, manifest, minimum_agreement=0.58):
    rows = json.loads(Path(storyboard).read_text())["scenes"]
    assets = json.loads(Path(manifest).read_text())["assets"]
    by_id = {x["id"]: x for x in assets}
    root = Path(manifest).resolve().parent.parent
    with av.open(str(video)) as container:
        stream = next((item for item in container.streams if item.type == "video"), None)
        if stream is None:
            raise ValueError("video_stream_unavailable")
        duration = _video_duration(container, stream)
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
        frame = _frame_png_at(video, timestamp).resize((54, 96))
        with Image.open(path) as art:
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
    Path(output).write_text(json.dumps(result, indent=2) + "\\n")
    return result
