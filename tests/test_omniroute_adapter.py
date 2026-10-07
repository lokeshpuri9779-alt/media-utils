import os
import omniroute_adapter as omni

def test_task_policy_has_quality_roles():
    assert {"creative","story","director","research","routine"} <= set(omni.TASK_POLICY)

def test_defaults_are_auto_routed():
    for role in ("creative","story","director"):
        assert omni.TASK_POLICY[role]

def test_gateway_is_openai_compatible_path():
    assert omni.BASE_URL.endswith("/v1")

def test_quality_prompts_reject_technical_only_success(monkeypatch):
    seen=[]
    def fake(messages, task="routine", temperature=0.7, max_tokens=2000):
        seen.append((messages,task))
        return "ok"
    monkeypatch.setattr(omni,"chat",fake)
    assert omni.creative("x")=="ok"
    assert omni.story("x")=="ok"
    assert omni.director("x")=="ok"
    assert [x[1] for x in seen]==["creative","story","director"]
    director_system=seen[2][0][0]["content"].lower()
    assert "technical metrics" in director_system
    assert "stitched-clip" in director_system
