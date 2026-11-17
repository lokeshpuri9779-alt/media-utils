import base64
import json
import unittest

from astra_v2.github_contents import decode_json_contents_file


class GitHubContentsJsonTests(unittest.TestCase):
    def test_decodes_normal_inline_contents_response(self):
        payload = {"version": 2, "published": {"one": {"video_id": "abc"}}}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        result = decode_json_contents_file(
            {"encoding": "base64", "content": encoded, "sha": "unused"},
            lambda _: self.fail("blob fallback should not be used"),
        )
        self.assertEqual(result, payload)

    def test_falls_back_to_blob_when_contents_api_omits_large_content(self):
        payload = {"version": 2, "padding": "x" * (1024 * 1024 + 32)}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        calls = []

        def api_get(endpoint):
            calls.append(endpoint)
            return {"encoding": "base64", "content": encoded}

        result = decode_json_contents_file(
            {"encoding": "none", "content": "", "sha": "large-blob-sha"}, api_get
        )
        self.assertEqual(result, payload)
        self.assertEqual(calls, ["git/blobs/large-blob-sha"])


if __name__ == "__main__":
    unittest.main()
