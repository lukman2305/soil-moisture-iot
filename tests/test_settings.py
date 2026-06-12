import unittest

from plant_monitor.settings import DEFAULT_READ_INTERVAL_SECONDS, read_interval_seconds


class SettingsTest(unittest.TestCase):
    def test_default_sampling_interval_is_ten_minutes(self):
        self.assertEqual(DEFAULT_READ_INTERVAL_SECONDS, 600)
        self.assertEqual(read_interval_seconds({}), 600.0)

    def test_read_interval_seconds_can_be_overridden_from_environment(self):
        self.assertEqual(read_interval_seconds({"READ_INTERVAL_SECONDS": "30"}), 30.0)


if __name__ == "__main__":
    unittest.main()
