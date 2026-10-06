import os
import unittest
from unittest.mock import patch

from channel_memory import channel_dataset, build_channel_memory


class ChannelMemoryTests(unittest.TestCase):
    def setUp(self):
        self.data={"videos":{
            "legacy":{"genre":"space"},
            "ray":{"genre":"fiction","channel_key":"rayvan"},
            "other":{"genre":"tech","channel_key":"channel2"},
        }}

    def test_rayvan_inherits_legacy_only(self):
        scoped=channel_dataset(self.data,"rayvan")
        self.assertEqual(set(scoped["videos"]),{"legacy","ray"})

    def test_second_channel_does_not_train_on_rayvan(self):
        scoped=channel_dataset(self.data,"channel2")
        self.assertEqual(set(scoped["videos"]),{"other"})

    def test_memory_guardrail_disables_cross_channel_training(self):
        memory=build_channel_memory(self.data,"channel2")
        self.assertFalse(memory["guardrails"]["cross_channel_training"])


if __name__=="__main__":
    unittest.main()
