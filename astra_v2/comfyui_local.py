"""Opt-in, loopback-only client for a locally running ComfyUI server.

This adapter submits trusted ComfyUI API-format workflows and reads job
metadata. It does not download, approve, register, or publish generated assets.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request


def enabled() -> bool:
    return os.getenv("ASTRA_COMFYUI_ENABLED") == "1"


def _base_url() -> str:
    raw = os.getenv("ASTRA_COMFYUI_URL", "http://127.0.0.1:8188").strip()
    parsed = urllib.parse.urlparse(raw)
    host = parsed.hostname
    loopback = False
    if host:
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host.lower() == "localhost"
    if (parsed.scheme != "http" or not loopback or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")):
        raise ValueError("ComfyUI URL must be a plain HTTP loopback origin")
    return raw.rstrip("/")


def _timeout() -> int:
    try:
        value = int(os.getenv("ASTRA_COMFYUI_TIMEOUT_SECONDS", "30"))
    except ValueError as exc:
        raise ValueError("Invalid ComfyUI timeout") from exc
    if not 5 <= value <= 300:
        raise ValueError("ComfyUI timeout must be between 5 and 300 seconds")
    return value


def _json_request(path: str, payload: dict | None = None):
    url = _base_url() + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, method="GET" if data is None else "POST",
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=_timeout()) as response:
            result = json.load(response)
    except urllib.error.URLError as exc:
        raise RuntimeError("Local ComfyUI service unavailable") from exc
    except TimeoutError as exc:
        raise RuntimeError("Local ComfyUI request timed out") from exc
    if not isinstance(result, dict):
        raise ValueError("ComfyUI returned an invalid JSON object")
    return result


def submit_workflow(workflow: dict, client_id: str = "astra-local") -> str:
    """Submit a trusted API-format workflow and return its ComfyUI prompt ID."""
    if not enabled():
        raise RuntimeError("Local ComfyUI integration is disabled")
    if not isinstance(workflow, dict) or not workflow:
        raise ValueError("ComfyUI workflow must be a non-empty object")
    if any(not isinstance(node, dict) for node in workflow.values()):
        raise ValueError("ComfyUI workflow nodes must be objects")
    if not isinstance(client_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", client_id):
        raise ValueError("Invalid ComfyUI client ID")
    result = _json_request("/prompt", {"prompt": workflow, "client_id": client_id})
    prompt_id = result.get("prompt_id")
    if not isinstance(prompt_id, str) or not re.fullmatch(r"[A-Fa-f0-9-]{8,80}", prompt_id):
        raise ValueError("ComfyUI did not return a valid prompt ID")
    return prompt_id


def get_history(prompt_id: str) -> dict:
    """Read job history metadata; generated files remain under local review."""
    if not isinstance(prompt_id, str) or not re.fullmatch(r"[A-Fa-f0-9-]{8,80}", prompt_id):
        raise ValueError("Invalid ComfyUI prompt ID")
    if not enabled():
        raise RuntimeError("Local ComfyUI integration is disabled")
    return _json_request("/history/" + prompt_id)
