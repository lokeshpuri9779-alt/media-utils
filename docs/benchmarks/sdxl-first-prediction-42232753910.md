# First denoiser prediction with two sets of text vectors

Swapping the exported text vectors for their FP32 reference counterparts changed the first guided noise prediction by **0.07067%** in relative L2 norm. The prompt-dependent component (positive prediction minus negative prediction) changed by **0.86296%**. Both calls used the same compiled INT8 OpenVINO U-Net. This result measures a small initial change for the seed-42 truck prompt. Its effect on object count requires a completed image.

[Run 79](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/42232753910) · [Tested code](https://github.com/lokeshpuri9779-alt/media-utils/commit/a0cce528d547fbffb6e5efd221c609360709c6b6) · [Run-78 source tensors](sdxl-text-review-42192924660.md) · [Run-76 visual assessment](sdxl-native-review-41988573278.md)

| Compared output | Relative L2 difference | Cosine similarity |
| --- | ---: | ---: |
| Negative prompt | 0.00994% | 0.999999995 |
| Positive prompt | 0.00407% | 0.999999999 |
| Positive minus negative | 0.86296% | 0.999967894 |
| Guided prediction | 0.07067% | 0.999999750 |
| Implied clean latent | 0.70073% | 0.999978876 |

Each difference is normalized by the norm of the corresponding output with reference text conditioning. Guidance used negative + 7.5 × (positive − negative). The implied clean latent used the Euler epsilon formula at the initial sigma. It is an arithmetic estimate at the first timestep, with zero scheduler updates and zero images generated.

The worker verified both input packs and the pinned model files, compiled the U-Net once, and ran two calls on the same 1024×1024 schedule, starting noise, scaled sample and size IDs. The first of the 20 scheduled timesteps was 951 (sigma 11.0283355713). The calls took 86.46 and 86.51 seconds. Total supervised time was 260.81 seconds and peak sampled process-tree RSS was 8.30 GiB against the 12 GiB cap. All 34 offline guardrail tests passed in the live job.

The downloaded archive matched GitHub's digest `sha256:da00301795cc405c26788225f92358b24c0e45b1d7fcde7a8f30300bccaec136`. All saved array hashes matched. Independent calculations using the raw prediction rows reproduced the RMSE, relative L2, cosine and maximum absolute difference for all five rows. The initial latent also reproduced the shared scaled-sample SHA-256 `feaff25c7684b1281f1cba182d9c71494c2f14762b8341ee3ec9daecd9466419`.

For a direct visual check, reconstruct the first Euler update from `initial-latent.npy` and the guided rows of `reference-prediction.npy`, then complete the remaining 19 calls with the verified run-78 reference pack and decode once. Keep the original seed, model revision, scheduler, guidance and resource limits. Manually compare the resulting truck count, framing, silhouette, wheels and roof ladder with the archived run-76 image. School scenes and character continuity require separate evidence.

The benchmark is review-only with `approved=false`, `production_ready=false`, `published=false` and mandatory manual visual review. Paid APIs, production fallback, automatic approval and publishing are disabled.
