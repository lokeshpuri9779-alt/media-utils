from __future__ import annotations

import json
import os

import requests

EXPECTED_CHANNEL_ID = "UCT-PQG2AMDzqybPWRxCL0iQ"


def need(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise RuntimeError(f"Missing required secret: {name}")
    return value


def main() -> None:
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": need("YOUTUBE_CLIENT_ID_2"),
            "client_secret": need("YOUTUBE_CLIENT_SECRET_2"),
            "refresh_token": need("YOUTUBE_REFRESH_TOKEN_2"),
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if not token_response.ok:
        raise RuntimeError(
            f"Channel 2 OAuth refresh failed with HTTP {token_response.status_code}; no upload attempted."
        )

    access_token = token_response.json().get("access_token")
    if not access_token:
        raise RuntimeError("Channel 2 OAuth response contained no access token.")

    response = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "id,snippet", "mine": "true"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"Channel 2 identity check failed with HTTP {response.status_code}; no upload attempted."
        )

    items = response.json().get("items") or []
    ids = [item.get("id") for item in items]
    print("Channel 2 authorized IDs:", json.dumps(ids))
    print("Channel 2 expected ID:", EXPECTED_CHANNEL_ID)
    if ids != [EXPECTED_CHANNEL_ID]:
        raise RuntimeError(
            "Channel 2 credential mismatch; publishing remains disabled and no upload was attempted."
        )

    title = items[0].get("snippet", {}).get("title", "")
    print(f"CHANNEL2_IDENTITY_VERIFIED: {EXPECTED_CHANNEL_ID} | {title}")


if __name__ == "__main__":
    main()
