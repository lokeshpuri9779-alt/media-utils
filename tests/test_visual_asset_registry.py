import unittest
from astra_v2.visual_asset_registry import inventory, resolve_asset
from astra_v2.pillow_duo_scene import ACTORS

class VisualAssetRegistryTests(unittest.TestCase):
    def test_inventory_is_real_recipes(self):
        data = inventory()
        self.assertEqual(data["characters"], len(ACTORS) * 250)
        self.assertEqual(data["total"], data["characters"] + data["icons"])
        self.assertEqual(data["external_assets"], 0)

    def test_all_species_present(self):
        species = {resolve_asset(f"character-{i:04d}")["recipe"]["species"]
                   for i in range(inventory()["characters"])}
        self.assertEqual(species, set(ACTORS))

    def test_boundary_entries(self):
        self.assertEqual(resolve_asset("character-0000")["type"], "character")
        self.assertEqual(resolve_asset("icon-0000")["type"], "icon")

    def test_invalid_ids_fail_closed(self):
        for bad in ("", "character--1", "character-9999", "icon-9999",
                    "character-0", "https://example.com/art.png"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                resolve_asset(bad)
