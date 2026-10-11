"""Regression tests for the ASTRA Main pre-upload publication gate."""
import unittest

from astra_v2.publication_quality import publication_rejection


class PublicationQualityTests(unittest.TestCase):
    def test_unreviewed_procedural_short_rejected(self):
        self.assertEqual(
            publication_rejection({"content_id": "rayvan-procedural-123", "title": "The Chase"}),
            "unreviewed_template_procedural_story",
        )

    def test_unreviewed_procedural_long_rejected(self):
        self.assertEqual(
            publication_rejection({"content_id": "RAYVAN-PROCEDURAL-456", "title": "An Adventure", "format": "long"}),
            "unreviewed_template_procedural_story",
        )

    def test_malformed_title_rejected(self):
        self.assertEqual(
            publication_rejection({"content_id": "curated-01", "title": "The A Monkey Escapes"}),
            "malformed_title_article_collision",
        )

    def test_missing_identity_rejected(self):
        self.assertEqual(publication_rejection({"content_id": "", "title": "A Tale"}),
                         "missing_publication_identity_or_title")

    def test_curated_short_allowed(self):
        self.assertIsNone(publication_rejection(
            {"content_id": "curated-01", "title": "The Monkey Escapes", "format": "short"}))

    def test_curated_long_allowed(self):
        self.assertIsNone(publication_rejection(
            {"content_id": "long-01", "title": "Jungle Adventure", "format": "long"}))


if __name__ == "__main__":
    unittest.main()
