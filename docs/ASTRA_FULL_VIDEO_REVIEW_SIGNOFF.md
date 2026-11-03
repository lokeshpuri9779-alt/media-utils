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

## Trusted cross-run handoff: reviewer-managed Git branch

An independently authorized reviewer deposits exactly TWO non-secret documents on the dedicated branch `astra-video-reviews`. Do not put the signing private key, the MP4 or an unsigned claimed approval on this branch:

- `signed-reviews/<sha256-of-UTF8-content-id>/<sha256-of-exact-MP4>/packet.json` — the unmodified `.story-review.json` packet from the same preload run.
- `signed-reviews/<sha256-of-UTF8-content-id>/<sha256-of-exact-MP4>/signed-review.json` — the signed reviewer decision produced by the offline signing CLI.

Use all 64 lowercase hexadecimal characters for each directory hash. Stage and commit the pair from the *reviewer's* checkout of `astra-video-reviews`, not from an ASTRA rendering or publisher workflow. Protect the reviewer branch and keep the independent signing key off all GitHub runners. The repository branch may not exist until a reviewer creates it.

Reviewers can calculate the target directory on their trusted workstation after signing:

```bash
python - <<'PY'
import json, hashlib, shutil
from pathlib import Path
story = json.loads(Path('candidate.json').read_text(encoding='utf-8'))
id_sha = hashlib.sha256(story['content_id'].encode('utf-8')).hexdigest()
mp4_sha = hashlib.sha256(Path('video.mp4').read_bytes()).hexdigest()
directory = Path('signed-reviews') / id_sha / mp4_sha
directory.mkdir(parents=True, exist_ok=False)
shutil.copyfile('review.story-review.json', directory / 'packet.json')
shutil.copyfile('independent-review.json', directory / 'signed-review.json')
print('REVIEW_STAGING_PATH=' + str(directory))
PY
```

**Publisher operation:** The existing `ASTRA_REQUIRE_INDEPENDENT_VIDEO_REVIEW=1` switch controls strict verification. When switched on with neither explicit review file path set, the full-video verifier fetches `astra-video-reviews` read-only and looks for the hashed pair for the *actually selected* content ID and encoded MP4. It then verifies the Ed25519 signature using `ASTRA_SEMANTIC_REVIEW_PUBLIC_KEY` before the existing pre-upload boundary.

Missing branch, missing files, missing/untrusted public key, corrupt documents, changed video, or invalid signature all produce `not_verified` and block the selected fiction Short before YouTube reservation/upload. Git fetch success alone is never approval. Exactly one explicitly configured local review path fails closed rather than falling back to the branch.

When strict review is disabled, no reviewer branch is fetched and existing publishing behavior remains unchanged. **Do not enable the strict switch until a real independent reviewer and repeatable deposit process are ready**: without signed evidence, unsupervised fiction Shorts will pause. No paid API, extra production schedule, automated signing, or new publishing authorization is introduced.
