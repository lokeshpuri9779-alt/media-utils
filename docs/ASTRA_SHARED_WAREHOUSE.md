# Shared receipts and package reservations

`astra_v2.adaptive_shared_queue.PostgresWarehouse` supplies a remote receipt index
and a transactional queue through an injected Psycopg connection factory. It
complements the S3 artifact adapter; it does not replace the current publisher.

## State and guarantees

| Operation | Stored effect |
| --- | --- |
| `save_receipt` | Immutable `(namespace, content ID, manifest SHA)` reference; no queue entry |
| `list_receipts` / `get_receipt` | Recover exact manifest versions from another worker |
| `enqueue` | One immutable queue entry per namespace/content ID, referencing an existing receipt plus previously validated editorial/QA evidence digests |
| `claim` | Atomic `ready` to `reserved`, with a random lease token and server-clock expiry |
| `renew` | Extend a live reservation with its matching token; cannot revive an expired one |
| `confirm` | Record a supplied verified YouTube ID/evidence digest; identical retries are idempotent |
| `expired` | List uncertain reservations for reconciliation; never automatically requeue |
| `counts` | Current ready/reserved/published/expired counts for adaptive planning |

Claims lock only the selected row with `FOR UPDATE SKIP LOCKED`, allowing other
workers to proceed. Transactions cover each operation, including receipt checks,
queue admission and confirmation. Namespace-scoped uniqueness prevents two queue
rows from confirming the same YouTube ID. A content ID already admitted/published
cannot silently switch to a new manifest or new evidence, and admission retries
never reset its state. Receipt listing uses a stable, bounded cursor and requires
an explicit manifest SHA for restoration rather than guessing the newest version.

The trusted caller still validates the actual editorial decision, QA report,
producer provenance and complete publication history. These methods validate
evidence-reference syntax; a hash alone is not proof of approval. Likewise,
`confirm` stores evidence from an authoritative YouTube verifier, but does not call
YouTube. Atomic database operations do not make an external upload exactly-once.

If a worker fails before commit, the claim rolls back. If the claim commits but
its acknowledgment is lost, the package remains reserved. Expiry does not prove
that an upload failed. There is no automatic release/requeue or reconciliation
override in this implementation; a verified reconciliation adapter remains
necessary before publication adoption.

## Configuration and commands

Install `integrations/requirements-shared-warehouse.txt` only where this backend
is explicitly used. Supply `ASTRA_WAREHOUSE_DATABASE_URL` through the execution
environment, never a committed file. Remote database URLs require
`sslmode=verify-full` and a valid trusted certificate configuration. The namespace
is selected with `ASTRA_WAREHOUSE_NAMESPACE` (default `astra`); use a stable
namespace per channel. The constructor/factory does not connect or migrate until
an operation is explicitly invoked.

Initialize the versioned tables once in an existing configured database:

```bash
python -m pip install -r integrations/requirements-shared-warehouse.txt
python -m astra_v2.adaptive_shared_queue initialize
```

Initialization only creates the two versioned tables and their indexes if absent.
It never drops or rewrites prior publisher/state data. Subsequent schema versions
need a separately reviewed migration. Worker operations use bounded statement and
lock timeouts. No cloud account, database server, bucket or credential is created.

For automatic receipt indexing after successful remote archiving, explicitly set
`ASTRA_RECEIPT_INDEX=postgres` as well as the S3 archive configuration. The existing
producer still requires `ASTRA_REMOTE_ARCHIVE=1`. This indexes receipts only: no
approved queue entry, lease or publication is created. A database failure is
reported after the local receipt is written, allowing the same receipt to be
registered again without duplication:

```bash
python -m astra_v2.adaptive_shared_queue register preload-archive-receipt.json
python -m astra_v2.adaptive_shared_queue list --limit 100
python -m astra_v2.adaptive_shared_queue counts
```

Use the returned content ID and manifest SHA to restore with a fresh object cache:

```bash
python -m astra_v2.adaptive_package_archive --cache storage/consumer restore-indexed CONTENT_ID MANIFEST_SHA restored-package
```

Continue a receipt listing with `list --after CONTENT_ID MANIFEST_SHA`, using the
returned `next_cursor`. The command-line interface intentionally exposes no
approval, enqueue, claim or YouTube publication commands.

## Validation and deployment boundary

Fast CI supplies a disposable PostgreSQL 16 service and runs the integration tests
through `ASTRA_TEST_POSTGRES_DSN`. That URL/password is for CI's temporary test
database only. Tests use isolated namespaces and remove only their own rows.
Locally, database integration tests explicitly skip when that test variable is
absent; this is never counted as successful database verification.

Integration coverage includes concurrent admissions, 24 claims by eight independent
connections against 16 packages, locked-row skipping, immutable versions,
pagination, foreign-key rollback, lease renewal/expiry, confirmation idempotency,
video-ID uniqueness, failure before commit, acknowledgment loss after commit and
recovering an archived package without the producer's local receipt. Object
storage in these tests is simulated; PostgreSQL is real.

Production activation remains pending a configured persistent database and object
bucket, credentials, retention/backups, an authoritative admission/reconciliation
bridge and a cross-run restore/soak check. No production workflow supplies these
settings. Current YouTube selection/upload code and its safeguards remain intact.
OmniRoute review remains unavailable; no provider verdict is invented.

Primary protocol references:
[PostgreSQL SELECT locking](https://www.postgresql.org/docs/current/sql-select.html)
and [Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).
