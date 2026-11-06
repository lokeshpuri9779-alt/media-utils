# SDXL text encoders agree on the truck prompt

The OpenVINO export and its FP32 reference preserved the truck count instruction through tokenization, layer selection and guidance packing. Both produced closely aligned conditioning vectors for “one vehicle only.” The repeated-truck image from run 76 still fails ASTRA's single-object requirement. The effect of the measured vector differences on denoising is the remaining question.

[Manual CPU run 78](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/42192924660) · [Tested code](https://github.com/lokeshpuri9779-alt/media-utils/commit/a13775b0d1c91e402624eb00b9b98412ac411a85) · [Original image review](sdxl-native-review-41988573278.md) · [Reference VAE comparison](sdxl-reference-decode-42034690654.md)

## What ran

Run 78 replayed the exact positive and negative prompts from run 76, with the seed-42 starting noise, 1024×1024 size, zero crop and guidance scale 7.5. The job verified 4,100,871,135 bytes of pinned inputs. It used the Optimum text wrapper with the original OpenVINO CPU settings and the original FP32 Transformers text encoders. It loaded one encoder at a time. The pinned Diffusers SDXL pipeline selected and packed the outputs. A recorder intercepted the first U-Net call before it could make a prediction.

The worker completed in 82.79 seconds on an AMD EPYC 9V74 runner, with 2.80 GiB peak sampled process-tree RSS against a 12 GiB limit. All 32 offline tests passed in the live job. The worker executed zero denoising steps and generated zero images. The tensors come from this fresh replay. Run 76 archived the prompt and final latent, and used an AMD EPYC 7763 runner.

## Token and layer checks

- Both tokenizers reproduced all expected content IDs for both prompts. The positive prompt occupied 37 positions including boundaries and the negative occupied 21. The full 77-position padded arrays matched between backends. Each tokenizer preserved its own padding convention (49407 for encoder 1 and 0 for encoder 2).
- The export selected `hidden_states.11` of 13 outputs and `hidden_states.31` of 33 outputs. For each prompt those same layers gave the closest reference match through the end token. The second encoder supplied the projected pooled vector.
- The boundary arrays matched the corresponding per-encoder outputs exactly within each backend, including feature concatenation and negative-then-positive row order. Both time-ID rows equaled `[1024,1024,0,0,1024,1024]`.

## Numerical comparison

Relative error is the L2 norm of the export/reference difference divided by the reference norm. The phrase rows cover only the three relevant token positions and exclude special tokens and padding.

| Measured input | Relative error | Cosine similarity |
| --- | ---: | ---: |
| Combined sequence, shape 2×77×2048 | 0.647% | 0.999980 |
| Pooled prompts, shape 2×1280 | 1.396% | 0.999903 |
| Positive-minus-negative sequence | 3.010% | 0.999547 |
| Positive-minus-negative pooled vector | 1.505% | 0.999887 |
| “one vehicle only”, encoder 1 | 3.682% | 0.999324 |
| “one vehicle only”, encoder 2 | 2.999% | 0.999552 |

I independently recomputed boundary RMSE, relative error and cosine similarity from the archived tensors. Comparing the actual words as well as the entire tensor avoids letting padding or high-norm boundary tokens dominate the interpretation. These figures narrow the investigation for this reproducible prompt pair. Visual quality and cross-scene identity still require image evidence and human review.

## Smallest next check

Measure the first noise prediction with the same pinned OpenVINO U-Net twice, once for each saved set of conditioning tensors. Use identical scheduler-scaled seed-42 noise, timestep, size IDs and guidance. Compare the negative, positive and guided predictions before any scheduler update. This isolates the first-step response to the measured text differences and takes two forward passes with zero full renders. A material difference would justify testing its effect across the denoising trajectory. Close first-step predictions would shift attention to the denoiser and later steps. Object count still needs a completed image for assessment.

The text-only workflow requires explicit manual dispatch. The evidence records `approved=false`, `production_ready=false`, `published=false` and mandatory manual visual review. Automatic approval, production fallback, paid APIs and publishing are disabled.

## Reusable evidence

| File | SHA-256 |
| --- | --- |
| Original Actions ZIP, artifact 13490129575 | `5cb88c22a9c032eca3ec7604f25cd3a661e118fffbd54ff392554e462c6b26e5` |
| export-inputs.npz | `7a2162e015cbfeb287f6c79a0f1a59074790750658d85b5242ffadca096c38f0` |
| reference-inputs.npz | `451c083783cf31f432505f0dc0c49750ddd00cc1650b9348cf239a15569ff3af` |

The original archive digest matched GitHub's digest after download. It contains both tensor packs, token IDs, observed output names, per-component metrics, file hashes and run metadata.
