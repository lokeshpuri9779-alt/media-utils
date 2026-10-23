import unittest
from astra_v2.r2_usage_audit import measure


class FakeClient:
    def __init__(self, pages):
        self.pages = iter(pages)

    def list_objects_v2(self, **kwargs):
        return next(self.pages)


class UsageTests(unittest.TestCase):
    def test_pagination(self):
        client = FakeClient([
            {'Contents': [{'Size': 4}], 'IsTruncated': True,
             'NextContinuationToken': 'next'},
            {'Contents': [{'Size': 6}], 'IsTruncated': False},
        ])
        self.assertEqual(measure(client, 'bucket', 'astra/')['used_bytes'], 10)

    def test_incomplete_listing_fails_closed(self):
        with self.assertRaises(RuntimeError):
            measure(FakeClient([{'IsTruncated': True}]), 'bucket', 'astra/')

    def test_bad_size(self):
        with self.assertRaises(ValueError):
            measure(FakeClient([{'Contents': [{'Size': -1}]}]), 'bucket', 'astra/')


if __name__ == '__main__':
    unittest.main()
