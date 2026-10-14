"""Story variety and continuity tests."""
import unittest
from experimental.story_director import PLOTS,LOCATIONS,BEATS,generate,plan_for,batch,signature
from experimental.story_demo import make_demo
from pathlib import Path
from tempfile import TemporaryDirectory

class StoryDirectorTests(unittest.TestCase):
    def test_all_plots_and_locations(self):
        for plot in PLOTS:
            for location in LOCATIONS:
                story=generate(7,plot,location)
                self.assertEqual(len(story.beats),4)
                self.assertEqual(plan_for(story,3).width,360)
    def test_repeatability(self):
        self.assertEqual(generate(42),generate(42))
    def test_variety(self):
        stories=batch(24,7)
        self.assertEqual(len(set(map(signature,stories))),24)
    def test_repair_beat_sequence(self):
        self.assertEqual(BEATS["repair"],("problem","investigate","repair","celebrate"))
    def test_demo_files(self):
        with TemporaryDirectory() as folder:
            make_demo(folder)
            self.assertTrue((Path(folder)/"story-contact-sheet.png").exists())
            self.assertTrue((Path(folder)/"manifest.json").exists())
            self.assertEqual(len(list(Path(folder).glob("beat-*.png"))),4)

if __name__=="__main__": unittest.main()
