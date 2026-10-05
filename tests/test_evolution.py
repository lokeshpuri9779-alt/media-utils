import unittest
from evolution import diagnose_video, evolution_state

def entry(views=100,avp=80,likes=3,shares=1,subs=0):
    return {"analytics":{"views":views,"averageViewPercentage":avp,"likes":likes,"shares":shares,"subscribersGained":subs},
      "analytics_reports":{"basic":{"status":"available"},"traffic_sources":{"status":"available","rows":[{"views":views}]}}}

class EvolutionTests(unittest.TestCase):
    def test_tiny_sample_is_not_learned(self):
        self.assertEqual(diagnose_video(entry(20,95))["status"],"insufficient_evidence")
    def test_low_retention_diagnosis(self):
        self.assertEqual(diagnose_video(entry(100,40))["failure"],"hook_or_retention")
    def test_healthy_becomes_blueprint(self):
        d={"videos":{"abc":{**entry(200,90,10,3,2),"genre":"space","content_id":"x"}}}
        e=evolution_state(d)
        self.assertEqual(e["winner_blueprints"][0]["genre"],"space")
        self.assertIn("reuse abstract",e["rule"])

if __name__=="__main__":unittest.main()
