#!/usr/bin/env python3
"""Fail-closed, zero-cost OmniRoute image-provider selector.

This is routing policy only: no external API invocation, credentials or billing.
Only verified local CPU generation is executable in this isolated lab.
"""
import argparse
import json
import os

ROUTES = {
    "sd15_cpu": {"kind": "local", "cost": "zero_api_cost", "implemented": True,
                 "requires": [], "capability": "text_to_image"},
    "sd15_img2img": {"kind": "local", "cost": "zero_api_cost", "implemented": True,
                    "requires": ["reference_image"], "capability": "image_to_image"},
    "gpt_image_api": {"kind": "remote", "cost": "paid", "implemented": False,
                      "requires": ["api_key", "billing_approval"], "capability": "text_to_image"},
    "free_remote_provider": {"kind": "remote", "cost": "unknown", "implemented": False,
                             "requires": ["provider_integration", "terms_review"],
                             "capability": "text_to_image"},
}

def select_route(*, reference_image=False, zero_cost=True, preferred=None):
    if not zero_cost:
        raise ValueError("This lab only supports zero-cost routing")
    candidates = ["sd15_img2img", "sd15_cpu"] if reference_image else ["sd15_cpu"]
    if preferred:
        if preferred not in ROUTES:
            raise ValueError("Unknown provider: " + preferred)
        candidates = [preferred]
    for name in candidates:
        route = ROUTES[name]
        if route["implemented"] and route["kind"] == "local" and (
            not route["requires"] or reference_image
        ):
            return {"selected": name, "reason": "implemented local CPU route",
                    "paid_api_called": False, "published": False}
    return {"selected": None, "reason": "No eligible implemented zero-cost route",
            "paid_api_called": False, "published": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-image", action="store_true")
    parser.add_argument("--preferred", choices=tuple(ROUTES))
    args = parser.parse_args()
    result = select_route(reference_image=args.reference_image, preferred=args.preferred)
    print(json.dumps({"policy": "zero_cost_only", "routes": ROUTES, **result}, indent=2))
    if not result["selected"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
