# SDXL prompt conditioning audit for run 76

The request for one truck fits the standard 77-position CLIP sequence. Both the count instruction and the final ladder instruction survive text tokenization. Run 77 had already reproduced the repeated vehicles using the original FP32 VAE and the same saved latent. The evidence points to checking the inputs to denoising before spending another full image run.

## Replay of the exact prompt text

I reconstructed the CLIP vocabulary from the BPE merge table using OpenAI's byte-to-Unicode vocabulary construction. I decoded the table from the stable-diffusion.cpp clip_merges.hpp blob `5c0e8576c8b2da94c1f773babbf6c6913af0ccea`. Before using the replay as evidence, I matched **both** byte streams to the digests in the run-76 manifest for tokenizer and tokenizer_2.

| Resource | Bytes | SHA-256 |
| --- | ---: | --- |
| merges.txt | 524619 | 9fd691f7c8039210e0fced15865466c65820d09b63988b0174bfe25de299051a |
| Reconstructed sorted, indented UTF-8 vocab.json | 1059962 | e089ad92ba36837a0d31433e555c8f45fe601ab5c221d4f607ded32d9f7a4349 |

I lowercased and split the two ASCII prompts according to CLIP's letter/punctuation rules, applied ranked BPE merges within each token, looked up the IDs, and added the start and end IDs. The counts below are before padding. The runtime capture should check the padding values separately for each encoder.

| Input | Text | Tokens including boundaries | Remaining positions |
| --- | --- | ---: | ---: |
| Positive | One red toy fire engine, one vehicle only, centered in a single side-view composition on a white studio background, fully visible, with attached wheels and one roof ladder. | 37 | 40 |
| Negative | people, text, words, watermark, logo, blurry, deformed wheels, missing ladder | 21 | 56 |

Positive IDs: `49406, 637, 736, 5988, 1769, 5857, 267, 637, 5299, 1033, 267, 24584, 530, 320, 2688, 1145, 268, 1093, 17510, 525, 320, 1579, 3155, 5994, 267, 2401, 8626, 267, 593, 11038, 8025, 537, 637, 6449, 16637, 269, 49407`

Negative IDs: `49406, 1047, 267, 4160, 267, 2709, 267, 2505, 2110, 267, 5750, 267, 21977, 267, 561, 6528, 8025, 267, 3423, 16637, 49407`

This replay establishes the expected content IDs. The archived run saved the prompt, latent and spatial conditioning but did not capture the actual padded IDs or either encoder's output.

## Source trace

| Step | Finding |
| --- | --- |
| Benchmark call | The benchmark passes the positive and negative strings directly to the SDXL pipeline with guidance 7.5, the recorded native sizes and zero crops. |
| Text features | The pinned Diffusers implementation encodes both prompts, selects the penultimate hidden state from each text encoder and concatenates the feature dimensions. It selects the two-dimensional pooled output for the projected text input. |
| Guidance ordering | Diffusers concatenates negative then positive rows for sequence embeddings, pooled embeddings and size IDs. The OpenVINO UNet wrapper forwards the conditioning arrays to model inputs. |
| Native size | The OpenVINO SDXL helper concatenates original size, crop and target size. The benchmark recorded [1024, 1024, 0, 0, 1024, 1024] at preparation. |
| Runtime check still needed | The OpenVINO text wrapper enumerates hidden-state output names in exported graph output order. Diffusers indexes that list by position. A runtime trace can check the selected layer name and values for each encoder, and verify that the projected pooled output occupies the expected slot. The source trace alone gives no evidence of incorrect ordering. |

## Smallest remaining runtime check

Use this one positive/negative pair and the pinned source and export revisions. Start with the two padded token-ID arrays per tokenizer, including the end-token position. For each encoder in turn, record the selected OpenVINO output name and compare its tensor with the corresponding reference penultimate layer. For encoder two, also compare the projected pooled output. Record shapes, finite values, numerical differences, and whether positive and negative inputs give distinguishable outputs. Finally check concatenation order and time IDs at the denoiser input boundary.

This test needs only the text components on CPU. Keep the existing memory ceiling and manual dispatch. Numerical differences between INT8 and FP32 require interpretation. A correct ID sequence and plausible tensor shapes establish only part of the conditioning contract. This audit ran the token replay and source trace. The tensor comparison is pending.

The candidate stays review-only with `production_ready=false`, `approved=false`, `published=false` and human visual review required. Scene fidelity and character continuity still require separate evidence.

Sources: [run 76](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/41988573278), [reference decode](https://github.com/lokeshpuri9779-alt/media-utils/actions/runs/42034690654), [benchmark call](https://github.com/lokeshpuri9779-alt/media-utils/blob/c26da903fc75045deaa181f6ac10c26c9ec4ebe7/tools/experimental_sdxl_load.py#L243), [OpenAI tokenizer](https://github.com/openai/CLIP/blob/a1d071733d7111c9c014f024669f959182114e33/clip/simple_tokenizer.py), [Diffusers SDXL prompt encoding](https://github.com/huggingface/diffusers/blob/v0.39.0/src/diffusers/pipelines/stable_diffusion_xl/pipeline_stable_diffusion_xl.py#L283), [OpenVINO text encoder wrapper](https://github.com/huggingface/optimum-intel/blob/v2.2.0/optimum/intel/openvino/modeling_diffusion.py#L1242).
