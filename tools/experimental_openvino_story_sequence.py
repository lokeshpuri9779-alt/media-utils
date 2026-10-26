"""Isolated three-scene CPU storyboard feasibility benchmark. Never publishes."""
import json
import resource
import time
from pathlib import Path

OUT = Path("artifacts/experimental-openvino/story")
SUBJECT = ("one solitary tall lighthouse with red and white horizontal stripes, small dark "
           "roof and one lantern at the top, on a rocky island in the ocean, the entire "
           "lighthouse clearly visible from base to lantern, consistent storybook painting")
SCENES = [
    ("01_sunset", "at warm golden sunset with a calm sea, orange clouds and soft golden light"),
    ("02_storm", "during a dramatic rainstorm with dark clouds, rough waves and bright beacon light"),
    ("03_after", "on a peaceful clear morning after the storm, gentle blue sky and calm water"),
]
NEGATIVE = ("multiple lighthouses, duplicate towers, cropped building, floating objects, "
            "disjointed architecture, distorted tower, watermark, words, letters")
MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"engine": "OpenVINO CPU FP32", "model": MODEL, "steps_per_scene": 12,
              "seed": 42, "approved": False, "published": False,
              "production_ready": False, "semantic_match": "manual_review_required",
              "character_continuity": "manual_review_required", "scenes": []}
    began = time.monotonic()
    stage = "initialization"
    try:
        from optimum.intel import OVStableDiffusionPipeline
        from PIL import Image, ImageDraw
        import torch
        from astra_v2.omniroute_image_assets import image_quality_report
        stage = "load_export"
        print("ASTRA_STORY_STAGE: load_export", flush=True)
        pipe = OVStableDiffusionPipeline.from_pretrained(
            MODEL, export=True, compile=False, device="CPU", load_in_8bit=False,
            ov_config={"INFERENCE_PRECISION_HINT": "f32"})
        stage = "compile"
        print("ASTRA_STORY_STAGE: compile", flush=True)
        pipe.reshape(batch_size=1, height=768, width=512, num_images_per_prompt=1)
        pipe.compile()
        images = []
        for index, (slug, setting) in enumerate(SCENES):
            stage = "generate_" + slug
            print("ASTRA_STORY_STAGE: " + stage, flush=True)
            started = time.monotonic()
            # Independent reset to the same noise seed gives comparable compositions;
            # it does NOT guarantee subject/identity continuity.
            generator = torch.Generator(device="cpu").manual_seed(42)
            result = pipe(SUBJECT + ", " + setting, negative_prompt=NEGATIVE,
                          height=768, width=512, num_inference_steps=12,
                          guidance_scale=8.0, generator=generator)
            img = result.images[0]
            if not isinstance(img, Image.Image):
                raise ValueError("No PIL image returned")
            path = OUT / (slug + ".png")
            img.save(path)
            quality = image_quality_report(path.read_bytes(), "scene")
            report["scenes"].append({"id": slug, "quality": quality,
                                      "png": str(path), "width": img.width,
                                      "height": img.height,
                                      "elapsed_seconds": round(time.monotonic() - started, 2),
                                      "nsfw_content_detected": (
                                          result.nsfw_content_detected[0] if
                                          getattr(result, "nsfw_content_detected", None) else None)})
            images.append(img)
            print("ASTRA_STORY_SCENE: " + json.dumps(report["scenes"][-1]), flush=True)
        stage = "contact_sheet"
        sheet = Image.new("RGB", (512 * 3, 768 + 50), "white")
        draw = ImageDraw.Draw(sheet)
        for i, image in enumerate(images):
            sheet.paste(image.convert("RGB"), (i * 512, 50))
            draw.text((i * 512 + 12, 14), SCENES[i][0], fill="black")
        sheet.save(OUT / "contact_sheet.png")
        report["technical_pass"] = all(s["quality"]["passed"] and
                                       s["nsfw_content_detected"] is not True
                                       for s in report["scenes"])
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["failed_stage"] = stage
        report["technical_pass"] = False
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - began, 2)
        report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("ASTRA_STORY_REPORT: " + json.dumps(report), flush=True)
    if not report["technical_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
