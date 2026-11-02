"""Offline regression: independent, topic-relevant long-form news sources."""
import unittest

from longform_trends import sourced_topics, story_candidate


def _item(news):
    return {'title': 'grambling basketball', 'region': 'US',
            'traffic': '10K+', 'news': news}


ESPN = {'title': 'Northern Illinois beats Grambling basketball',
        'url': 'https://www.espn.com/mens-college-basketball/game/_/id/1',
        'source': 'ESPN'}
ESPN_PH = {'title': 'Grambling basketball season preview',
           'url': 'https://www.espn.ph/basketball/story/123',
           'source': 'ESPN Philippines'}
FOOTBALL = {'title': 'Bruno Fernandes returns to Manchester United against Chelsea',
            'url': 'https://www.espn.ph/football/story/123',
            'source': 'ESPN Philippines'}
AP = {'title': 'Grambling basketball faces Northern Illinois',
      'url': 'https://apnews.com/article/grambling-basketball',
      'source': 'Associated Press'}


class TrendSourceFidelityTests(unittest.TestCase):
    def test_unrelated_football_headline_does_not_count_as_basketball(self):
        self.assertIsNone(story_candidate([_item([ESPN, FOOTBALL])]))

    def test_regional_domains_of_one_publisher_not_independent(self):
        self.assertIsNone(story_candidate([_item([ESPN, ESPN_PH])]))

    def test_independent_relevant_reporting_remains_eligible(self):
        candidate = story_candidate([_item([ESPN, AP])])
        self.assertIsNotNone(candidate)
        self.assertEqual(len(candidate['sources']), 2)

    def test_sensitive_topic_needs_independent_relevant_reporting(self):
        item = {'title': 'earthquake in Japan', 'traffic': '5K+',
                'news': [
                    {'title': 'Earthquake hits Japan',
                     'url': 'https://www.bbc.com/news/world-asia-1', 'source': 'BBC'},
                    {'title': 'Japan earthquake response continues',
                     'url': 'https://apnews.com/article/japan-quake', 'source': 'AP'},
                ]}
        self.assertEqual(len(sourced_topics([item])[0]['sources']), 2)

    def test_unanchored_generic_topic_fails_closed(self):
        self.assertIsNone(story_candidate([{
            'title': 'why is it trending now', 'traffic': '10K+',
            'news': [ESPN, AP]}]))


if __name__ == '__main__':
    unittest.main()
