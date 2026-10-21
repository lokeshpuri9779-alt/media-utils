# ASTRA immutable artifact storage

The local and S3 adapters implement the same `put(source)` / `verify(record)`
contract. Records contain an absolute URI, SHA-256 and exact byte length. The
package bridge consumes the existing `preload-package/` format. These components
archive bytes; they do not create editorial approval or publish to YouTube.

## Implemented

- `adaptive_artifact_store.ArtifactStore`: local immutable cache, absolute paths,
  size/hash verification, symlink rejection and atomic concurrent inserts.
- `adaptive_remote_store.S3ArtifactStore`: injected S3 client, content-addressed
  keys, conditional creation, bounded conflict retries and streaming downloads.
  Every remote reuse/write is verified against actual bytes. ETags and metadata
  are not treated as SHA-256 evidence. Authentication/permission failures and
  unsupported conditional writes are errors, never unconditional overwrites.
- `adaptive_package_archive.PackageArchive`: immutable manifest written after
  all members succeed. Binds `candidate.json`, `video.mp4`, `cover.jpg` and
  `cover_wide.jpg` by hash and size. Rejects unexpected paths, malformed metadata,
  mismatched video hashes and current publication-policy/media failures.
- Restore into a new directory stages all members, verifies them and reruns
  current media/policy checks before making the complete package available.
  Existing destinations are never replaced. Failed restores clean staging files.
- The existing preloader has an opt-in archive hook immediately after `prepare`.
  `ASTRA_REMOTE_ARCHIVE` defaults to disabled. No production workflow enables it,
  supplies new credentials or changes the publisher's selection/upload path.

The SDK is an optional dependency in
`integrations/requirements-artifact-storage.txt`. Fast CI installs it to validate
the real SDK request schema with a stubbed client; tests make no storage calls.

## Configured worker usage

Use an existing, privately configured bucket. This code does not provision cloud
resources, change bucket policy or choose a paid/free plan. A compatible endpoint
must support S3 conditional `PutObject` and SHA-256 checksums; compatibility is not
assumed merely from an S3-compatible label. Configure standard AWS SDK credentials
or an execution role outside the repository.

| Setting | Meaning |
| --- | --- |
| `ASTRA_ARTIFACT_S3_BUCKET` | Required existing bucket |
| `ASTRA_ARTIFACT_S3_ENDPOINT` | Optional HTTPS origin; absent uses AWS S3 |
| `ASTRA_ARTIFACT_S3_PREFIX` | Namespace, default `astra` |
| `AWS_DEFAULT_REGION` | Signing region, default `us-east-1` |
| `ASTRA_ARTIFACT_CACHE` | Producer cache directory, default `storage/artifacts` |
| `ASTRA_REMOTE_ARCHIVE` | Explicit `1` enables the producer hook |

The explicit CLI does not require the producer flag:

```bash
python -m pip install -r integrations/requirements-artifact-storage.txt
python -m astra_v2.adaptive_package_archive --cache storage/producer archive preload-package --receipt archive-receipt.json
python -m astra_v2.adaptive_package_archive --cache storage/consumer restore archive-receipt.json restored-package
```

Each command also needs the bucket/credentials configuration above. Restore uses
the normal `creative.inspect_video` check and therefore requires `ffprobe`.
Use different empty caches on separate workers for a live restore test. Receipts
are outside `preload-package/`, preserving the existing publisher's exact member
allowlist. The producer writes `preload-archive-receipt.json` and logs its manifest
reference. An enabled archive failure is visible as a producer failure; it never
silently reports that unpersisted media was archived.

Keep receipts in the eventual durable inventory/backup. This adapter provides no
mutable content-ID index, enumeration service or transactional publication queue;
a lost receipt is not automatically rediscovered. Multiple manifest versions may
refer to the same media. Hash equality proves byte identity, not human review,
producer trust, unique publication, copyright or continued policy eligibility.
Recorded provenance is descriptive, not an authenticated workflow attestation.

## Limits and deployment status

- Default object cap: 256 MiB. Existing video-package cap: 200 MiB; covers: 5 MiB
  each; candidate JSON: 1 MiB; manifest: 64 KiB. This is a single-object upload
  adapter, not multipart storage for arbitrarily large assets.
- Verified local cache hits can be reused without a network call.
  `S3ArtifactStore.verify(record, refresh=True)` explicitly rechecks remote bytes.
  A missing/corrupt remote object is never repaired by overwriting it.
- Interrupted writes may leave unreferenced objects. Retention/garbage collection
  is deliberately not automatic: it needs a durable reference index and backup
  policy before any deletion can be safe.
- No live backend, budget/retention policy, credentials or independent-run soak
  test was configured for this change. No production archiving is enabled.
- SQLite in `adaptive_queue` still coordinates only one shared filesystem.
  A remote transactional inventory/lease service and persisted manifest receipts
  remain required before independent publication workers can consume this archive.
- Publisher migration still needs authoritative editorial evidence, trusted
  producer verification, current renderer/freshness/novelty/history checks,
  transactional reservations and live YouTube confirmation. The bridge does not
  enqueue restored packages or turn them into approved uploads.
- OmniRoute review is unavailable in this workspace: plugin discovery returned no
  integration and no endpoint/model credentials were configured. No independent
  verdict is claimed. Provider selection and production deployment remain pending.

## Verification

```bash
python -m unittest discover -s tests -p 'test_adaptive_*.py' -v
```

Tests cover local/remote deduplication, concurrent independent caches, SDK request
validation, access denial, unsupported conditional writes, bounded conflicts,
corrupt/missing/truncated/oversized downloads, package round trips, policy/media
rejection, manifest/path tampering, partial uploads and non-overwriting restores.
These are offline tests, not evidence that a hosted backend has been deployed.

The remote protocol follows the primary API documentation:
[S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)
and [Boto3 PutObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html).
