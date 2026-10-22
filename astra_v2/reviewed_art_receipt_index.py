"""Publish and consume a content-addressed index of approved-art receipts.

The index itself is an immutable object. Consumers must be given its exact
SHA-256 receipt; a mutable 'latest' pointer cannot silently select artwork.
"""
import json
import re
from pathlib import Path

from astra_v2.adaptive_artifact_store import validate_record
from astra_v2.remote_reviewed_art import SCHEMA as ART_SCHEMA
from astra_v2.reviewed_art_bundle import MAX_BUNDLE_BYTES

INDEX_SCHEMA = "astra.reviewed-art.index.v1"


def _validate_receipt(receipt):
    if not isinstance(receipt, dict) or receipt.get("schema") != ART_SCHEMA or receipt.get("publication_triggered") is not False:
        raise ValueError("invalid_art_receipt")
    validate_record(receipt.get("bundle"), MAX_BUNDLE_BYTES)
    return receipt


def publish_index(receipts, store):
    if not isinstance(receipts, dict) or not receipts or len(receipts) > 500:
        raise ValueError("invalid_art_receipt_index")
    entries = {}
    for content_id, receipt in sorted(receipts.items()):
        if not isinstance(content_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", content_id):
            raise ValueError("invalid_art_content_id")
        entries[content_id] = _validate_receipt(receipt)
    import tempfile
    with tempfile.TemporaryDirectory(prefix="astra-art-index-") as temp:
        path = Path(temp) / "index.json"
        path.write_text(json.dumps({"schema": INDEX_SCHEMA, "entries": entries}, sort_keys=True), encoding="utf-8")
        record = store.put(path)
    validate_record(record, 256 * 1024)
    return {"schema": INDEX_SCHEMA, "index": record, "publication_triggered": False}


def lookup(index_receipt, content_id, store):
    if not isinstance(index_receipt, dict) or index_receipt.get("schema") != INDEX_SCHEMA or index_receipt.get("publication_triggered") is not False:
        raise ValueError("invalid_art_index_receipt")
    validate_record(index_receipt.get("index"), 256 * 1024)
    payload = store.verify(index_receipt["index"])
    if payload.stat().st_size > 256 * 1024:
        raise ValueError("art_index_too_large")
    data = json.loads(payload.read_text(encoding="utf-8"))
    if data.get("schema") != INDEX_SCHEMA or not isinstance(data.get("entries"), dict):
        raise ValueError("invalid_art_index")
    receipt = data["entries"].get(content_id)
    if receipt is None:
        return None
    return _validate_receipt(receipt)
