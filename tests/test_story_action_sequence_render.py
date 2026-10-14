"""End-to-end illustrated storyboard motion QA (no upload or API credentials)."""
import unittest
from PIL import Image, ImageChops
from astra_v2.story_action_motion import choose_action
from astra_v2.story_visuals import select_subject, draw_subject

SIZE=(1080,1920)
BG=(12,14,19)
ACCENT=(255,175,90)
ACTIONS=(
    ("The fox runs toward the bridge.", "run"),
    ("The fox jumps over a stone.", "jump"),
    ("The fox dances with relief.", "dance"),
    ("The fox hides behind the tree.", "hide"),
    ("The fox walks home.", "walk"),
    ("The fox looks toward the stars.", "look"),
)

def render_sequence(story, beats, times=(0.35,0.85,1.35)):
    """Return scene frames using the same subject and motion code as Studio."""
    result=[]
    for speech, expected in beats:
        shot={"speech":speech,"visual":"story"}
        subject=select_subject(story,shot)
        action=choose_action(shot)
        if action!=expected:
            raise AssertionError(f"Incorrect action {action} for {speech}")
        frames=[]
        for t in times:
            im=Image.new("RGB",SIZE,BG)
            if not draw_subject(im,subject,t,ACCENT,action):
                raise AssertionError(f"Missing illustration for {subject}")
            frames.append(im)
        result.append(frames)
    return result

class StorySequenceRenderTests(unittest.TestCase):
    def test_six_action_storyboard_renders_nonblank_and_moves(self):
        scenes=render_sequence({"title":"The fox's journey"},ACTIONS)
        self.assertEqual(len(scenes),6)
        for frames in scenes:
            self.assertEqual(len(frames),3)
            for frame in frames:
                self.assertIsNotNone(ImageChops.difference(frame,Image.new("RGB",SIZE,BG)).getbbox())
            self.assertIsNotNone(ImageChops.difference(frames[0],frames[1]).getbbox())
    def test_scene_action_changes_visual_at_same_time(self):
        scenes=render_sequence({"title":"The fox's journey"},ACTIONS,times=(0.85,))
        self.assertIsNotNone(ImageChops.difference(scenes[0][0],scenes[1][0]).getbbox())
    def test_named_actor_persists_across_story_beats(self):
        story={"title":"The fox's journey"}
        for speech,_ in ACTIONS:
            self.assertEqual(select_subject(story,{"speech":speech,"visual":"story"}),"fox")
    def test_unknown_subject_does_not_paint(self):
        im=Image.new("RGB",SIZE,BG)
        self.assertFalse(draw_subject(im,"nonexistent",0.5,ACCENT,"jump"))
        self.assertIsNone(ImageChops.difference(im,Image.new("RGB",SIZE,BG)).getbbox())

if __name__=="__main__":
    unittest.main()
