# SDXL FP32 resource screening

Run: https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/40692592177
Code: dc5939a7bcb50f329c97222ca56bf8ca8fd96948
Artifact: 12818275469, astra-sdxl-resource-40692592177
Model: stabilityai/stable-diffusion-xl-base-1.0
Revision: 462165984030d82259a11f4367a4eed129e94a7b

The metadata-only job completed successfully in 7 seconds (11-second workflow). The image benchmark job was skipped. Success means the resource report was produced, not that SDXL passed feasibility.

| Measurement | Bytes |
| --- | ---: |
| Four FP32 component files | 13875688436 |
| Host total RAM | 16766414848 |
| Effective available RAM | 15358529536 |
| Required available RAM screening budget | 18170655732 |
| Free disk | 92034150400 |
| Required disk screening budget | 29898860520 |

Result: blocked_before_download, insufficient_available_ram_for_fp32_screening_budget. Available RAM was 14.30 GiB versus 16.92 GiB screening requirement. Disk passed.

The RAM budget is component weight size plus a deliberately chosen 4 GiB working reserve. The disk budget allows source and exported weights plus 2 GiB. These are screening policies, not measured loading or inference requirements. No weight download, model load, export, inference, or image generation occurred. Peak loading memory remains null. This is not an observed OOM and does not prove SDXL cannot run with another precision or loading strategy.

Boundary tests covered RAM-only rejection, disk-only rejection, both rejections, and exact-threshold acceptance. ASTRA Fast CI for the code commit also passed (40581524549).

## Decision and smallest next validation

Do not attempt the current direct FP32 export route on this runner. Assess one pinned, preconverted lower-memory SDXL package from a traceable source: verify base-model provenance, license, actual component precision/compression, and total download size before considering a bounded CPU load test. Do not silently enable the exporter's automatic INT8 compression. A new precision is a separate candidate and needs its own semantic review.

No reliable free image path is established. Scene fidelity and character consistency remain unverified for SDXL. Keep approved=false, production_ready=false, published=false, manual_visual_review_required=true. No production fallback, paid APIs, automatic approval, or publishing is enabled.
