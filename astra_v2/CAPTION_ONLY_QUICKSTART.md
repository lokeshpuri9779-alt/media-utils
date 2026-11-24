# ASTRA caption-only Shorts quick start

This path creates **narration + timed captions only**. It does not create animations, illustrations, stock footage, music, or publish to YouTube.

## Runtime

- Python 3.11 recommended
- FFmpeg is supplied by `imageio-ffmpeg`
- Kokoro ONNX voice model is loaded through the existing `studio_renderer.voice_engine()` cache. If the model files are not already cached, the existing Studio asset helper downloads and checksum-verifies them from the upstream release.
- No Gemini, vidIQ, or paid API is called by the renderer.

Install the focused dependencies from the repository root:

```bash
python -m pip install -r requirements-caption-only.txt
```

## Render a review-only story candidate

First create a seven-scene candidate JSON using the existing review-only generator/queue. The candidate must contain the seven `performance_scenes` roles in order (`hook`, `stakes`, `attempt`, `setback`, `discovery`, `climax`, `payoff`) and a story-specific `question` for the spoken engagement CTA.

Then run:

```bash
python -m astra_v2.caption_short_pipeline --candidate candidate.json --output output/rayvan-short.mp4
```

The renderer synthesizes the scene narration with Kokoro, appends the engagement question, creates phrase-synchronized captions, and encodes a vertical 1080x1920 MP4. Actual audio duration must pass the existing 28–40 second Shorts contract. A decode check runs on the finished MP4.

## Outputs

- `rayvan-short.mp4` — narration with static, timed captions
- `rayvan-short.captions.json` — phrase timing manifest
- `rayvan-short.review.json` — review report

The report always leaves `approved`, `production_ready`, and `published` false. This CLI does not upload, schedule, or publish.

## Generate a candidate

The current story generator is a separate, optional Gemini-backed step. It requires `ASTRA_GEMINI_ENABLED=1` and `GEMINI_API_KEY`; it is disabled by default and may incur provider charges. Do not enable it unless the API key, model, and billing are explicitly approved. The caption renderer itself makes no Gemini calls.

## Current limitation

This is a local, manually invoked production command, not yet a scheduled unattended service. It needs a machine with Python and the Kokoro model cache available while rendering. No 24/7 cloud runner or automatic public publishing is configured.
