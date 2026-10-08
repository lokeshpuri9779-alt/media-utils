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
        nested = body.get("errors") or []
        if nested:
            return str(nested[0].get("reason") or "api_error")
        return str(body.get("status") or "api_error")
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
        names = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
        missing = [name for name in names if not os.environ.get(name)]
        if missing:
            raise RuntimeError("Required GitHub Actions OAuth secrets missing: " + ", ".join(missing))
        response = self.client.post("https://oauth2.googleapis.com/token", data={
            "client_id": os.environ["YOUTUBE_CLIENT_ID"],
            "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
            "refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        })
        self.check(response, "oauth_refresh")
        self.token = response.json().get("access_token")
        if not self.token:
            raise RuntimeError("OAuth response missing access token.")
        data = self.get("channels", {"part": "id,contentDetails", "mine": "true"})
        records = data.get("items") or []
        if len(records) != 1 or records[0].get("id") != self.expected_id:
            raise RuntimeError("OAuth authorizes a different channel: refused to upload.")
        return records[0]

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

    def upload(self, video, title, description, synthetic=False):
        metadata = {
            "snippet": {"title": title[:100], "description": description[:5000],
                        "categoryId": "24", "defaultLanguage": "en"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
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
