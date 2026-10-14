import tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
from experimental.premium_compositor import Layer,layout,render,quality_report

class PremiumCompositionTests(unittest.TestCase):
    def test_collision_rejected(self):
        a=Layer("a.png",200,200,100,100)
        b=Layer("b.png",205,205,100,100)
        with self.assertRaisesRegex(ValueError,"overlap"):
            layout([a,b],width=400,height=400)
    def test_bright_render_with_separated_layers(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=[]
            for n,color in enumerate(((255,180,55,255),(235,65,92,255))):
                path=Path(folder)/f"{n}.png"
                im=Image.new("RGBA",(128,128),(0,0,0,0))
                ImageDraw.Draw(im).ellipse((8,8,120,120),fill=color)
                im.save(path);paths.append(str(path))
            layers=[Layer(paths[0],90,210,110,110),Layer(paths[1],280,210,110,110)]
            im=render(layers,360,640)
            report=quality_report(im,layers)
            self.assertTrue(report["brightness_pass"])
            self.assertTrue(report["color_pass"])
            self.assertEqual(im.size,(360,640))
    def test_deterministic_layout(self):
        layers=[Layer("x",90,90,64,64)]
        self.assertEqual(layout(layers),layout(layers))
if __name__=="__main__":unittest.main()
