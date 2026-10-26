# Offline smoke test — unified ASTRA

This is a **non-generative** technical pipeline check using eight existing storyboard JPG files. It does not prove AI generation, consistent characters, narration, or YouTube publishing.

Prerequisites: Python, numpy, opencv-python, ffmpeg, and eight scene images named `scene_01.jpg` through `scene_08.jpg` in an asset folder.

From the repository root:

```bash
export REPO_ROOT="$PWD"
export ASSET_DIR="/absolute/path/to/scene_images"
export OUT_DIR="/absolute/path/to/smoke_output"
for stage in STORY IMAGES CONSISTENCY ANIMATION NARRATION EDIT QUALITY; do
  export "ASTRA_${stage}_CMD=python $REPO_ROOT/astra_unified/demo_stage.py ${stage,,} $ASSET_DIR"
done
python astra_unified/pipeline.py --output "$OUT_DIR"
```

The adapter runs seven stages, checks that all eight JPGs decode, creates an 8-second 360×640 slideshow at 12 fps, adds a **silent placeholder audio track**, and verifies 96 decoded video frames. It intentionally does not perform speech synthesis or real character animation. Publishing remains disabled unless explicitly opted in and configured.

Run unit tests with `python -m unittest discover -s astra_unified -p 'test_*.py'`. GitHub Actions CI is not enabled by this change. Main ASTRA is unchanged.
