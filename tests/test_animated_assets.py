"""Animation/state visual regression tests."""
import unittest
from experimental.animated_assets import ANIMALS,STATES,animal_frame,item_state_frame

class AnimatedAssetTests(unittest.TestCase):
    def test_animals_render(self):
        for animal in ANIMALS:
            self.assertEqual(animal_frame(animal,0,64).size,(64,64))
    def test_animals_move(self):
        for animal in ANIMALS:
            self.assertNotEqual(animal_frame(animal,0,96).tobytes(),
                                animal_frame(animal,.2,96).tobytes())
    def test_state_visuals_differ(self):
        results=[item_state_frame("house","architecture",state,96).tobytes() for state in STATES]
        self.assertEqual(len(set(results)),len(STATES))
    def test_deterministic(self):
        self.assertEqual(animal_frame("dog",1).tobytes(),animal_frame("dog",1).tobytes())
    def test_invalid_species(self):
        with self.assertRaises(ValueError):
            animal_frame("unknown",0)

if __name__=="__main__":
    unittest.main()
