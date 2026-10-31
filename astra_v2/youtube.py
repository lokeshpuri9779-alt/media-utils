"""YouTube Data API adapter. OAuth secrets never enter source control or logs."""
import os
import httpx

API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"


class YoutubeError(RuntimeError):
    def __init__(self, stage, code, reason):
        self.stage, self.code, self.reason = stage, code, reason
        super().__init__(f"YouTube {stage}: HTTP {code}; reason={reason}")


def reason_for(response):
    try:
        body = response.json().get("error") or {}
        # OAuth failures return {"error":"invalid_grant"} rather than the
        # structured YouTube Data API {"error":{"errors":[...]}} response.
        if isinstance(body, str):
            return body[:80]
        if not isinstance(body, dict):
            return "api_error"
        if isinstance(body.get("error"), str):
            return body["error"][:80]
        nested = body.get("errors") or []
        if nested and isinstance(nested[0], dict):
            return str(nested[0].get("reason") or "api_error")[:80]
        return str(body.get("status") or "api_error")[:80]
    except (ValueError, TypeError, AttributeError):
        return "http_error"


class Youtube:
    def __init__(self, expected_id):
        self.expected_id = expected_id
        self.client = httpx.Client(timeout=60)
        self.token = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    @staticmethod
    def check(response, stage):
        if response.status_code >= 400:
            raise YoutubeError(stage, response.status_code, reason_for(response))
        return response

    def get(self, resource, parameters):
        response = self.client.get(API + "/" + resource, params=parameters,
                                   headers={"Authorization": "Bearer " + self.token})
        return self.check(response, resource).json()

    def authorize(self):
        """Select only an upload-capable OAuth identity matching this channel.

        The original primary refresh token may be revoked (invalid_grant);
        re-use the independently authorized community/backup OAuth credentials
        already stored as GitHub Actions secrets. Never log secret values.
        """
        candidates = [
            ("primary", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"),
            ("community", "YOUTUBE_COMMUNITY_CLIENT_ID", "YOUTUBE_COMMUNITY_CLIENT_SECRET",
             "YOUTUBE_COMMUNITY_REFRESH_TOKEN"),
        ]
        if os.environ.get("ASTRA_OAUTH_PRIORITY") == "community":
            candidates.reverse()
        reasons = []
        for alias, client, secret, refresh in candidates:
            if not all(os.environ.get(k) for k in (client, secret, refresh)):
                reasons.append(alias + ":not_configured")
                continue
            try:
                response = self.client.post("https://oauth2.googleapis.com/token", data={
                    "client_id": os.environ[client],
                    "client_secret": os.environ[secret],
                    "refresh_token": os.environ[refresh],
                    "grant_type": "refresh_token",
                })
            except httpx.RequestError:
                reasons.append(alias + ":oauth_network_error")
                continue
            if response.status_code >= 400:
                reasons.append(alias + ":" + reason_for(response))
                continue
            token = response.json().get("access_token")
            if not token:
                reasons.append(alias + ":missing_access_token")
                continue
            self.token = token
            try:
                data = self.get("channels", {"part": "id,contentDetails", "mine": "true"})
            except YoutubeError as exc:
                reasons.append(alias + ":channels_" + exc.reason)
                self.token = None
                continue
            records = data.get("items") or []
            if len(records) != 1 or records[0].get("id") != self.expected_id:
                reasons.append(alias + ":channel_mismatch")
                self.token = None
                continue
            # Channel lock happens before any write API call.
            self.credential_alias = alias
            print("ASTRA_YOUTUBE_AUTH=authorized_channel_via_" + alias)
            return records[0]
        self.token = None
        raise RuntimeError("No authorized upload identity for RAYVAN (" +
                           ", ".join(reasons) + ")")

    def recent(self, channel):
        playlist = (channel.get("contentDetails", {}).get("relatedPlaylists") or {}).get("uploads")
        if not playlist:
            raise RuntimeError("Uploads playlist unavailable; refusing unsafe retry.")
        data = self.get("playlistItems", {"part": "snippet", "playlistId": playlist,
                                           "maxResults": 50})
        identities, titles = set(), set()
        for item in data.get("items") or []:
            snippet = item.get("snippet") or {}
            titles.add(str(snippet.get("title") or "").casefold().strip())
            for line in str(snippet.get("description") or "").splitlines():
                if line.startswith(("ASTRA-ID:", "ASTRA-V2-ID:")):
                    identities.add(line.split(":", 1)[1].strip())
        return identities, titles

    def status(self, video_id):
        data = self.get("videos", {"part": "status", "id": video_id})
        items = data.get("items") or []
        return items[0].get("status") or {} if items else {}

    @staticmethod
    def discover_tags(title, description):
        """Use relevant evergreen discovery terms; do not invent live trends."""
        import re
        text = (title + " " + description).casefold()
        # Trend explainers are not fictional cartoons. Use the existing stable
        # content identity, not keywords such as "rocket" that can be ambiguous.
        if "ASTRA-V2-ID:trend-brief-" in description:
            topic = re.sub(r"^Why\s+", "", title, flags=re.IGNORECASE)
            topic = re.sub(r"\s+Is Getting Attention Now\s*\|\s*RAYVAN\s*$", "", topic, flags=re.IGNORECASE).strip()
            tags = ["news explainer", "current events", "trend analysis"]
            if 2 <= len(topic) <= 60 and re.fullmatch(r"[\w\s'’.-]+", topic):
                tags.insert(0, topic)
            return tags, []
        themes = {
            "comedy": (("funny", "comedy", "joke", "laugh", "humor", "humour"), ("comedy", "funny cartoon", "animated comedy")),
            "mystery": (("mystery", "detective", "clue", "secret"), ("mystery story", "animated mystery")),
            "suspense": (("suspense", "thriller", "twist", "scary", "horror"), ("suspense story", "animated thriller")),
            "adventure": (("adventure", "quest", "journey"), ("animated adventure", "adventure story")),
            "animals": (("monkey", "dog", "cat", "puppy", "animal"), ("animal cartoon", "funny animals")),
        }
        tags = ["animated stories", "original animation", "3D cartoon"]
        matched = []
        for _, (keywords, additions) in themes.items():
            if any(re.search(r"\b" + re.escape(k) + r"\b", text) for k in keywords):
                tags.extend(additions)
                matched.append(additions[0])
        if not matched:
            tags.append("animated storytelling")
        tags = list(dict.fromkeys(tags))[:15]
        hashtags = ["#Shorts"] if "#shorts" in description.casefold() or "short" in title.casefold() else []
        for tag in matched[:2]:
            hashtags.append("#" + "".join(w.capitalize() for w in tag.split()))
        return tags, hashtags

    def set_thumbnail(self, video_id, image_path):
        """Best-effort custom thumbnail for eligible long-form uploads.

        Shorts cover frames remain local; do not claim the API can select a
        Shorts thumbnail. This operation is never retried automatically.
        """
        from pathlib import Path
        image = Path(image_path)
        if not image.is_file() or not 0 < image.stat().st_size <= 2 * 1024 * 1024:
            raise ValueError("Thumbnail must be a nonempty JPEG under 2 MB")
        with image.open("rb") as stream:
            response = self.client.post(
                "https://www.googleapis.com/upload/youtube/v3/thumbnails/set",
                params={"videoId": str(video_id), "uploadType": "media"},
                headers={"Authorization": "Bearer " + self.token,
                         "Content-Type": "image/jpeg"},
                content=stream.read(),
            )
        self.check(response, "thumbnail_set")
        return True

    def upload(self, video, title, description, synthetic=False, made_for_kids=None):
        # Audience classification is independent of animation style.
        # The publisher may supply an explicit per-video classification.
        if made_for_kids is None:
            made_for_kids = os.getenv("ASTRA_MADE_FOR_KIDS", "0") == "1"
        if not isinstance(made_for_kids, bool):
            raise ValueError("made_for_kids must be a boolean")
        tags, hashtags = self.discover_tags(title, description)
        existing = {token.casefold() for token in description.split() if token.startswith("#")}
        extra = [tag for tag in hashtags if tag.casefold() not in existing]
        if extra:
            description = description[:max(0, 5000 - len(" ".join(extra)) - 2)] + "\n" + " ".join(extra)
        metadata = {
            "snippet": {"title": title[:100], "description": description[:5000],
                        "tags": tags, "categoryId": "24", "defaultLanguage": "en"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": made_for_kids,
                       "containsSyntheticMedia": bool(synthetic)},
        }
        result = self.client.post(UPLOAD, params={
            "uploadType": "resumable", "part": "snippet,status",
        }, headers={
            "Authorization": "Bearer " + self.token,
            "X-Upload-Content-Length": str(video.stat().st_size),
            "X-Upload-Content-Type": "video/mp4",
        }, json=metadata)
        self.check(result, "upload_session")
        location = result.headers.get("Location")
        if not location or not location.startswith("https://"):
            raise RuntimeError("Upload session URL absent.")
        # Do not retry a network-uncertain transfer: it might already be uploaded.
        try:
            with video.open("rb") as stream, httpx.Client(timeout=None) as transfer:
                result = transfer.put(location, content=stream, headers={
                    "Authorization": "Bearer " + self.token,
                    "Content-Type": "video/mp4",
                    "Content-Length": str(video.stat().st_size),
                })
        except httpx.RequestError as exc:
            # Never log the resumable URL, bearer token or credential-bearing
            # request object from a transfer exception.
            raise RuntimeError("Upload transfer indeterminate; check Studio before retry.") from None
        self.check(result, "upload_transfer")
        video_id = result.json().get("id")
        if not video_id:
            raise RuntimeError("Upload may have succeeded but returned no video ID; review Studio.")
        return str(video_id)
