"""Offline coordinated development smoke tests."""
from pathlib import Path
from PIL import Image
from astra_v2.coordinated_development import build_plan, frame, render


def test_plan_reproducible_and_unique():
    a = build_plan("integration-seed", 16)
    b = build_plan("integration-seed", 16)
    assert a == b
    assert len({s["character_id"] for s in a["scenes"]}) == 16
    assert len({s["object_id"] for s in a["scenes"]}) == 16
    assert a["publication_allowed"] is False


def test_frame_and_storyboard(tmp_path):
    plan = build_plan("visual-smoke", 4)
    image = frame(plan["scenes"][0], 0.3)
    assert image.size == (540, 960)
    result = render(plan, tmp_path, fps=4, video=False)
    assert result["scene_count"] == 4
    assert not result["motion_failures"]
    assert result["quality_approved"] is False
    assert (tmp_path / "storyboard.png").is_file()
    assert (tmp_path / "plan.json").is_file()
    assert (tmp_path / "report.json").is_file()


def test_duplicate_artwork_is_detected_despite_scene_number(tmp_path):
    import pytest
    plan = build_plan("same-artwork", 2)
    plan["scenes"][1]["character_id"] = plan["scenes"][0]["character_id"]
    plan["scenes"][1]["object_id"] = plan["scenes"][0]["object_id"]
    with pytest.raises(RuntimeError, match="duplicate_openings"):
        render(plan, tmp_path, fps=4, video=False)
    import json
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["visually_duplicate_scene_openings"] == [2]
