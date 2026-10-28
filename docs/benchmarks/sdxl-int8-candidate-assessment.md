# Preconverted SDXL INT8 candidate assessment

Assessment date: 2026-10-28. Review only; no model binaries downloaded or benchmark dispatched during this assessment.

## Candidate and provenance

Model: OpenVINO/stable-diffusion-xl-base-1.0-int8-ov
Pinned revision: d54e5b43fcb6b4b358f3a134269115d3fcb3eb25
Source: https://huggingface.co/OpenVINO/stable-diffusion-xl-base-1.0-int8-ov
Pinned files: https://huggingface.co/OpenVINO/stable-diffusion-xl-base-1.0-int8-ov/tree/d54e5b43fcb6b4b358f3a134269115d3fcb3eb25

The OpenVINO publisher identifies stabilityai/stable-diffusion-xl-base-1.0 as the original model and NNCF weight compression with INT8_ASYM, ratio 1.0. Metadata identifies the relation as quantized and license as openrail++. The model card links the original model's license and restrictions. The package is traceable to its publisher and immutable artifact revision; an exact original checkpoint SHA and complete reproducible conversion environment are not supplied by the inspected card/model index. Do not claim equivalence to our previously pinned FP32 checkpoint.

The model card documents OpenVINO >=2025.2.0 and Optimum Intel >=1.26.0 and includes a CPU inference example. Our existing 2026.4.1/2.2.0 pins satisfy those stated minima, but runtime compatibility still needs validation.

## Size and precision inspection

Hugging Face API metadata reported 3,506,359,216 bytes across the full snapshot (about 3.27 GiB), including auxiliary tokenizer graphs, VAE encoder, and an unnecessary duplicate notebook checkpoint XML.

| Component binary | Bytes |
| --- | ---: |
| text_encoder/openvino_model.bin | 123822587 |
| text_encoder_2/openvino_model.bin | 697523959 |
| unet/openvino_model.bin | 2576698520 |
| vae_decoder/openvino_model.bin | 49647853 |
| vae_encoder/openvino_model.bin | 34282956 |

Inspected the five pinned component XML graphs, without downloading weight binaries. All contain predominantly u8 constant storage, plus f16/f32 constants and integer shape metadata. For example, the UNet references 2,567,374,724 bytes of u8 constants, 2,988,808 bytes f16, and 6,334,608 bytes f32. This supports the weight-compression description; it does not establish all-INT8 arithmetic, quantized activations, or peak resident RAM.

The model index declares StableDiffusionXLPipeline with EulerDiscreteScheduler. Treat this as a new candidate rather than a controlled one-variable comparison to the SD1.5 PNDM tests.

## Decision and next validation

Eligible for one bounded CPU load-and-compile test, not image generation or production use. The much smaller stored package justifies this test; package size is not runtime memory.

Use pinned files with verified advertised SHA256 hashes, export=false, CPU only, no additional quantization, no remote model code, batch one, and static 1024x1024 target shape. Fetch only required files. Log actual package versions, selected runtime precision settings, available RAM/disk before download, stage times, and peak process-tree RSS separately for loading and compilation.

Proposed limits: one attempt, 10 minutes for model load/compile after download, terminate at 12 GiB process-tree RSS or less than 2 GiB system available RAM. Use a supervisor and retain a failure report on timeout/memory-limit/compatibility errors. These are experiment budgets, not claims about required resources. Do not render in this test. Do not increase runner tier or incur paid services.

If loading and compilation pass, the next separate validation is one fixed-seed, native-resolution toy-fire-engine image with the previously recorded positive/negative prompt and explicit manual checks for one recognizable vehicle, coherent attached wheels/ladder, white background, and absence of text/people. A single semantic pass would still not establish reliability or character continuity.

Keep approved=false, production_ready=false, published=false, manual_visual_review_required=true. No automatic approval, production fallback, paid APIs, publishing, or merge.
