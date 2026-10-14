"""Regression checks for the isolated fox gift-pickup rig."""
import math
import unittest

from PIL import Image, ImageChops
from astra_v2.character_object_catalog import draw_character
from astra_v2.coordinated_development import build_comedy_demo, carry_elbow, frame


class CarryRigRegression(unittest.TestCase):
    def test_joint_connects_shoulders_to_both_prop_sides(self):
        # The two segments must join at the elbow without any detached gap.
        for scale in (0.53, 0.82, 1.0):
            for side in (-1, 1):
                shoulder = (300.0 + side * 75 * scale, 1130.0)
                for y in (1190.0, 1300.0, 1510.0):
                    hand = (300.0 + side * 55 * scale, y)
                    elbow = carry_elbow(shoulder, hand, side, scale)
                    self.assertTrue(all(math.isfinite(v) for v in elbow))
                    a = math.dist(shoulder, elbow)
                    b = math.dist(elbow, hand)
                    self.assertAlmostEqual(a, b, delta=1e-6)
                    self.assertGreater(a, 0)
                    self.assertLess(abs(elbow[0] - hand[0]), 500)

    def test_rig_pose_replaces_original_fixed_carry_arms(self):
        plan = build_comedy_demo()
        index = plan["scenes"][2]["character_id"]
        images = []
        for gesture in ("carry", "carry_rig"):
            image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
            draw_character(image, index, 0.25, 540, 1060,
                           expression="focused", gesture=gesture)
            images.append(image)
        self.assertIsNotNone(ImageChops.difference(images[0].convert("RGB"), images[1].convert("RGB")).getbbox())

    def test_gift_pickup_changes_artwork_across_five_frames(self):
        scene = build_comedy_demo()["scenes"][2]
        frames = [frame(scene, t) for t in (0.0, 0.35, 0.7, 1.1, 1.8)]
        self.assertTrue(all(img.size == (540, 960) for img in frames))
        # Restrict to the interacting fox and box, excluding the scene label.
        patches = [im.crop((40, 380, 260, 800)) for im in frames]
        for a, b in zip(patches, patches[1:]):
            self.assertIsNotNone(ImageChops.difference(a, b).getbbox())
        # Every sampled pose should be visually distinguishable.
        self.assertEqual(len({patch.tobytes() for patch in patches}), 5)


if __name__ == "__main__":
    unittest.main()
