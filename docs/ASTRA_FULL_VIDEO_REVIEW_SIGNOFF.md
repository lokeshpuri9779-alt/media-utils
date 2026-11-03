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

## Prepare one reviewer-ready folder from existing Actions artifacts (offline)

GitHub Actions stores the producer's `astra-preloaded-<content_id>` package and its `astra-preload-story-review-<run_id>-<lane>` evidence as **two separate ZIP files**. Do not guess which review packet belongs to the video. Download both ZIPs from the same successful preload workflow run, then run this offline intake (requires only Python standard library):

```bash
python -m astra_v2.independent_review_bundle \
  --preload-zip ./astra-preloaded.zip \
  --visual-review-zip ./astra-preload-story-review.zip \
  --output-dir ./review-ready
```

The intake refuses mismatched content IDs, story beats, exact MP4 bytes, JPEG hashes, missing evidence, ambiguous packet matches, duplicate archive members, traversal/symlinks, corrupt provenance or pre-existing destinations. A reviewer ZIP can contain evidence for **other** candidates in the same lane: the intake picks only the uniquely matching packet by its `content_id` and verifies its actual bytes.

The resulting folder contains exactly `candidate.json`, `video.mp4`, `contact.jpg`, `review.story-review.json`, `completed-checklist.json` and `review-intake-status.json`. **All checklist boxes are initially false; no Ed25519 key, signature, approval or publishing action is created.** The reviewer must personally watch the complete MP4 and compare it against all four authored beats. The JPEG is only supporting evidence.

After genuine independent review, a separately authorized reviewer may fill the checklist, run the existing signing CLI against these filenames, and deposit the verified signed decision according to the trusted branch instructions. Publishing still requires the existing editorial, media and publication gates. This intake does not add network/API calls or GitHub Actions storage.

## Optional 24-frame human review timeline (no approval)

The existing original four-frame contact JPEG is not enough to establish that events actually happened. For fuller, **still unsigned** visual evidence, use the previously prepared `review-ready` folder:

```bash
python -m astra_v2.review_timeline --review-dir ./review-ready
```

This **offline** command requires local `ffmpeg`, `ffprobe` and Pillow (already in ASTRA's video environment). It reads the exact `candidate.json`, `video.mp4` and original `.story-review.json` packet, checks SHA-256 and all four narrated beats, then creates `timeline-24.jpg` and `timeline-24.json` without overwriting the original packet, MP4, checklist or signed decision.

Each of the four narrated beats gets six timestamps inferred from the previously recorded shot-midpoint times. If the source packet has no genuine increasing midpoint alignment, extraction fails instead of guessing equal quarters. These samples are **visual inspection aids**, not proof of correct depiction or a human review. Any decoder failure or mismatched identity fails closed.

The independent reviewer must still personally **watch the entire encoded MP4**, use the 24-frame timeline to flag potential omissions, and independently decide whether every checklist criterion holds. The tool cannot mark a checkbox true, sign a decision, configure branch protection, or publish a video. Do not add timeline-generated files to the signed evidence branch; that branch continues to carry only the original packet and independent signed decision.

## Optional decoded-pixel motion evidence (diagnostic only)

For a reviewer-ready folder containing the **existing** `timeline-24.jpg` and `timeline-24.json` from `astra_v2.review_timeline`, run:

```bash
python -m astra_v2.mp4_motion_evidence --review-dir ./review-ready
```

The read-only processor verifies the exact encoded `video.mp4`, candidate and review-packet identities and hashes, 24-frame JPEG hash, all four authored story beats, and the original narration-aligned sample timestamps. It creates *only* `motion-evidence.json` and `motion-heatmap.png` as unsigned evidence. It never changes checklists, signatures or existing video files.

For each story beat, the report measures the median fraction of changed grayscale pixels across five adjacent frame pairs in a **center-stage region**, and a distinct **side background-control region**. The heatmap shows changed center-stage pixels. Where the background is highly dynamic, the hint is `background_motion_confounded`; otherwise it reports a simple low-change hint or that some pixels changed, with **action still unverified**. All values are diagnostic approximations; no metric establishes object identity, character movement, continuous prop contact, physical action or causal story fidelity.

Weather, camera motion, subtitles, animated backgrounds, lighting, cropping and JPEG compression can bias the measurement. A moving puppet can have nonzero pixels even when the narrated action is wrong. The report explicitly leaves `narrated_action_verified`, `character_motion_verified`, `prop_contact_verified`, `complete_video_reviewed`, `publication_approval` and `reviewer_signature_created` false. **The authorized reviewer must still watch the complete encoded MP4 and evaluate each narrated action.** Do not place the heatmap or report on the signed reviewer branch; only the original packet and independently signed decision belong there.

## Optional marked subject/prop region displacement (human assistance only)

Automatic pixel changes cannot identify a character or prove prop contact. To compare **manually selected regions** in the actual, hash-bound 24-frame review sheet, generate a create-only blank template:

```bash
python -m astra_v2.annotated_object_motion --review-dir ./review-ready --create-template
```

An authorized reviewer or analyst can inspect `timeline-24.jpg`, enter visible **subject** and **prop** bounding boxes into `object-region-annotations.json`, and leave all boxes `null` where the region cannot be identified. Boxes are `[x_min, y_min, x_max, y_max]`, **normalized between 0 and 1 within each individual 250×444 image**, excluding the 34-pixel row header. Do not invent boxes merely to show contact. The template starts entirely empty and explicitly unapproved.

Then calculate geometry **offline**:

```bash
python -m astra_v2.annotated_object_motion --review-dir ./review-ready
```

The tool rechecks exact encoded MP4 hash, review packet, timeline JPEG and timestamp alignment before accepting the 24-frame annotations. It reports per-beat annotated center displacement, maximum observed span, rectangle separation and box overlap, and creates `object-region-evidence.json` and `object-region-overlay.png` without replacing any existing evidence.

**Important:** The tool does not locate or recognize subjects/props; it only measures user-supplied rectangles. **Box overlap does not demonstrate a real grasp, continuous object motion, or narrative action.** Sparse or missing annotations yield insufficient evidence, not approval. Changes to annotation files or forged full-review flags cannot create a signature. Every output retains `semantic_quality: not_verified` and `publication_approval: false`.

This evidence must NOT be treated as an independent human full-video signoff. The separately authorized reviewer still has to watch every frame of the complete MP4, document the individual beat findings, and sign only under the existing independent review protocol. This command uses no network service or paid model and changes no YouTube publishing workflow.
