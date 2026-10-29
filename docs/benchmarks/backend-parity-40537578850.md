# CPU backend parity review

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40537578850

Code: `1e40a53d113cb02fa7633c5dec9dd789ff033a0f`. Artifact: `12749731856`, expires 2026-11-03. Original PNGs and the saved initial tensor were downloaded and their SHA-256 values verified against the report. Both original images were visually inspected.

## Result

Both backends rendered successfully with exit code 0. Both passed the technical pixel check. Both failed manual prompt fidelity: the requested single red toy fire truck on white became a large red truck-like vehicle plus a smaller red vehicle and a detached ladder/wheel-like object on teal. There are no obvious people. Character continuity was not tested.

The images have effectively the same composition and defects. Across RGB channels on the 0–255 scale: mean absolute difference 0.00296656, RMSE 0.05446616, maximum absolute difference 1. These describe backend agreement, not semantic quality.

| Backend | Setup | Inference | Process peak RSS |
| --- | --- | --- | --- |
| PyTorch CPU FP32 | 35.64 s | 195.12 s | 7,257,084 KiB |
| OpenVINO CPU FP32 | 71.73 s | 177.85 s | 9,418,196 KiB |

Single-run timings do not establish sustained throughput. OpenVINO ran second and could benefit from cached downloads.

## Matching conditions

Pinned SD1.5 model revision `451f4fe16113bff5a5d2269ed5ad43b0592e9a14`, identical prompt and empty negative prompt, 512x512, 20 steps, guidance 7.5, PNDM. Both received copies of one saved float32 initial tensor of shape (1,4,64,64). Recorded core package versions agree.

- Initial tensor bytes SHA-256: `e97f3de04c7c6ba86354db4402b91d4402ede9c72aabed29a96dd7d635a798ba`
- PyTorch PNG SHA-256: `878cb35cfb03d5d2dd5d534a12e6b119a8c2c0e824232d9138abfd92f23d30e9`
- OpenVINO PNG SHA-256: `876e9d2d69fc3cde543afeb1f18953c43c5604078c355c677106255b27e1e4da`

## Why GitHub reports failure

The final comparator compared the full scheduler dictionaries literally. The only difference was order in `_use_default_values`: [timestep_spacing, prediction_type] versus [prediction_type, timestep_spacing]. Actual scheduler settings matched. This caused `technical_pair_completed=false` and workflow exit 1 after both successful renders.

The comparator now sorts only that provenance list, preserving every actual scheduler setting and retaining the raw report configurations. Local regression checks on these recorded configs accept reordered metadata and reject changed prediction_type or steps_offset. The historical run and its report remain unchanged; no expensive generation rerun is needed to establish the observed image agreement.

## Decision and next validation

For this case, OpenVINO export/runtime is not the leading explanation for the semantic failure: native PyTorch reproduces it. This does not prove equivalence for every prompt or model. The accumulated evidence still does not establish a reliable free ASTRA image path.

Stop backend tuning for this failure. The smallest useful next generation test is a bounded prompt intervention on the existing OpenVINO runner: retain seed 42, model, scheduler, steps, dimensions and guidance; use a concise positive prompt specifying one coherent red toy fire engine, fully visible, centered on a white studio background, and an explicit negative prompt for multiple vehicles, detached parts, collage, text and colored background. Record both exact prompts. Compare against this saved baseline; this tests the prompt pair as a combined intervention, not either component independently. If it fails, do not expand the seed/step sweep. If it passes, repeat at seed 123 before a combined truck-and-school test. Character-continuity testing remains blocked until scene fidelity is demonstrated.

All outputs remain review-only: approved=false, production_ready=false, published=false, manual visual review required. No automatic approval, production fallback, paid API, publishing or main-branch integration was enabled.
