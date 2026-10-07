"""OmniRoute adapter for Astra.

Keeps provider/model routing outside the creative engine. OmniRoute exposes an
OpenAI-compatible endpoint, so Astra can request a capability tier rather than
hard-code one provider throughout the pipeline.
"""
from __future__ import annotations
import json, os, urllib.request

BASE_URL = os.getenv("OMNIROUTE_BASE_URL", "http://127.0.0.1:20128/v1").rstrip("/")
API_KEY = os.getenv("OMNIROUTE_API_KEY", "")

TASK_POLICY = {
    "creative": os.getenv("ASTRA_OMNI_CREATIVE_MODEL", "auto"),
    "story": os.getenv("ASTRA_OMNI_STORY_MODEL", "auto"),
    "director": os.getenv("ASTRA_OMNI_DIRECTOR_MODEL", "auto"),
    "research": os.getenv("ASTRA_OMNI_RESEARCH_MODEL", "auto"),
    "routine": os.getenv("ASTRA_OMNI_ROUTINE_MODEL", "auto"),
}

def chat(messages: list[dict], task: str = "routine", temperature: float = 0.7,
         max_tokens: int = 2000) -> str:
    model = TASK_POLICY.get(task, TASK_POLICY["routine"])
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions", data=payload, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        data = json.load(response)
    return data["choices"][0]["message"]["content"]

def creative(prompt: str) -> str:
    return chat([{"role":"system","content":"You are Astra's senior creative director. Optimize for originality, coherent storytelling, retention, audiovisual continuity and finished-viewer quality. Never confuse technical validity with creative quality."},{"role":"user","content":prompt}], task="creative", temperature=0.9, max_tokens=3500)

def story(prompt: str) -> str:
    return chat([{"role":"system","content":"Create one coherent short-form story with a strong hook, escalation, payoff, visual causality and scene-to-scene continuity. Design dialogue, action and reactions as one timeline."},{"role":"user","content":prompt}], task="story", temperature=0.85, max_tokens=3500)

def director(prompt: str) -> str:
    return chat([{"role":"system","content":"Judge the finished viewing experience harshly. Reject incoherent pacing, repetitive visuals, continuity breaks, weak audio-story alignment, or stitched-clip feel even if technical metrics pass."},{"role":"user","content":prompt}], task="director", temperature=0.35, max_tokens=2500)
