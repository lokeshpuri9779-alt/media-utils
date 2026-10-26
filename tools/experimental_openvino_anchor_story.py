"""Experimental anchor-conditioned lighthouse continuity test. Never publishes."""
import gc
import json
import resource
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

OUT = Path("artifacts/experimental-openvino/anchor-story")
ANCHOR = Path("artifacts/anchor-input/01_sunset.png")
MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"
SUBJECT = ("the very same short red-and-white coastal lighthouse, identical tower shape, "
           "roof, lantern, rocks and horizon from the provided reference image, "
           "coherent illustrated storybook painting, complete lighthouse visible")
SCENES = (
    ("02_storm", "a rainstorm, dark clouds and crashing waves, beacon illuminated"),
    ("03_after", "a calm morning after the storm, clear blue sky and still ocean"),
)
NEGATIVE = ("different lighthouse, different tower, second lighthouse, duplicate tower, "
            "floating objects, cropped building, disjointed architecture, letters, watermark")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"engine": "OpenVINO image-to-image CPU FP32",
              "model": MODEL, "anchor_run": 40371027354,
              "strength": 0.42, "seed": 42, "steps": 16,
              "published": False, "approved": False, "production_ready": False,
              "semantic_match": "manual_review_required",
              "character_continuity": "manual_review_required", "scenes": []}
    started = time.monotonic()
    stage = "anchor_check"
    try:
        if not ANCHOR.is_file():
            raise FileNotFoundError("Anchor PNG not downloaded")
        anchor = Image.open(ANCHOR).convert("RGB")
        if anchor.size != (512, 768):
            raise ValueError("Anchor dimensions invalid")
        from optimum.intel import OVStableDiffusionImg2ImgPipeline
        import torch
        from astra_v2.omniroute_image_assets import image_quality_report
        stage = "load_img2img"
        print("ASTRA_ANCHOR_STAGE: load_img2img", flush=True)
        pipe = OVStableDiffusionImg2ImgPipeline.from_pretrained(
            MODEL, export=True, device="CPU", compile=False, load_in_8bit=False,
            ov_config={"INFERENCE_PRECISION_HINT": "f32"})
        stage = "compile"
        print("ASTRA_ANCHOR_STAGE: compile", flush=True)
        pipe.reshape(batch_size=1, height=768, width=512, num_images_per_prompt=1)
        pipe.compile()
        frames = [anchor]
        anchor.save(OUT / "01_anchor_sunset.png")
        for slug, condition in SCENES:
            stage = "render_" + slug
            print("ASTRA_ANCHOR_STAGE: " + stage, flush=True)
            scene_start = time.monotonic()
            result = pipe(
                SUBJECT + ", now in " + condition, image=anchor.copy(),
                negative_prompt=NEGATIVE, strength=0.42,
                num_inference_steps=16, guidance_scale=8.0,
                generator=torch.Generator(device="cpu").manual_seed(42))
            img = result.images[0]
            if not isinstance(img, Image.Image):
                raise ValueError("No PIL image returned")
            img = img.convert("RGB")
            if img.size != (512, 768):
                raise ValueError("Result dimensions invalid")
            output = OUT / (slug + ".png")
            img.save(output)
            quality = image_quality_report(output.read_bytes(), "scene")
            nsfw = getattr(result, "nsfw_content_detected", None)
            if nsfw is not None:
                nsfw = bool(nsfw[0])
            delta = ImageStat.Stat(ImageChops.difference(anchor, img)).mean
            record = {"id": slug, "quality": quality,
                      "anchor_mean_absolute_rgb_difference": round(sum(delta) / 3, 2),
                      "nsfw_content_detected": nsfw, "png": str(output),
                      "elapsed_seconds": round(time.monotonic() - scene_start, 2)}
            report["scenes"].append(record)
            print("ASTRA_ANCHOR_SCENE: " + json.dumps(record), flush=True)
            frames.append(img)
        stage = "contact_sheet"
        sheet = Image.new("RGB", (512 * 3, 818), "white")
        draw = ImageDraw.Draw(sheet)
        for i, frame in enumerate(frames):
            sheet.paste(frame, (i * 512, 50))
            draw.text((i * 512 + 12, 14),
                      ("01_anchor_sunset", "02_storm", "03_after")[i],
                      fill="black")
        sheet.save(OUT / "contact_sheet.png")
        report["technical_pass"] = (
            len(report["scenes"]) == 2
            and all(s["quality"]["passed"] and s["nsfw_content_detected"] is not True
                    for s in report["scenes"]))
        del pipe
        gc.collect()
    except Exception as exc:
        report["failed_stage"] = stage
        report["error_type"] = type(exc).__name__
        report["technical_pass"] = False
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("ASTRA_ANCHOR_REPORT: " + json.dumps(report), flush=True)
    if not report["technical_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
