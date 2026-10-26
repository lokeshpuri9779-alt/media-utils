# ASTRA offline smoke test

This test checks the seven-stage video transport pipeline. It **reuses eight existing storyboard images**, creates a simple slideshow and silent audio, and does **not** establish AI image generation, speech synthesis, or character consistency.

## Single-command run

Requirements: Python with numpy and opencv-python, and FFmpeg installed.

```bash
python astra_unified/run_smoke.py \
  --assets /absolute/path/to/eight_scene_jpgs \
  --output /absolute/path/to/smoke_output
```

The assets directory must contain `scene_01.jpg` through `scene_08.jpg`. The launcher configures all seven stage commands internally, runs `pipeline.py`, and does not enable publishing.

Expected outputs: `pilot.mp4`, `qa.json`, `run_report.json`, plus intermediate files. Check `run_report.json` and verify all seven stages passed, publishing was skipped, and `qa.json` reports 96 decoded frames.

## Production distinction

The smoke launcher intentionally does not use `--production`. A passed smoke test must never be interpreted as proof that real AI models ran. The separate `offline_sd15.py` adapter requires local model weights and dependencies; `offline_tts.py` requires an installed speech engine. Neither is automatically invoked by the smoke launcher.

Unit tests: `python -m unittest discover -s astra_unified -p 'test_*.py'`.

No GitHub Actions CI is enabled by this change, and main ASTRA remains unchanged.
