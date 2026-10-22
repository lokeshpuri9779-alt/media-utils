"""Immutable remote transport for independently approved artwork bundles.

A receipt proves byte identity, not editorial approval or publication eligibility.
"""
import argparse
import json
from pathlib import Path

from astra_v2.adaptive_artifact_store import validate_record
from astra_v2.reviewed_art_bundle import MAX_BUNDLE_BYTES, install_bundle

SCHEMA = "astra.reviewed-art.bundle.v1"


def upload(archive, store):
    archive = Path(archive)
    # Validate the actual archive contents before remote persistence.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="astra-reviewed-art-validate-") as temp:
        install_bundle(archive, Path(temp) / "checked")
    record = store.put(archive)
    validate_record(record, MAX_BUNDLE_BYTES)
    return {"schema": SCHEMA, "bundle": record, "publication_triggered": False}


def restore(receipt, store, destination):
    if (not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA
            or receipt.get("publication_triggered") is not False):
        raise ValueError("invalid_reviewed_art_receipt")
    validate_record(receipt.get("bundle"), MAX_BUNDLE_BYTES)
    archive = store.verify(receipt["bundle"])
    return install_bundle(archive, destination)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", default="storage/artifacts")
    commands = parser.add_subparsers(dest="command", required=True)
    producer = commands.add_parser("upload")
    producer.add_argument("archive")
    producer.add_argument("receipt")
    consumer = commands.add_parser("restore")
    consumer.add_argument("receipt")
    consumer.add_argument("destination")
    args = parser.parse_args(argv)
    from astra_v2.adaptive_remote_store import store_from_environment
    store = store_from_environment(args.cache)
    if args.command == "upload":
        receipt = upload(args.archive, store)
        Path(args.receipt).write_text(json.dumps(receipt, sort_keys=True, indent=2))
        print("ASTRA_REVIEWED_ART_REMOTE_RECEIPT=" + json.dumps(receipt, sort_keys=True))
    else:
        receipt = json.loads(Path(args.receipt).read_text())
        manifest = restore(receipt, store, args.destination)
        print("ASTRA_REVIEWED_ART_MANIFEST=" + str(manifest))


if __name__ == "__main__":
    main()
