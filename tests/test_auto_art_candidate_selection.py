"""Regression tests for fail-closed automatic artwork candidate selection."""
import json
from unittest.mock import patch

from astra_v2.select_editorial_art_candidate import main


def test_empty_inventory_fails_closed(capsys):
    with patch("astra_v2.select_editorial_art_candidate.load_editorial_stories", return_value=[]):
        assert main() == 2
    assert "no_eligible_approved_unpublished_story" in capsys.readouterr().err


def test_selects_deterministic_eligible_story(capsys):
    stories = [{"content_id": "story-z", "title": "Z"}, {"content_id": "story-a", "title": "A"}]
    with patch("astra_v2.select_editorial_art_candidate.load_editorial_stories", return_value=stories):
        assert main() == 0
    assert json.loads(capsys.readouterr().out)["content_id"] == "story-a"


def test_missing_content_ids_not_selected(capsys):
    with patch("astra_v2.select_editorial_art_candidate.load_editorial_stories", return_value=[{"title": "Incomplete"}]):
        assert main() == 2
