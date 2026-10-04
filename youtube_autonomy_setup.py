from __future__ import annotations

"""One-time local authorization helper for Astra's owner-only YouTube features.

This file never commits credentials. It either installs the refresh token into
GitHub with the authenticated `gh` CLI or stores it under ~/.astra with
owner-only permissions for manual secret installation.
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

REPO = "lokeshpuri9779-alt/media-utils"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
FULL_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def _find_json(explicit: str | None, names: list[str]) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    for name in names:
        candidates.extend([Path(name), Path("secrets") / name])
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("Could not find " + " or ".join(names))


def _client(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    config = raw.get("installed") or raw.get("web")
    if not isinstance(config, dict):
        raise ValueError("OAuth client JSON has no installed/web configuration")
    if not config.get("client_id") or not config.get("client_secret"):
        raise ValueError("OAuth client JSON is missing client_id/client_secret")
    return config


def _safe_store(name: str, value: str) -> Path:
    folder = Path.home() / ".astra"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(value.strip() + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def _install_github_secret(name: str, value: str) -> bool:
    if not shutil.which("gh"):
        return False
    result = subprocess.run(
        ["gh", "secret", "set", name, "--repo", REPO],
        input=value.strip() + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        print(f"Installed GitHub Actions secret: {name}")
        return True
    print("GitHub CLI could not install the secret automatically.")
    if result.stderr:
        print(result.stderr.strip()[:500])
    return False


def install_existing_analytics(path_arg: str | None) -> None:
    path = _find_json(path_arg, ["analytics_token.json"])
    data = json.loads(path.read_text(encoding="utf-8"))
    refresh = str(data.get("refresh_token") or "").strip()
    scopes = set(data.get("scopes") or [])
    required = {
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    }
    if not refresh:
        raise RuntimeError("analytics_token.json has no refresh_token")
    if not required.issubset(scopes):
        raise RuntimeError("analytics_token.json does not contain the expected Analytics scopes")
    if _install_github_secret("YOUTUBE_ANALYTICS_REFRESH_TOKEN", refresh):
        return
    saved = _safe_store("youtube_analytics_refresh_token.txt", refresh)
    print("Analytics authorization is valid, but GitHub secret installation needs one local step:")
    print(f'gh secret set YOUTUBE_ANALYTICS_REFRESH_TOKEN --repo {REPO} < "{saved}"')


class _Callback(BaseHTTPRequestHandler):
    result: dict = {}
    expected_state = ""

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        state = (qs.get("state") or [""])[0]
        if state != self.expected_state:
            self.result = {"error": "OAuth state mismatch"}
            status = 400
        elif qs.get("error"):
            self.result = {"error": (qs["error"] or ["authorization_error"])[0]}
            status = 400
        else:
            self.result = {"code": (qs.get("code") or [""])[0]}
            status = 200
        body = (
            b"Astra YouTube authorization received. You can close this browser tab."
            if status == 200
            else b"Astra authorization failed. Return to the terminal for details."
        )
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def authorize_full(client_path_arg: str | None) -> None:
    client_path = _find_json(client_path_arg, ["client_secret.json"])
    cfg = _client(client_path)

    server = HTTPServer(("127.0.0.1", 0), _Callback)
    port = server.server_address[1]
    redirect_uri = f"http://localhost:{port}/"

    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).decode("ascii").rstrip("=")
    state = secrets.token_urlsafe(24)
    _Callback.expected_state = state
    _Callback.result = {}

    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(FULL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = AUTH_URL + "?" + urlencode(params)
    print("Opening Google authorization in your browser.")
    print("Approve the requested YouTube permissions for the LOKI channel.")
    if not webbrowser.open(url):
        print("Browser did not open automatically. Open this URL locally:")
        print(url)

    server.timeout = 300
    server.handle_request()
    server.server_close()

    if _Callback.result.get("error"):
        raise RuntimeError("Google authorization failed: " + _Callback.result["error"])
    code = _Callback.result.get("code")
    if not code:
        raise RuntimeError("No authorization code was received")

    with httpx.Client(timeout=30) as client:
        r = client.post(TOKEN_URL, data={
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "code": code,
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        })
    if r.status_code >= 400:
        raise RuntimeError("Token exchange failed: " + r.text[:400])
    token = r.json()
    refresh = str(token.get("refresh_token") or "").strip()
    if not refresh:
        raise RuntimeError("Google did not return a refresh token; revoke the old consent and retry")

    if _install_github_secret("YOUTUBE_FULL_REFRESH_TOKEN", refresh):
        print("Astra's analytics learning and guarded comment replies can now run in the cloud.")
        return

    saved = _safe_store("youtube_full_refresh_token.txt", refresh)
    print("Authorization succeeded. Install the saved token as a GitHub Actions secret:")
    print(f'gh secret set YOUTUBE_FULL_REFRESH_TOKEN --repo {REPO} < "{saved}"')
    print("Never paste this token into chat or commit it to Git.")


def main():
    p = argparse.ArgumentParser(description="Complete Astra YouTube autonomy authorization.")
    p.add_argument("--client-secret", help="Path to client_secret.json")
    p.add_argument("--analytics-token", help="Path to analytics_token.json")
    p.add_argument("--install-existing-analytics", action="store_true")
    p.add_argument("--authorize-full", action="store_true")
    args = p.parse_args()

    if args.install_existing_analytics:
        install_existing_analytics(args.analytics_token)
        return
    if args.authorize_full:
        authorize_full(args.client_secret)
        return
    p.print_help()


if __name__ == "__main__":
    main()
