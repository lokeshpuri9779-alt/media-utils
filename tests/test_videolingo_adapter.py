from videolingo_adapter import REQUIRED_SOURCE_FILES, backend_info


def test_videolingo_boundary_is_non_production():
    info = backend_info()
    assert info["engine"] == "Huanshere/VideoLingo"
    assert info["production_enabled"] is False
    assert info["imports_upstream_runtime"] is False
    assert "subtitle-segmentation" in info["purpose"]


def test_videolingo_expected_source_contract():
    assert "core/_5_split_sub.py" in REQUIRED_SOURCE_FILES
    assert "core/asr_backend/whisperX_local.py" in REQUIRED_SOURCE_FILES
