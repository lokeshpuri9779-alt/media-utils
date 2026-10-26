# Offline smoke-test adapter (non-generative)

The unified orchestrator can run a deterministic offline smoke test against **eight existing scene JPGs**. This does not install or benchmark Stable Diffusion, prove character consistency, provide speech synthesis, or publish.

Prerequisites: Python, numpy, opencv-python, ffmpeg; place scene_01.jpg through scene_08.jpg in a local folder.

The adapter is in `astra_unified/demo_stage.py`. From an empty output directory, configure each ASTRA_*_CMD stage to call `python /absolute/path/to/astra_unified/demo_stage.py <stage> --asset-dir /absolute/path/to/scenes`. Then run `python /absolute/path/to/astra_unified/pipeline.py --output /absolute/path/to/output`. Leave ASTRA_PUBLISH_CMD unset; publishing remains disabled.

The adapter validates images technically, creates an eight-second motion slideshow, generates a quiet synthetic ambient tone, muxes audio, and checks 96 decoded frames at 12 fps. These tests are a transport/encoding proof only. The main ASTRA pipeline remains unchanged.
