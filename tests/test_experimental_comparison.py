import json,tempfile,unittest
from pathlib import Path
from tools.compare_experimental_engines import compare

class ComparisonTests(unittest.TestCase):
    def test_failed_report_not_winner(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.json';p.write_text(json.dumps({'engine':'Blender','success':False,'elapsed_seconds':2}))
            result=compare([p]);self.assertIsNone(result['fastest_successful_benchmark'])
            self.assertIsNone(result['promoted_engine'])
    def test_fastest_not_visual_winner(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.json';p.write_text(json.dumps({'engine':'Godot','success':True,'elapsed_seconds':3}))
            result=compare([p]);self.assertEqual(result['fastest_successful_benchmark'],'Godot')
            self.assertIsNone(result['visual_quality_winner'])
            self.assertFalse(result['benchmarks'][0]['production_eligible'])

if __name__=='__main__':unittest.main()
