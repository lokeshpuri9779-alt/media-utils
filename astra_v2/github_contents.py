"""Read JSON files through GitHub's Contents API, including blobs over 1 MiB."""

import base64
import json
from typing import Callable, Any


def decode_json_contents_file(metadata: dict[str, Any], api_get: Callable[[str], dict[str, Any]]) -> Any:
    """Decode a Contents API response, falling back to the Git Blobs API.

    GitHub omits the inline `content` field for sufficiently large files.
    The blob endpoint returns the full base64 payload for the same object.
    """
    encoded = metadata.get("content")
    if metadata.get("encoding") == "base64" and isinstance(encoded, str) and encoded.strip():
        raw = base64.b64decode(encoded)
    else:
        sha = metadata.get("sha")
        if not isinstance(sha, str) or not sha:
            raise ValueError("Contents API response has neither inline content nor a blob SHA")
        blob = api_get(f"git/blobs/{sha}")
        if blob.get("encoding") != "base64" or not isinstance(blob.get("content"), str):
            raise ValueError("Git Blobs API did not return base64 content")
        raw = base64.b64decode(blob["content"])
    return json.loads(raw.decode("utf-8"))
