import os, tempfile, unittest
from unittest.mock import patch
import revenue_geo

class RevenueGeoTests(unittest.TestCase):
    def test_cold_start_is_not_fake_rpm(self):
        s=revenue_geo.geography_state({"videos":{}})
        self.assertEqual(s["mode"],"cold_start")
        self.assertFalse(s["guardrails"]["fake_location"])
    def test_actual_revenue_overrides_prior(self):
        d={"videos":{"v":{"analytics_reports":{"geography":{"status":"available","rows":[
          {"country":"IN","views":100,"estimatedMinutesWatched":100,"estimatedRevenue":5},
          {"country":"US","views":100,"estimatedMinutesWatched":100,"estimatedRevenue":1}]}}}}}
        s=revenue_geo.geography_state(d)
        self.assertEqual(s["mode"],"actual_revenue")
        self.assertEqual(s["ranked_countries"][0]["country"],"IN")

if __name__=="__main__": unittest.main()
