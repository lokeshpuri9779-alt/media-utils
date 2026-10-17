"""Deterministic inventory of renderable ASTRA procedural assets.

Recipes are not image files. No external art is implied or licensed here.
"""
from astra_v2.procedural_visual_library import (
    CHARACTER_VARIANTS, ICON_VARIANTS, character_recipe, icon_recipe,
)

def inventory():
    return {"characters": CHARACTER_VARIANTS, "icons": ICON_VARIANTS,
            "total": CHARACTER_VARIANTS + ICON_VARIANTS,
            "format": "procedural_recipe", "external_assets": 0}

def resolve_asset(asset_id):
    if not isinstance(asset_id, str):
        raise ValueError("invalid asset id")
    for prefix, count, resolver, kind in (
        ("character-", CHARACTER_VARIANTS, character_recipe, "character"),
        ("icon-", ICON_VARIANTS, icon_recipe, "icon"),
    ):
        if asset_id.startswith(prefix):
            digits = asset_id[len(prefix):]
            if not digits.isdigit() or len(digits) != 4:
                raise ValueError("invalid asset id")
            index = int(digits)
            if not 0 <= index < count:
                raise ValueError("asset not found")
            recipe = resolver(index)
            if recipe["id"] != asset_id:
                raise ValueError("noncanonical asset id")
            return {"type": kind, "source": "procedural", "recipe": recipe}
    raise ValueError("asset not found")
