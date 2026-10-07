"""Durable Astra orchestration control plane.

Pure decision layer: no provider-specific execution. It coordinates persisted state,
route migration, render feasibility and release policy without bypassing quality.
"""
from __future__ import annotations
from runtime_state import default_state, quarantine, record_canary, checkpoint
from self_migration import decide
from render_preflight import RenderProbe, assess
from hardware_render_planner import RenderProfile, release_policy

def plan_job(job: dict, state: dict|None, current_route: dict|None,
             candidates: list[dict], probe: RenderProbe|None,
             profile: RenderProfile|None) -> dict:
    state=state or default_state()
    migration=decide(current_route,candidates,state.get("canary_passes",{}))

    if migration["action"]=="checkpoint":
        state=checkpoint(state,job["id"],{"stage":"route_selection","reason":migration["reason"]})
        return {"action":"checkpoint","stage":"route_selection","state":state,"migration":migration}

    route=migration["selected"]
    if migration.get("quarantine"):
        state=quarantine(state,migration["quarantine"],migration["reason"])

    if migration["action"]=="canary":
        # Canary execution is always private and cannot become a production release.
        return {"action":"run_canary","route":route,"private_only":True,
                "requires_quality_gate":True,"state":state,"migration":migration}

    if probe is None or profile is None:
        state=checkpoint(state,job["id"],{"stage":"preflight","reason":"missing_runtime_probe"})
        return {"action":"checkpoint","stage":"preflight","state":state,"migration":migration}

    feasibility=assess(probe)
    if not feasibility["render_feasible"]:
        state=quarantine(state,route,"render_preflight_failed")
        state=checkpoint(state,job["id"],{"stage":"preflight","reason":feasibility["reasons"]})
        return {"action":"checkpoint","stage":"preflight","state":state,
                "migration":migration,"feasibility":feasibility}

    release=release_policy(profile)
    state["active_route"]=route
    return {"action":"render","route":route,"profile":profile.name,
            "release":release,"state":state,"migration":migration,
            "feasibility":feasibility}

def finish_canary(state: dict, route: str, quality_passed: bool) -> dict:
    return record_canary(state,route,quality_passed)

def finish_render(state: dict, job_id: str, quality_passed: bool) -> dict:
    out={**state,"checkpoints":dict(state.get("checkpoints",{}))}
    if quality_passed:
        out["checkpoints"].pop(job_id,None)
    else:
        out=checkpoint(out,job_id,{"stage":"quality_gate","reason":"quality_regression"})
    return out
