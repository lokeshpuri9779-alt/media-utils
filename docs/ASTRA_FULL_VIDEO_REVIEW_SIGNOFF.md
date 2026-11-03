# ASTRA — Independent full-video review signoff

This is an **offline, reviewer-operated** handoff to the existing `astra_v2.semantic_video_gate.evaluate` publisher check. It does not make the renderer or four sampled JPEG frames a semantic reviewer, and it cannot publish.

## Required artifacts

Download **both** artifacts from the *same preload run/lane*: `astra-preloaded-<content_id>` contains `candidate.json` and `video.mp4`; `astra-preload-story-review-<run_id>-<lane>` contains the contact JPEG and `.story-review.json` packet. The human reviewer must watch the **entire original MP4**, compare all narrated identities, actions, props and consequences, and reject any inaccurate video. Four decoded frames are only supporting evidence.

If source artifacts are missing or do not match, do not sign. Do not synthesize approval or recreate an original review packet.

## Independent reviewer and checklist

An independently authorized human must hold a PEM Ed25519 private key **outside producer workflows and GitHub Actions**. The reviewer alone signs. Keep the private PEM owner-only (`chmod 600` on POSIX); do not commit, upload, or log the private key. The publisher only needs its base64-encoded 32-byte public key.

Create a JSON checklist with exactly `complete_video_reviewed` and `beat_checks`. Start with `complete_video_reviewed: false` and four ordered beat entries, each with `beat` 1–4 and all four booleans set to false: `character_visible`, `narrated_action_visible`, `visual_prompt_matches_video`, `setting_and_prop_continuity`. Only change these to true after independently watching the *complete MP4* and establishing each claim. **Never** make unsupported claims to obtain a signature.

## Offline command, once independently reviewed

```bash
python -m astra_v2.independent_video_review_signoff \
  --candidate ./candidate.json \
  --packet ./review.story-review.json \
  --mp4 ./video.mp4 \
  --contact-sheet ./review.jpg \
  --checklist ./completed-checklist.json \
  --private-key /secure/offline/reviewer-private.pem \
  --trusted-public-key ./trusted-reviewer-public.txt \
  --reviewer-id independent-qa-01 \
  --confirm-full-video-reviewed \
  --output ./independent-review.json
```

The CLI refuses unsigned, partial, mismatched or incomplete evidence. It binds its decision to the exact MP4, contact JPEG, storyboard inspection packet and story identity, then verifies its own output with the production Ed25519 review checker. This is cryptographic verification of an independent person's claim, **not** a computer-vision semantic pass or publisher approval.

## Publisher activation is intentionally separate

Existing `astra_v2/run.py` supports `ASTRA_SEMANTIC_REVIEW_PACKET`, `ASTRA_SEMANTIC_REVIEW_DECISION`, and `ASTRA_SEMANTIC_REVIEW_PUBLIC_KEY`. The workflow maps repository variables to those values, but setting a path **does not transfer files between GitHub Actions runs**. A separate trusted handoff of the signed record and original packet to the publisher runner is still required. The files must match the exact candidate/MP4 being considered.

Only after that handoff is ready, deliberately set `ASTRA_REQUIRE_INDEPENDENT_VIDEO_REVIEW=1` if full human review must be mandatory. Missing evidence then blocks fiction Shorts **before YouTube reservation and upload**. Enabling the flag without a reviewer process can pause unsupervised Shorts publishing. Other editorial and publication gates remain intact.

Unit tests use fake MP4 bytes and generated test-only keys. Passing those tests proves only input and cryptographic binding, **not** actual video semantic accuracy.
