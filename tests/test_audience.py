import copy
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
import httpx
import autonomy
import cloud_once
import reach_reports

class AudienceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 5, 21, 20, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.data = {"videos": {"test": {"published_at": "2026-10-04T22:52:22+05:30"}}}
        self.cred = patch.object(autonomy, "_credential", return_value=("unused", "mock", set()))
        self.cred.start()
        self.addCleanup(self.cred.stop)

    def report(self, headers, rows):
        return {"columnHeaders": [{"name": n} for n in headers], "rows": rows}

    def test_no_eligible_video_is_not_active_and_makes_no_queries(self):
        self.data["videos"]["test"]["published_at"] = self.now.isoformat()
        with patch.object(autonomy, "_query_analytics") as query:
            autonomy.refresh_analytics(self.data, self.now)
        query.assert_not_called()
        self.assertEqual(self.data["analytics_state"]["status"], "awaiting_eligible_videos")

    def test_empty_reports_clear_old_metrics_and_do_not_look_active(self):
        self.data["videos"]["test"]["analytics"] = {"views": 99999}
        self.data["analytics_state"] = {"status":"active", "checked_at": self.now.isoformat()}
        with patch.object(autonomy, "_query_analytics", return_value={}) as query:
            autonomy.refresh_analytics(self.data, self.now)
        self.assertEqual(query.call_count, 4)
        self.assertEqual(self.data["analytics_state"]["status"], "awaiting_data")
        self.assertNotIn("analytics", self.data["videos"]["test"])
        self.assertEqual(query.call_args.kwargs["end_date"], "2026-10-04")
        self.assertEqual(self.data["strategy"]["mode"], "explore")

    def test_traffic_rows_and_retention_are_preserved(self):
        reports = [
            self.report(["views", "averageViewPercentage"], [[40, 70]]),
            self.report(["insightTrafficSourceType", "views", "estimatedMinutesWatched"],
                        [["YT_SEARCH", 30, 8], ["SHORTS", 10, 2]]),
            self.report(["country", "views", "estimatedMinutesWatched"],
                        [["IN", 25, 7], ["US", 15, 3]]),
            self.report(["elapsedVideoTimeRatio", "audienceWatchRatio", "relativeRetentionPerformance"],
                        [[.1,.9,.5],[.5,.6,.4],[.9,.3,.2]]),
        ]
        with patch.object(autonomy, "_query_analytics", side_effect=reports) as query:
            autonomy.refresh_analytics(self.data, self.now)
        entry=self.data["videos"]["test"]
        self.assertEqual(self.data["analytics_state"]["status"], "active")
        self.assertEqual(len(entry["analytics_reports"]["traffic_sources"]["rows"]), 2)
        self.assertEqual(query.call_args_list[1].kwargs["dimensions"], "insightTrafficSourceType")
        self.assertFalse(entry["analytics_reports"]["traffic_sources"]["owner_views_identifiable"])
        self.assertEqual(len(entry["analytics_reports"]["geography"]["rows"]), 2)
        self.assertEqual(query.call_args_list[2].kwargs["dimensions"], "country")

    def test_forbidden_reports_are_errors_and_do_not_leak_tokens(self):
        response=httpx.Response(403, request=httpx.Request("GET","https://example.invalid/?token=secret"))
        error=httpx.HTTPStatusError("secret", request=response.request, response=response)
        with patch.object(autonomy, "_query_analytics", side_effect=error):
            autonomy.refresh_analytics(self.data,self.now)
        self.assertEqual(self.data["analytics_state"]["status"],"error")
        self.assertEqual(self.data["analytics_state"]["failures"][0]["http_status"],403)
        self.assertNotIn("secret",str(self.data))

    def test_excluded_videos_and_raw_views_never_choose_winner(self):
        videos={}
        for vid in autonomy.learning_exclusions():
            videos[vid]={"genre":"space", "analytics":{"views":100000,"averageViewPercentage":100,
                "refreshed_at":self.now.isoformat()}, "analytics_reports":{
                "basic":{"status":"available"},
                "traffic_sources":{"status":"available","rows":[{"views":100000}]}},
                "history":[{"at":self.now.isoformat(),"views":100000}],
                "published_at":(self.now-timedelta(hours=30)).isoformat()}
        data={"videos":videos,"strategy":{"genre_weights":{"space":1}}}
        self.assertEqual(autonomy._strategy(data,self.now)["mode"],"explore")
        self.assertIsNone(autonomy.strategy_genre(data,{"space"},now=self.now))
        self.assertEqual(cloud_once.genre_scores(videos),{})
        self.assertEqual(autonomy._strategy(data,self.now)["excluded_video_count"],9)

    def test_single_video_cannot_establish_winning_genre(self):
        entry={"genre":"space","analytics":{"views":100000,"averageViewPercentage":100,
            "refreshed_at":self.now.isoformat()},"analytics_reports":{
            "basic":{"status":"available"},
            "traffic_sources":{"status":"available","rows":[{"views":100000}]}}}
        self.assertEqual(autonomy._strategy({"videos":{"new":entry}},self.now)["mode"],"explore")

    def test_reach_waits_for_scope_instead_of_fabricating_impressions(self):
        with patch.object(autonomy,"_credential",return_value=None):
            reach_reports.refresh_reach(self.data,self.now)
        self.assertEqual(self.data["reach_state"]["status"],"awaiting_scope")
        self.assertNotIn("reach",self.data["videos"]["test"])

    def test_reach_backfills_replace_day_instead_of_double_counting(self):
        csv="date,channel_id,video_id,video_thumbnail_impressions,video_thumbnail_impressions_ctr\n"
        csv+="20261004,"+autonomy.EXPECTED_CHANNEL_ID+",test,100,5.2\n"
        report={"id":"r1","createTime":"2026-10-05T00:00:00Z"}
        for _ in range(2):
            reach_reports.ingest_csv(self.data,csv,report,self.now)
        days=self.data["videos"]["test"]["reach"]["days"]
        self.assertEqual(len(days),1)
        self.assertEqual(days["2026-10-04"]["impressions"],100)
        reach_reports.ingest_csv(self.data,csv.replace(",100,",",120,"),
                                 {"id":"r2","createTime":"2026-10-05T02:00:00Z"},self.now)
        self.assertEqual(days["2026-10-04"]["impressions"],120)

    def test_reach_rejects_wrong_channel_without_partial_mutation(self):
        csv="date,channel_id,video_id,video_thumbnail_impressions,video_thumbnail_impressions_ctr\n"
        csv+="20261004,WRONG,test,100,5.2\n"
        with self.assertRaises(ValueError):
            reach_reports.ingest_csv(self.data,csv,{"id":"r1"},self.now)
        self.assertNotIn("reach",self.data["videos"]["test"])
