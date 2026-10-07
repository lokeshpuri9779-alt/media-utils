from renderer_router import rank, select

def test_long_form_continuation_prefers_continuation_capable_candidates():
    rows=rank({"long_form":True,"continuation":True,"image_reference":True,"reference_conditioning":True})
    assert rows[0]["key"]=="longcat_video"
    assert "missing_continuation" in next(x for x in rows if x["key"]=="hunyuanvideo_1_5")["blockers"]

def test_unvalidated_renderers_fail_closed():
    result=select({"long_form":False,"image_reference":True})
    assert result["selected"] is None
    assert result["status"]=="blocked"
    assert result["policy"]=="fail_closed_no_paid_and_no_unvalidated_renderer"

def test_vram_is_a_real_blocker_when_capacity_known():
    rows=rank({"image_reference":True}, available_vram_gb=12)
    assert all("insufficient_vram" in x["blockers"] for x in rows)

def test_no_wan_ltx_or_agnes_candidates():
    names=" ".join(rank({})[i]["key"] for i in range(len(rank({})))).lower()
    assert "wan" not in names
    assert "ltx" not in names
    assert "agnes" not in names
