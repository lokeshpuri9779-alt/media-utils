from __future__ import annotations

"""Provider capability and cost policy for Astra video generation.

Automatic execution is allowed only for explicitly free/self-hosted backends.
Paid or unknown backends require explicit human approval.
"""

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ProviderCapability:
    key: str
    execution: str
    cost_class: str
    requires_gpu: bool
    autonomous_allowed: bool
    notes: str = ""


CAPABILITIES = {
    "ltx-local": ProviderCapability(
        "ltx-local","local","self-hosted",True,True,
        "Open-source model on operator-owned/attached GPU compute."
    ),
    "wan2.2-local": ProviderCapability(
        "wan2.2-local","local","self-hosted",True,True,
        "Open-source model on operator-owned/attached GPU compute."
    ),
    "remote-open-source-gpu": ProviderCapability(
        "remote-open-source-gpu","remote","self-hosted",True,True,
        "Authenticated Astra GPU worker; compute ownership/cost is external to Astra."
    ),
    "hf-zerogpu": ProviderCapability(
        "hf-zerogpu","remote","free-quota",True,True,
        "Hugging Face ZeroGPU shared compute; must fail closed when free quota is unavailable."
    ),
    "replicate": ProviderCapability(
        "replicate","remote","paid",True,False,
        "Paid inference fallback; explicit spend approval required."
    ),
}


def capability(provider: str | None) -> dict:
    key=str(provider or "").strip()
    item=CAPABILITIES.get(key)
    if item:
        return asdict(item)
    return {
        "key":key or "unknown",
        "execution":"unknown",
        "cost_class":"unknown",
        "requires_gpu":True,
        "autonomous_allowed":False,
        "notes":"Unknown providers are fail-closed until reviewed.",
    }


def autonomous_provider_allowed(provider: str | None) -> bool:
    return bool(capability(provider).get("autonomous_allowed"))


def choose_autonomous_provider(candidates: list[str]) -> str | None:
    for provider in candidates:
        if autonomous_provider_allowed(provider):
            return provider
    return None
