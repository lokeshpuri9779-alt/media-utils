import unittest

from astra_v2.github_release_inventory import measure_release_assets


class ReleaseInventoryTests(unittest.TestCase):
    def test_only_tagged_assets_count(self):
        pages = [[
            {"tag_name": "astra-media-001", "assets": [{"size": 100}, {"size": 50}]},
            {"tag_name": "other-release", "assets": [{"size": 900}]},
        ]]
        result = measure_release_assets(lambda n: pages[n - 1])
        self.assertEqual(result["used_bytes"], 150)
        self.assertEqual(result["asset_count"], 2)
        self.assertEqual(result["scope"], "tagged_releases_only")

    def test_pagination(self):
        first = [{"tag_name": "other", "assets": []} for _ in range(100)]
        result = measure_release_assets(lambda n: first if n == 1 else [
            {"tag_name": "astra-media-002", "assets": [{"size": 10}]}])
        self.assertEqual(result["used_bytes"], 10)

    def test_fail_closed_on_truncation(self):
        with self.assertRaises(RuntimeError):
            measure_release_assets(
                lambda n: [{"tag_name": "other", "assets": []} for _ in range(100)],
                max_pages=2)

    def test_rejects_truncated_embedded_assets(self):
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            measure_release_assets(lambda n: [{
                "tag_name": "astra-media-many",
                "assets": [{"size": 1} for _ in range(30)]
            }])

    def test_rejects_mismatched_asset_count(self):
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            measure_release_assets(lambda n: [{
                "tag_name": "astra-media-many",
                "assets_count": 4,
                "assets": [{"size": 1}]
            }])

    def test_paginates_all_release_assets(self):
        calls = []
        def assets(release_id, page):
            calls.append((release_id, page))
            return [{"size": 2} for _ in range(100)] if page == 1 else [{"size": 3}]
        result = measure_release_assets(
            lambda n: [{"id": 7, "tag_name": "astra-media-v1",
                        "assets_count": 101, "assets": []}],
            fetch_assets=assets)
        self.assertEqual(result["used_bytes"], 203)
        self.assertEqual(result["asset_count"], 101)
        self.assertEqual(calls, [(7, 1), (7, 2)])

    def test_pagination_rejects_incomplete_asset_count(self):
        with self.assertRaisesRegex(RuntimeError, "count_mismatch"):
            measure_release_assets(
                lambda n: [{"id": 7, "tag_name": "astra-media-v1",
                            "assets_count": 2, "assets": []}],
                fetch_assets=lambda rid, page: [{"size": 1}])

    def test_invalid_asset_size(self):
        with self.assertRaises(ValueError):
            measure_release_assets(lambda n: [
                {"tag_name": "astra-media-1", "assets": [{"size": -1}]}])


if __name__ == "__main__":
    unittest.main()
