"""Optional Ollama-backed local JSON generation for ASTRA scripts.

The service is expected to listen on loopback. Model weights stay outside Git.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request


def _endpoint():
    raw = os.getenv("ASTRA_LOCAL_LLM_URL", "http://127.0.0.1:11434")
    parsed = urllib.parse.urlparse(raw)
    if (parsed.scheme != "http" or parsed.hostname not in
            ("127.0.0.1", "localhost", "::1") or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ValueError("Local LLM URL must use HTTP on loopback")
    return raw.rstrip("/") + "/api/chat"


def enabled():
    return os.getenv("ASTRA_LOCAL_LLM_ENABLED") == "1" and bool(
        os.getenv("ASTRA_LOCAL_LLM_MODEL", "qwen2.5:3b-instruct-q4_K_M").strip()
    )


def generate_json(prompt, schema):
    """Generate one schema-constrained JSON response from a local Ollama model."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Local LLM prompt is empty")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError("Local LLM requires an object JSON schema")
    model = os.getenv("ASTRA_LOCAL_LLM_MODEL", "qwen2.5:3b-instruct-q4_K_M").strip()
    if not model or len(model) > 120:
        raise ValueError("Invalid local LLM model name")
    try:
        timeout = int(os.getenv("ASTRA_LOCAL_LLM_TIMEOUT_SECONDS", "300"))
    except ValueError as exc:
        raise ValueError("Invalid local LLM timeout") from exc
    if not 10 <= timeout <= 1800:
        raise ValueError("Invalid local LLM timeout")
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "format": schema,
        "stream": False,
        "options": {"temperature": 0.9, "num_predict": 2400},
    }).encode("utf-8")
    request = urllib.request.Request(
        _endpoint(), data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except urllib.error.URLError as exc:
        raise RuntimeError("Local LLM service unavailable") from exc
    except TimeoutError as exc:
        raise RuntimeError("Local LLM generation timed out") from exc
    content = (result.get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Local LLM returned no content")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Local LLM returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("Local LLM response must be a JSON object")
    return data
